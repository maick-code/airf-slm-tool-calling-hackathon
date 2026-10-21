#!/usr/bin/env python3
"""Synthetic tool-calling examples with NEW names/places/templates (dev-style OOD)."""
from __future__ import annotations

import json
import random
from pathlib import Path

RNG = random.Random(2026)

ALL_TOOLS = [
    "send_money", "buy_airtime", "buy_data", "check_balance",
    "buy_electricity_token", "report_outage", "get_crop_price",
    "get_weather", "convert_currency", "set_reminder",
]
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

# Names / places not copied from typical train hubs
FIRST = [
    "Zainab", "Chinedu", "Folake", "Ifeanyi", "Naledi", "Thabo", "Palesa", "Sipho",
    "Ama", "Kojo", "Efua", "Yaw", "Wanjiku", "Kamau", "Achieng", "Otieno",
    "Namuli", "Kato", "Amina", "Juma", "Uwase", "Mugisha", "Chisomo", "Mutale",
    "Tigist", "Dawit", "Lerato", "Bongani", "Adjoa", "Ngozi", "Kofi", "Aisha",
]
LAST = [
    "Okeke", "Mensah", "Mwangi", "Nkrumah", "Dlamini", "Banda", "Tesfaye", "Kagame",
    "Okafor", "Boateng", "Kipchoge", "Ssemakula", "Phiri", "Abebe", "Botha", "Iheanacho",
]
PLACES = [
    "Oyugis", "Homa Bay", "Kericho", "Embu", "Meru", "Machakos",
    "Hohoe", "Techiman", "Cape Coast", "Koforidua",
    "Awka", "Uyo", "Jos", "Makurdi", "Abeokuta",
    "Jinja", "Gulu", "Mbarara", "Fort Portal",
    "Morogoro", "Dodoma", "Iringa", "Moshi",
    "Musanze", "Nyagatare", "Rusizi",
    "Ndola", "Chipata", "Livingstone",
    "Bahir Dar", "Hawassa", "Mekelle",
    "Polokwane", "Mahikeng", "Nelspruit", "Kimberley",
]
CROPS = [
    "maize", "beans", "rice", "cassava", "tomatoes", "onions", "sorghum",
    "millet", "groundnuts", "plantain", "yams", "sukuma wiki", "coffee", "teff",
]
PROVIDERS = [
    "MTN MoMo", "M-Pesa", "Airtel Money", "OPay", "PalmPay", "Telecel Cash",
    "Tigo Pesa", "Vodafone Cash", "FNB eWallet", "CBE Birr", "MoMo",
]
NETWORKS = ["MTN", "Airtel", "Glo", "Safaricom", "Vodafone", "Tigo", "9mobile", "Telkom"]
CUR = [
    ("naira", "NGN"), ("cedis", "GHS"), ("bob", "KES"), ("Kenyan shillings", "KES"),
    ("Ugandan shillings", "UGX"), ("Tanzanian shillings", "TZS"),
    ("rand", "ZAR"), ("kwacha", "ZMW"), ("birr", "ETB"), ("Rwandan francs", "RWF"),
    ("dollars", "USD"),
]
TASKS = [
    "pay my rent", "call the landlord", "pick up the kids from school",
    "buy cooking gas", "attend the chama meeting", "send the invoice",
    "water the garden", "charge the inverter", "collect the parcel",
]
DATES = [("tomorrow", "tomorrow"), ("today", "today"), ("on Friday", "friday"),
         ("on Monday", "monday"), ("on 3 March", "3 March"), ("on 12 April", "12 April")]
TIMES = [("7am", "07:00"), ("9:30am", "09:30"), ("6pm", "18:00"), ("1:15pm", "13:15"), ("noon", "12:00")]


def distractors(need, n=4):
    rest = [t for t in ALL_TOOLS if t not in need]
    RNG.shuffle(rest)
    tools = list(need) + rest[: max(0, n - len(need))]
    RNG.shuffle(tools)
    return tools


def person():
    if RNG.random() < 0.45:
        return RNG.choice(FIRST)
    return f"{RNG.choice(FIRST)} {RNG.choice(LAST)}"


def phone():
    if RNG.random() < 0.3:
        return "+234" + "".join(str(RNG.randint(0, 9)) for _ in range(10))
    return "0" + "".join(str(RNG.randint(0, 9)) for _ in range(10))


def meter():
    return "".join(str(RNG.randint(0, 9)) for _ in range(11))


def amount():
    return RNG.choice([200, 500, 1000, 1500, 2000, 2500, 5000, 7500, 10000, 20000, 50000])


def fmt_amt(n, word, iso):
    if iso == "NGN" and RNG.random() < 0.3:
        return f"₦{n:,}", n, iso
    if iso == "ZAR" and RNG.random() < 0.3:
        return f"R{n}", n, iso
    if n >= 1000 and n % 1000 == 0 and RNG.random() < 0.4:
        return f"{n // 1000}k {word}", n, iso
    return f"{n:,} {word}", n, iso


def greet():
    return RNG.choice(["", "Please ", "Abeg ", "Sasa, ", "Chale, ", "Oga, ", "Hey, ", "Quick one: "])


def tail():
    return RNG.choice(["", ".", " thanks", " pls", " thx"])


def make_send(missing=False):
    rec, prov = person(), RNG.choice(PROVIDERS)
    word, iso = RNG.choice(CUR)
    n = amount()
    text_amt, n, iso = fmt_amt(n, word, iso)
    drop = RNG.choice(["provider", "currency", "amount", "recipient"]) if missing else None
    bits = []
    if drop != "amount":
        bits.append(text_amt)
    who = rec if drop != "recipient" else "my landlord"
    bits.append(f"to {who}")
    if drop != "provider":
        bits.append(f"on {prov}")
    req = greet() + RNG.choice(["Send ", "Transfer ", "Please send "]) + " ".join(bits) + tail()
    params = {
        "recipient": None if drop == "recipient" else rec,
        "amount": None if drop == "amount" else n,
        "currency": None if drop in ("amount", "currency") else iso,
        "provider": None if drop == "provider" else prov,
    }
    if drop == "currency" and "amount" not in (drop,):
        # amount without currency word
        req = greet() + f"Send {n} to {who}" + (f" on {prov}" if drop != "provider" else "") + tail()
        params["amount"] = n
        params["currency"] = None
    return req, "send_money", params


def make_air(data=False, missing=False):
    tool = "buy_data" if data else "buy_airtime"
    ph, net, n = phone(), RNG.choice(NETWORKS), amount()
    drop = RNG.choice(["phone", "network", "amount"]) if missing else None
    kind = "data" if data else RNG.choice(["airtime", "airtime", "call credit"])
    parts = [greet() + RNG.choice(["Buy ", "Load ", "Please buy ", "Top up "])]
    if drop != "amount":
        parts.append(f"{n} ")
    parts.append(f"{kind} ")
    if drop != "phone":
        parts.append(f"for {ph} ")
    if drop != "network":
        parts.append(f"on {net}")
    req = "".join(parts).strip() + tail()
    return req, tool, {
        "phone": None if drop == "phone" else ph,
        "amount": None if drop == "amount" else n,
        "network": None if drop == "network" else net,
    }


def make_bal(missing=False):
    prov = RNG.choice(PROVIDERS)
    if missing:
        req = greet() + RNG.choice(["Check my balance", "What's my wallet balance", "Show balance"]) + tail()
        return req, "check_balance", {"provider": None}
    req = greet() + RNG.choice([
        f"Check my {prov} balance",
        f"What's my {prov} balance?",
        f"Show {prov} balance",
    ]) + tail()
    return req, "check_balance", {"provider": prov}


def make_token(missing=False):
    m, n = meter(), amount()
    word, iso = RNG.choice(CUR)
    text, n, iso = fmt_amt(n, word, iso)
    drop = RNG.choice(["meter_number", "amount", "currency"]) if missing else None
    if drop == "currency":
        req = greet() + f"Buy electricity token of {n} for meter {m}" + tail()
        return req, "buy_electricity_token", {"meter_number": m, "amount": n, "currency": None}
    if drop == "amount":
        req = greet() + f"Buy tokens for meter {m}" + tail()
        return req, "buy_electricity_token", {"meter_number": m, "amount": None, "currency": None}
    if drop == "meter_number":
        req = greet() + f"Buy {text} electricity token" + tail()
        return req, "buy_electricity_token", {"meter_number": None, "amount": n, "currency": iso}
    req = greet() + f"Buy {text} electricity token for meter {m}" + tail()
    return req, "buy_electricity_token", {"meter_number": m, "amount": n, "currency": iso}


def make_outage(missing=False):
    loc = RNG.choice(PLACES)
    if missing:
        req = greet() + RNG.choice(["Report the outage", "There's a blackout, report it", "No power, please report"]) + tail()
        return req, "report_outage", {"location": None}
    req = greet() + RNG.choice([
        f"Report a power outage in {loc}",
        f"There's a blackout in {loc}, please report it",
        f"No electricity in {loc}",
    ]) + tail()
    return req, "report_outage", {"location": loc}


def make_crop(missing=False):
    crop, loc = RNG.choice(CROPS), RNG.choice(PLACES)
    drop = RNG.choice(["crop", "location"]) if missing else None
    if drop == "location":
        req = greet() + f"What's the price of {crop}?" + tail()
        return req, "get_crop_price", {"crop": crop, "location": None}
    if drop == "crop":
        req = greet() + f"How are prices at {loc} market?" + tail()
        return req, "get_crop_price", {"crop": None, "location": loc}
    req = greet() + RNG.choice([
        f"What's the {crop} price in {loc}?",
        f"How much is {crop} selling for at {loc}?",
        f"Price of {crop} around {loc}",
    ]) + tail()
    return req, "get_crop_price", {"crop": crop, "location": loc}


def make_weather(missing=False):
    loc = RNG.choice(PLACES)
    dtxt, dval = RNG.choice(DATES)
    drop = RNG.choice(["location", "date"]) if missing else None
    if drop == "date":
        req = greet() + f"Will it rain in {loc}?" + tail()
        return req, "get_weather", {"location": loc, "date": None}
    if drop == "location":
        req = greet() + f"What's the weather {dtxt}?" + tail()
        return req, "get_weather", {"location": None, "date": dval}
    req = greet() + RNG.choice([
        f"Weather in {loc} {dtxt}?",
        f"Will it rain in {loc} {dtxt}?",
        f"Forecast for {loc} {dtxt}",
    ]) + tail()
    return req, "get_weather", {"location": loc, "date": dval}


def make_fx(missing=False):
    (w1, i1), (w2, i2) = RNG.sample(CUR, 2)
    n = amount()
    drop = RNG.choice(["amount", "to_currency", "from_currency"]) if missing else None
    if drop == "amount":
        req = greet() + f"What's the {w1} to {w2} rate?" + tail()
        return req, "convert_currency", {"amount": None, "from_currency": i1, "to_currency": i2}
    if drop == "to_currency":
        req = greet() + f"How much is {n:,} {w1} in my local money?" + tail()
        return req, "convert_currency", {"amount": n, "from_currency": i1, "to_currency": None}
    req = greet() + RNG.choice([
        f"Convert {n:,} {w1} to {w2}",
        f"How much is {n:,} {w1} in {w2}?",
        f"What's {n:,} {w1} worth in {w2}?",
    ]) + tail()
    return req, "convert_currency", {"amount": n, "from_currency": i1, "to_currency": i2}


def make_rem(missing=False):
    task = RNG.choice(TASKS)
    dtxt, dval = RNG.choice(DATES)
    ttxt, tval = RNG.choice(TIMES)
    drop = RNG.choice(["time", "date", "task"]) if missing else None
    if drop == "time":
        req = greet() + f"Remind me to {task} {dtxt}" + tail()
        return req, "set_reminder", {"task": task, "date": dval, "time": None}
    if drop == "date":
        req = greet() + f"Remind me to {task} at {ttxt}" + tail()
        return req, "set_reminder", {"task": task, "date": None, "time": tval}
    req = greet() + f"Remind me to {task} {dtxt} at {ttxt}" + tail()
    return req, "set_reminder", {"task": task, "date": dval, "time": tval}


SINGLE = [make_send, make_air, lambda m=False: make_air(True, m), make_bal, make_token,
          make_outage, make_crop, make_weather, make_fx, make_rem]


def pack(req, tool, params, category, extra_tools=None):
    need = extra_tools or [tool]
    tools = distractors(need, n=RNG.choice([4, 5, 6]))
    row = {
        "id": None,
        "request": req.strip(),
        "tools": tools,
        "meta": {"category": category, "synthetic": True},
    }
    if category == "multiple" or extra_tools:
        return None  # filled by caller
    row["tool"] = tool
    row["parameters"] = params
    row["answer"] = {"tool": tool, "parameters": params}
    return row


def make_multi():
    a = RNG.choice(SINGLE)(False)
    b = RNG.choice(SINGLE)(False)
    if a[1] == b[1] and RNG.random() < 0.5:
        # same tool two crops / two weather
        pass
    req = a[0].rstrip(". ") + ", then " + b[0][0].lower() + b[0][1:]
    tools = distractors([a[1], b[1]], n=5)
    calls = [
        {"tool": a[1], "parameters": a[2]},
        {"tool": b[1], "parameters": b[2]},
    ]
    return {
        "id": None,
        "request": req,
        "tools": tools,
        "tool_calls": calls,
        "answer": calls,
        "meta": {"category": "multiple", "synthetic": True},
    }


def generate(n_single=5000, n_missing=2000, n_multi=2000):
    rows = []
    for i in range(n_single):
        fn = SINGLE[i % len(SINGLE)]
        req, tool, params = fn(False)
        rows.append(pack(req, tool, params, "single"))
    for i in range(n_missing):
        fn = SINGLE[i % len(SINGLE)]
        req, tool, params = fn(True)
        rows.append(pack(req, tool, params, "missing_info"))
    for _ in range(n_multi):
        rows.append(make_multi())
    for i, r in enumerate(rows, 1):
        r["id"] = f"syn-{i:05d}"
    RNG.shuffle(rows)
    return rows


def main():
    rows = generate()
    out = Path("data/synthetic.jsonl")
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} -> {out}")


if __name__ == "__main__":
    main()
