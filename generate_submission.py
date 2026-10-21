#!/usr/bin/env python3
"""Build Codabench submission.json / submission.zip and optionally push to GitHub.

Usage (after Colab training, or with the rule parser fallback):

  python generate_submission.py --dev data/dev.jsonl --out submission.json
  python generate_submission.py --adapter ./adapter --model google/functiongemma-270m-it
  python generate_submission.py --push   # git add, commit, push current branch
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import zipfile
from pathlib import Path

SCHEMAS = {
    "send_money": ["recipient", "amount", "currency", "provider"],
    "buy_airtime": ["phone", "amount", "network"],
    "buy_data": ["phone", "amount", "network"],
    "check_balance": ["provider"],
    "buy_electricity_token": ["meter_number", "amount", "currency"],
    "report_outage": ["location"],
    "get_crop_price": ["crop", "location"],
    "get_weather": ["location", "date"],
    "convert_currency": ["amount", "from_currency", "to_currency"],
    "set_reminder": ["task", "date", "time"],
}
NUM_PARAMS = {"amount"}


def coerce_call(obj):
    if not isinstance(obj, dict) or "tool" not in obj:
        return None
    tool = obj["tool"]
    if tool not in SCHEMAS:
        return None
    raw = obj.get("parameters") or {}
    params = {}
    for k in SCHEMAS[tool]:
        v = raw.get(k, None)
        if v is None or v == "" or v == "null":
            params[k] = None
        elif k in NUM_PARAMS:
            try:
                n = float(v)
                params[k] = int(n) if n == int(n) else n
            except (TypeError, ValueError):
                params[k] = None
        else:
            params[k] = v
    return {"tool": tool, "parameters": params}


def coerce_answer(value):
    if value is None:
        return {"tool": "", "parameters": {}}
    if isinstance(value, list):
        calls = [c for c in (coerce_call(x) for x in value) if c]
        if not calls:
            return {"tool": "", "parameters": {}}
        if len(calls) == 1:
            return calls[0]
        return calls
    call = coerce_call(value)
    return call if call else {"tool": "", "parameters": {}}


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def predict_rules(dev):
    from parser import predict_one

    return {ex["id"]: predict_one(ex["request"], ex["tools"]) for ex in dev}


def predict_model(dev, model_name, adapter, tools_path):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tools = {t["name"]: t for t in json.loads(Path(tools_path).read_text())}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(adapter if Path(adapter).exists() else model_name)
    tokenizer.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype, attn_implementation="eager")
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    model.to(device).eval()

    instruction = "Reply with a JSON list of the tool calls for the request, with null for values not given.\nTools:\n"

    def build_prompt(example):
        signatures = [
            f"{name}({', '.join(f'{p}: {t}' for p, t in tools[name]['parameters'].items())})"
            for name in example["tools"]
        ]
        messages = [
            {"role": "system", "content": instruction + "\n".join(signatures)},
            {"role": "user", "content": example["request"]},
        ]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    def parse(text):
        text = text.split("<end_of_turn>")[0]
        starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
        try:
            value = json.JSONDecoder().raw_decode(text, min(starts))[0] if starts else None
        except json.JSONDecodeError:
            return None
        return value

    stop = [tokenizer.eos_token_id]
    eot = tokenizer.convert_tokens_to_ids("<end_of_turn>")
    if eot is not None and eot != tokenizer.unk_token_id:
        stop.append(eot)

    out = {}
    batch_size = 16 if device == "cuda" else 2
    order = sorted(dev, key=lambda ex: len(build_prompt(ex)))
    with torch.no_grad():
        for i in range(0, len(order), batch_size):
            batch = order[i : i + batch_size]
            inputs = tokenizer(
                [build_prompt(ex) for ex in batch],
                return_tensors="pt",
                padding=True,
                add_special_tokens=False,
            ).to(device)
            tokens = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                eos_token_id=stop,
                pad_token_id=tokenizer.pad_token_id,
            )
            for ex, seq in zip(batch, tokens[:, inputs["input_ids"].shape[1] :]):
                out[ex["id"]] = parse(tokenizer.decode(seq, skip_special_tokens=False))
    return out


def write_submission(preds, out_path):
    out_path = Path(out_path)
    clean = {k: coerce_answer(v) for k, v in preds.items()}
    out_path.write_text(json.dumps(clean, indent=1, ensure_ascii=False))
    zpath = out_path.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(out_path, arcname="predictions.json")
        z.write(out_path, arcname=out_path.name)
    print(f"{len(clean)} predictions -> {out_path} and {zpath}")
    return out_path, zpath


def git_push():
    subprocess.check_call(["git", "add", "submission.json", "generate_submission.py", "parser.py"], cwd=".")
    st = subprocess.check_output(["git", "status", "--porcelain"], text=True)
    if not st.strip():
        print("nothing to commit")
        return
    subprocess.check_call(["git", "commit", "-m", "Update Codabench submission artifacts"])
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    subprocess.check_call(["git", "push", "origin", branch])
    print("pushed", branch)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dev", default="data/dev.jsonl")
    p.add_argument("--tools", default="data/tools.json")
    p.add_argument("--out", default="submission.json")
    p.add_argument("--model", default=os.environ.get("MODEL_NAME", "google/gemma-3-270m-it"))
    p.add_argument("--adapter", default="")
    p.add_argument("--rules-only", action="store_true")
    p.add_argument("--push", action="store_true")
    args = p.parse_args()

    dev = load_jsonl(args.dev)
    adapter = args.adapter or os.environ.get("ADAPTER_DIR", "")
    if args.rules_only or not adapter:
        print("using rule parser")
        preds = predict_rules(dev)
    else:
        print("using model", args.model, "adapter", adapter)
        preds = predict_model(dev, args.model, adapter, args.tools)
    write_submission(preds, args.out)
    if args.push:
        git_push()


if __name__ == "__main__":
    main()
