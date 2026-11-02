"""Schema-safe helpers for the African SLM Tool Calling submission format.

This module deliberately does not infer missing values from a request.  It only
parses a model's JSON, validates offered tool names, fills required-but-omitted
fields with ``None``, and converts values to the JSON types in ``tools.json``.
"""

from __future__ import annotations

import json
import math
import re
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence


_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_COMMA_GROUPED_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[eE][+-]?\d+)?$")
_SPACE_GROUPED_RE = re.compile(r"^[+-]?\d{1,3}(?: \d{3})+(?:\.\d+)?(?:[eE][+-]?\d+)?$")
_NULL_TEXT = {"", "null", "none", "nil"}


def answer_from_training_row(row: Mapping[str, Any]) -> Any:
    """Return a benchmark answer, collapsing a one-call list to one object."""
    if "tool_calls" in row:
        calls = row["tool_calls"]
    else:
        calls = [{"tool": row["tool"], "parameters": row["parameters"]}]
    if not isinstance(calls, list) or not calls:
        raise ValueError(f"Invalid training answer for {row.get('id', '<unknown>')}")
    return calls[0] if len(calls) == 1 else calls


def _as_finite_number(value: Any) -> int | float | None:
    """Convert JSON-ish numeric output to a JSON number; do not parse shorthand."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return int(value) if value.is_integer() else value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text or text.lower() in _NULL_TEXT:
        return None
    if _COMMA_GROUPED_RE.fullmatch(text):
        text = text.replace(",", "")
    elif _SPACE_GROUPED_RE.fullmatch(text):
        text = text.replace(" ", "")
    elif not _NUMBER_RE.fullmatch(text):
        return None

    if "." not in text and "e" not in text.lower():
        try:
            return int(text)
        except ValueError:
            return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    if number.is_integer():
        return int(number)
    return number


def _as_string_or_null(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return None if value.lower() in _NULL_TEXT else value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        # A string field (notably phone/meter numbers) must remain a JSON string.
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        return str(int(value)) if value.is_integer() else str(value)
    return None


def parse_model_json(text: str) -> Any | None:
    """Find the first JSON object/array in a model reply, including fenced output."""
    if not isinstance(text, str):
        return None
    decoder = json.JSONDecoder()
    starts = sorted(pos for pos in (text.find("{"), text.find("[")) if pos >= 0)
    for start in starts:
        try:
            value, _end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, (dict, list)):
            return value
    return None


def fallback_answer(available_tools: Sequence[str], schemas: Mapping[str, Any]) -> dict[str, Any]:
    """Return a well-formed last-resort answer when decoding/validation fails.

    This does not attempt to guess values.  It uses the first offered tool with
    null parameters so the submission remains schema-shaped rather than being
    rejected for malformed output.  The notebook reports how often this occurs.
    """
    if not available_tools:
        return {"tool": "", "parameters": {}}
    name = available_tools[0]
    schema = schemas.get(name, {})
    parameters = schema.get("parameters", {}) if isinstance(schema, Mapping) else {}
    return {"tool": name, "parameters": {key: None for key in parameters}}


def _coerce_call(
    call: Any,
    available_tools: Sequence[str],
    schemas: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(call, Mapping):
        return None

    tool_name = call.get("tool", call.get("name"))
    if not isinstance(tool_name, str) or tool_name not in available_tools:
        return None
    schema = schemas.get(tool_name)
    if not isinstance(schema, Mapping):
        return None
    parameter_schema = schema.get("parameters")
    if not isinstance(parameter_schema, Mapping):
        return None

    raw_parameters = call.get("parameters", call.get("arguments", {}))
    if not isinstance(raw_parameters, Mapping):
        raw_parameters = {}

    parameters: dict[str, Any] = {}
    for key, value_type in parameter_schema.items():
        value = raw_parameters.get(key)
        if value_type == "number":
            parameters[key] = _as_finite_number(value)
        elif value_type == "string":
            parameters[key] = _as_string_or_null(value)
        else:
            # Unknown schema types are not silently passed through.
            return None
    return {"tool": tool_name, "parameters": parameters}


def coerce_prediction(
    prediction: Any,
    available_tools: Sequence[str],
    schemas: Mapping[str, Any],
) -> tuple[Any, bool]:
    """Validate and schema-complete an answer; return (answer, used_fallback)."""
    value = parse_model_json(prediction) if isinstance(prediction, str) else prediction
    if isinstance(value, Mapping) and "tool_calls" in value:
        value = value["tool_calls"]

    calls = value if isinstance(value, list) else [value]
    if not calls:
        return fallback_answer(available_tools, schemas), True

    normalized: list[dict[str, Any]] = []
    for call in calls:
        result = _coerce_call(call, available_tools, schemas)
        if result is None:
            return fallback_answer(available_tools, schemas), True
        normalized.append(result)

    # The benchmark treats a one-item list and an object as equivalent; emit the
    # canonical object for one action and preserve order for genuine multi-calls.
    return (normalized[0] if len(normalized) == 1 else normalized), False


def validate_prediction_map(
    rows: Sequence[Mapping[str, Any]],
    predictions: Mapping[str, Any],
    schemas: Mapping[str, Any],
) -> None:
    """Raise on missing/extra IDs or malformed calls before creating a ZIP."""
    row_ids = [str(row["id"]) for row in rows]
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("Input data contains duplicate IDs")
    if set(predictions) != set(row_ids):
        missing = sorted(set(row_ids) - set(predictions))[:5]
        extra = sorted(set(predictions) - set(row_ids))[:5]
        raise ValueError(f"Prediction IDs do not match input IDs (missing={missing}, extra={extra})")

    for row in rows:
        answer = predictions[str(row["id"])]
        calls = answer if isinstance(answer, list) else [answer]
        if not calls:
            raise ValueError(f"Empty call list for {row['id']}")
        available = row.get("tools", [])
        for call in calls:
            if not isinstance(call, Mapping):
                raise ValueError(f"Invalid call for {row['id']}")
            name = call.get("tool")
            if name not in available or name not in schemas:
                raise ValueError(f"Tool {name!r} is not offered for {row['id']}")
            expected_keys = set(schemas[name]["parameters"])
            params = call.get("parameters")
            if not isinstance(params, Mapping) or set(params) != expected_keys:
                raise ValueError(f"Incomplete parameter schema for {row['id']} / {name}")
            for key, value_type in schemas[name]["parameters"].items():
                value = params[key]
                if value is not None and value_type == "number" and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or (isinstance(value, float) and not math.isfinite(value))
                ):
                    raise ValueError(f"Non-numeric {key!r} for {row['id']}")
                if value is not None and value_type == "string" and not isinstance(value, str):
                    raise ValueError(f"Non-string {key!r} for {row['id']}")


def write_submission_zip(
    rows: Sequence[Mapping[str, Any]],
    predictions: Mapping[str, Any],
    schemas: Mapping[str, Any],
    zip_path: str | Path = "submission.zip",
    json_path: str | Path = "predictions.json",
) -> tuple[Path, Path]:
    """Write the exact Codabench format: one root-level predictions.json in ZIP."""
    validate_prediction_map(rows, predictions, schemas)
    ordered = {str(row["id"]): predictions[str(row["id"])] for row in rows}
    json_file = Path(json_path)
    json_file.write_text(
        json.dumps(ordered, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )

    zip_file = Path(zip_path)
    with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(json_file, arcname="predictions.json")
    return json_file, zip_file
