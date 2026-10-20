#!/usr/bin/env python3
"""Rule-based tool-call parser for the Africa SLM tool-calling hackathon."""
from __future__ import annotations

import json
import re
from pathlib import Path

MONTHS = {
    "jan": "January", "january": "January", "feb": "February", "february": "February",
    "mar": "March", "march": "March", "apr": "April", "april": "April", "may": "May",
    "jun": "June", "june": "June", "jul": "July", "july": "July",
    "aug": "August", "august": "August", "sep": "September", "sept": "September",
    "september": "September", "oct": "October", "october": "October",
    "nov": "November", "november": "November", "dec": "December", "december": "December",
}
WEEKDAYS = {
    "mon": "monday", "monday": "monday", "tue": "tuesday", "tues": "tuesday",
    "tuesday": "tuesday", "wed": "wednesday", "weds": "wednesday", "wednesday": "wednesday",
    "thu": "thursday", "thur": "thursday", "thurs": "thursday", "thursday": "thursday",
    "fri": "friday", "friday": "friday", "sat": "saturday", "saturday": "saturday",
    "sun": "sunday", "sunday": "sunday",
}

CURRENCY_ISO = {
    "naira": "NGN", "ngn": "NGN", "cedi": "GHS", "cedis": "GHS", "ghs": "GHS", "ghc": "GHS",
    "ghana cedi": "GHS", "ghana cedis": "GHS", "ghanaian cedi": "GHS", "ghanaian cedis": "GHS",
    "kenyan shilling": "KES", "kenyan shillings": "KES", "kenya shilling": "KES",
    "kenya shillings": "KES", "ksh": "KES", "kes": "KES", "bob": "KES",
    "ugandan shilling": "UGX", "ugandan shillings": "UGX", "uganda shilling": "UGX",
    "uganda shillings": "UGX", "ugx": "UGX", "ush": "UGX",
    "tanzanian shilling": "TZS", "tanzanian shillings": "TZS", "tanzania shilling": "TZS",
    "tanzania shillings": "TZS", "tsh": "TZS", "tzs": "TZS",
    "rwandan franc": "RWF", "rwandan francs": "RWF", "rwanda franc": "RWF",
    "rwanda francs": "RWF", "rwandan": "RWF", "rwf": "RWF", "frw": "RWF",
    "rand": "ZAR", "rands": "ZAR", "zar": "ZAR",
    "kwacha": "ZMW", "zmw": "ZMW",
    "birr": "ETB", "etb": "ETB", "ethiopian birr": "ETB",
    "dollar": "USD", "dollars": "USD", "usd": "USD",
    "euro": "EUR", "euros": "EUR", "eur": "EUR",
    "pound": "GBP", "pounds": "GBP", "gbp": "GBP", "sterling": "GBP",
}

NUM_WORDS = {
    "zero": 0, "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

TITLES = (
    "mr", "mrs", "ms", "miss", "dr", "prof", "pastor", "rev", "reverend", "sir",
    "madam", "madame", "oga", "aunty", "auntie", "aunt", "uncle", "brother", "sister",
    "mama", "baba", "chief", "hon", "eng",
)
RELATIONS = (
    "sister", "brother", "uncle", "aunt", "aunty", "auntie", "cousin", "mother", "father",
    "mum", "mom", "dad", "wife", "husband", "son", "daughter", "friend", "landlord",
    "pastor", "neighbour", "neighbor", "boss", "colleague", "mama", "papa",
)

NETWORKS = sorted({
    "MTN Mobile Money", "MTN MoMo", "MTN Momo", "MTN Money", "MTN Mobile", "MTN",
    "AirtelTigo Money", "Airtel Money", "AirtelTigo", "Airtel",
    "Tigo Pesa", "Tigo", "M-Pesa", "Mpesa", "M Pesa", "Safaricom", "Saf",
    "Vodacom M-Pesa", "Vodafone Cash", "Vodacom", "Vodafone", "Voda",
    "Glo", "9mobile", "9Mobile", "Telecel Cash", "Telecel",
    "Orange Money", "Orange", "MoMoPay", "MoMo",
    "OPay", "PalmPay", "Paga", "Chipper Cash", "Chipper", "Kuda",
    "FNB eWallet", "FNB", "GTBank", "Ecobank", "Absa", "Capitec",
    "Standard Bank", "Equity", "Halotel", "T-Kash", "Tkash", "Equitel",
    "Paystack", "Flutterwave", "CBE Birr", "Telebirr", "M-Pesa", "Telkom",
}, key=len, reverse=True)

CROPS = sorted({
    "sukuma wiki", "sweet potato", "sweet potatoes", "irish potato", "irish potatoes",
    "groundnut", "groundnuts", "cashew", "cashews", "sorghum", "millet", "maize", "corn",
    "beans", "bean", "rice", "cassava", "yam", "yams", "plantain", "plantains",
    "banana", "bananas", "tomato", "tomatoes", "onion", "onions", "cabbage", "cabbages",
    "potato", "potatoes", "wheat", "coffee", "tea", "cocoa", "cotton", "sugarcane",
    "sugar cane", "pepper", "peppers", "okra", "spinach", "kale", "carrot", "carrots",
    "avocado", "avocados", "mango", "mangoes", "pineapple", "pineapples",
    "watermelon", "watermelons", "soya", "soybean", "soybeans", "cowpea", "cowpeas",
    "teff", "barley", "sunflower", "sesame", "butternut", "butternuts", "pumpkin",
    "pumpkins", "pawpaw", "papaya", "guava", "cocoyam", "taro", "lentils", "lentil",
    "chickpea", "chickpeas", "ground nut",
}, key=len, reverse=True)

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

STOP = {
    "the", "my", "this", "that", "here", "there", "town", "city", "area", "pls", "please",
    "me", "us", "it", "today", "tomorrow", "a", "an", "and", "or", "for", "from", "with",
    "on", "in", "at", "to", "of", "some", "any", "his", "her", "our", "your", "thanks",
    "cheers", "hello", "hey", "hi", "quick", "one", "also", "then",
    "help", "something", "someone", "goods", "supplier", "event",
}

INTENT_PATTERNS = [
    ("set_reminder", 10, r"\b(remind(?:\s+me)?|don't let me forget|dont let me forget|nudge me|ping me|a reminder|set a reminder|don't forget)\b"),
    ("convert_currency", 11, r"\b(convert|worth in|how much is|exchange rate|in rand|in naira|in usd|in dollars|us dollars|to usd|to eur|what(?:'s| is) [\d,].+ in |what's .+ in |to pound|cedi to|naira to)\b"),
    ("convert_currency", 9, r"(₦|\$|£|€|[A-Z]{3}\s*[\d,]).{0,30}\bto\s+(usd|eur|gbp|ngn|ghs|kes|ugx|tzs|rwf|zar|zmw|etb|[A-Z]{3})\b"),
    ("send_money", 9, r"\b(send|transfer|wire)\b(?!\s+me\b)"),
    ("buy_airtime", 10, r"\b(airtime|call credit|credit is finished|recharge)\b"),
    ("buy_data", 10, r"\b(data(?:\s+bundle)?|\d+\s*(?:gb|mb)\b|internet bundle|bundle for)\b"),
    ("check_balance", 10, r"\b(balance|\bbal\b|how much (?:do i have|have i|is (?:in|left|on my)))\b"),
    ("buy_electricity_token", 10, r"\b(electricity token|buy (?:tokens?|units)|prepaid|meter|eskom|kplc|luku)\b"),
    ("report_outage", 10, r"\b(outage|outtage|blackout|no power|no (?:light|electricity)|power cut|lights? (?:are )?out|power has been off|report (?:it|the (?:outage|blackout)))\b"),
    ("get_crop_price", 9, r"\b(price of|the price|prices? in|going for|selling for|cost of|market price)\b"),
    ("get_weather", 9, r"\b(weather|forecast|rain|sunny|temperature|will it rain|expect rain|how hot|how cold)\b"),
]


def norm_text(x):
    if x is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(x).lower())


def answers_equal(pred, gold):
    def as_list(x):
        return x if isinstance(x, list) else [x]
    p, g = as_list(pred), as_list(gold)
    if len(p) != len(g):
        return False
    for a, b in zip(p, g):
        if a.get("tool") != b.get("tool"):
            return False
        tool = a.get("tool")
        keys = SCHEMAS.get(tool, set(a.get("parameters") or {}) | set(b.get("parameters") or {}))
        pa, pb = a.get("parameters") or {}, b.get("parameters") or {}
        for k in keys:
            va, vb = pa.get(k), pb.get(k)
            if va is None and vb is None:
                continue
            if isinstance(va, (int, float)) or isinstance(vb, (int, float)):
                try:
                    if va is None or vb is None or float(va) != float(vb):
                        return False
                except (TypeError, ValueError):
                    return False
            elif not norm_text(va) == norm_text(vb):
                return False
    return True


def words_to_num(text):
    parts = [p for p in re.split(r"[\s-]+", text.lower().strip()) if p and p != "and"]
    if not parts:
        return None
    if "million" in parts:
        i = parts.index("million")
        left = words_to_num(" ".join(parts[:i])) if i else 1
        right = words_to_num(" ".join(parts[i + 1 :])) if i + 1 < len(parts) else 0
        if left is None:
            return None
        return left * 1_000_000 + (right or 0)
    if "thousand" in parts:
        i = parts.index("thousand")
        left = words_to_num(" ".join(parts[:i])) if i else 1
        right = words_to_num(" ".join(parts[i + 1 :])) if i + 1 < len(parts) else 0
        if left is None:
            return None
        return left * 1000 + (right or 0)
    if "hundred" in parts:
        i = parts.index("hundred")
        left = words_to_num(" ".join(parts[:i])) if i else 1
        right = words_to_num(" ".join(parts[i + 1 :])) if i + 1 < len(parts) else 0
        if left is None:
            return None
        return left * 100 + (right or 0)
    total = 0
    for p in parts:
        if p not in NUM_WORDS:
            return None
        total += NUM_WORDS[p]
    return total


def _f(s):
    s = (s or "").replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def scale(v, suf):
    suf = (suf or "").lower()
    if suf == "k":
        v *= 1000
    elif suf in ("m", "million"):
        v *= 1_000_000
    return int(v) if v == int(v) else v


PHONE_RE = re.compile(r"(\+?\d[\d][\d\s-]{6,18}\d)")


def phone_spans(text):
    spans = []
    for m in PHONE_RE.finditer(text):
        compact = re.sub(r"[\s-]", "", m.group(1))
        if len(re.sub(r"\D", "", compact)) >= 8:
            spans.append((compact, m.span()))
    return spans


def in_span(pos, spans):
    return any(a <= pos < b for a, b in spans)


def extract_amounts(text):
    phones = [s for _, s in phone_spans(text)]
    found = []

    def add(v, cur, span, pri=0):
        if v is None:
            return
        if any(not (span[1] <= p[0] or span[0] >= p[1]) for _, _, p, _ in found):
            return
        # skip if inside phone
        if any(span[0] >= a and span[1] <= b and (span[1] - span[0]) < (b - a) for a, b in phones):
            return
        found.append((v, cur, span, pri))

    for pat, cur in [
        (r"₦\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?", "NGN"),
        (r"GH₵\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?", "GHS"),
        (r"€\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?", "EUR"),
        (r"£\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?", "GBP"),
        (r"\$\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?", "USD"),
    ]:
        for m in re.finditer(pat, text, re.I):
            v = _f(m.group(1))
            if v is not None:
                add(scale(v, m.group(2)), cur, m.span(), 3)

    for m in re.finditer(r"\b([RrNn])\s*([\d,]+(?:\.\d+)?)\b", text):
        v = _f(m.group(2))
        if v is None:
            continue
        cur = "ZAR" if m.group(1) in "Rr" else "NGN"
        add(v if v != int(v) else int(v), cur, m.span(), 3)

    # K50 / k150 as ZMW only if letter is prefix not suffix 150k
    for m in re.finditer(r"(?<![A-Za-z0-9])([Kk])\s*([\d,]+(?:\.\d+)?)(?!\s*k)\b", text):
        v = _f(m.group(2))
        if v is not None and v < 1_000_000:
            add(int(v) if v == int(v) else v, "ZMW", m.span(), 2)

    iso_pat = r"\b(ksh|kes|ngn|ghs|ghc|ugx|ush|tsh|tzs|rwf|frw|zar|zmw|etb|usd|eur|gbp)\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?\b"
    for m in re.finditer(iso_pat, text, re.I):
        v = _f(m.group(2))
        if v is None:
            continue
        add(scale(v, m.group(3)), CURRENCY_ISO.get(m.group(1).lower()), m.span(), 3)

    money = (
        r"(naira|cedis?|ghana(?:ian)?\s+cedis?|kenyan\s+shillings?|kenya\s+shillings?|"
        r"ugandan\s+shillings?|uganda\s+shillings?|tanzanian\s+shillings?|"
        r"rwandan\s+francs?|rand|rands|kwacha|birr|ethiopian\s+birr|"
        r"dollars?|euros?|pounds?|bob)"
    )
    for m in re.finditer(rf"\b([\d,]+(?:\.\d+)?)\s*(k|m|million)?\s*{money}\b", text, re.I):
        v = _f(m.group(1))
        if v is None:
            continue
        w = re.sub(r"\s+", " ", m.group(3).lower())
        add(scale(v, m.group(2)), CURRENCY_ISO.get(w), m.span(), 3)
    for m in re.finditer(rf"\b{money}\s+([\d,]+(?:\.\d+)?)\s*(k|m|million)?\b", text, re.I):
        v = _f(m.group(2))
        if v is None:
            continue
        w = re.sub(r"\s+", " ", m.group(1).lower())
        add(scale(v, m.group(3)), CURRENCY_ISO.get(w), m.span(), 3)

    for m in re.finditer(r"\b([\d,]+(?:\.\d+)?)\s*(k|million|m)\b", text, re.I):
        v = _f(m.group(1))
        if v is None:
            continue
        add(scale(v, m.group(2)), None, m.span(), 1)

    for m in re.finditer(
        r"\b((?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
        r"forty|fifty|sixty|seventy|eighty|ninety)(?:[\s-]+(?:and\s+)?(?:one|two|three|"
        r"four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|"
        r"eighty|ninety|hundred|thousand|million))+)\b",
        text,
        re.I,
    ):
        v = words_to_num(m.group(1))
        if v:
            add(v, None, m.span(), 2)

    # numbers not in phones (2–7 digits)
    for m in re.finditer(r"\b(\d{1,3}(?:,\d{3})+|\d{2,7})(?:\.\d+)?\b", text):
        v = _f(m.group(1))
        if v is None:
            continue
        add(int(v) if v == int(v) else v, None, m.span(), 0)

    found.sort(key=lambda x: (-x[3], x[2][0]))
    out, used = [], []
    for item in found:
        s = item[2]
        if any(not (s[1] <= u[0] or s[0] >= u[1]) for u in used):
            continue
        out.append(item)
        used.append(s)
    out.sort(key=lambda x: x[2][0])
    return out


def extract_phones(text):
    return phone_spans(text)


def extract_meter(text):
    out = []
    for m in re.finditer(
        r"(?:meter(?:\s+(?:number|no\.?|#))?|metre|token(?:\s+for)?)\s*(?:is|:|#|no\.?|number)?\s*([A-Za-z]?\d[\d\sA-Za-z-]{4,})",
        text,
        re.I,
    ):
        val = re.sub(r"[\s-]", "", m.group(1))
        val = re.split(r"(?i)with|for|of", val)[0]
        val = re.sub(r"[A-Za-z]+$", "", val)
        if len(re.sub(r"\D", "", val)) >= 6:
            out.append((val, m.span()))
    if not out:
        for m in re.finditer(r"\b(\d{8,14})\b", text):
            out.append((m.group(1), m.span()))
        # spaced meter 8915 2042 503
        for m in re.finditer(r"\b(\d{3,5}(?:\s+\d{3,5}){1,3})\b", text):
            val = re.sub(r"\s+", "", m.group(1))
            if 8 <= len(val) <= 14:
                out.append((val, m.span()))
    return out


def extract_date(text):
    t = text.lower()
    if re.search(r"\b(today|tonight|this morning|this afternoon|this evening|this night)\b", t):
        return "today"
    if re.search(r"\b(tomorrow|tmrw|tmr|tommorrow)\b", t):
        return "tomorrow"
    m = re.search(
        r"\b(?:this|on|next)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b",
        t,
    )
    if m:
        return WEEKDAYS[m.group(1)]
    m = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
        t,
    )
    if m:
        mk = m.group(2).lower()
        key = mk if mk in MONTHS else mk[:3]
        return f"{int(m.group(1))} {MONTHS[key]}"
    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\b",
        t,
    )
    if m:
        mk = m.group(1).lower()
        key = mk if mk in MONTHS else mk[:3]
        return f"{int(m.group(2))} {MONTHS[key]}"
    return None


def extract_time(text):
    t = text.lower()
    if re.search(r"\b(noon|midday)\b", t):
        return "12:00"
    if re.search(r"\bmidnight\b", t):
        return "00:00"
    m = re.search(r"\bhalf past (\d{1,2})\s*(in the (morning|evening|afternoon)|am|pm|a\.m\.|p\.m\.)?", t)
    if m:
        h = int(m.group(1))
        rest = m.group(2) or ""
        if any(x in rest for x in ("evening", "afternoon", "pm")) and h < 12:
            h += 12
        if "morning" in rest and h == 12:
            h = 0
        return f"{h:02d}:30"
    m = re.search(r"\b(\d{1,2})\s*o['’]?clock\s*(in the (morning|evening|afternoon)|am|pm)?", t)
    if m:
        h = int(m.group(1))
        rest = m.group(2) or ""
        if any(x in rest for x in ("evening", "afternoon", "pm")) and h < 12:
            h += 12
        if "morning" in rest and h == 12:
            h = 0
        return f"{h:02d}:00"
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\s*(a\.?m\.?|p\.?m\.?)?\b", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        ap = (m.group(3) or "").replace(".", "")
        if ap.startswith("p") and h < 12:
            h += 12
        if ap.startswith("a") and h == 12:
            h = 0
        return f"{h:02d}:{mi:02d}"
    m = re.search(r"\b(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)\b", t)
    if m:
        h = int(m.group(1))
        ap = m.group(2).replace(".", "")
        if ap.startswith("p") and h < 12:
            h += 12
        if ap.startswith("a") and h == 12:
            h = 0
        return f"{h:02d}:00"
    return None


def extract_network(text):
    hits = []
    for name in NETWORKS:
        pat = re.compile(r"\b" + re.escape(name).replace(r"\-", r"[- ]?") + r"\b", re.I)
        for m in pat.finditer(text):
            hits.append((m.group(0).strip(), m.span(), len(name)))
    hits.sort(key=lambda x: -x[2])
    out, used = [], []
    for h in hits:
        s = h[1]
        if any(not (s[1] <= u[0] or s[0] >= u[1]) for u in used):
            continue
        out.append(h)
        used.append(s)
    out.sort(key=lambda x: x[1][0])
    return out


def extract_crops(text):
    hits = []
    tl = text.lower()
    for c in CROPS:
        for m in re.finditer(r"\b" + re.escape(c) + r"\b", tl):
            hits.append((c, m.span()))
    hits.sort(key=lambda x: -(x[1][1] - x[1][0]))
    out, used = [], []
    for h in hits:
        s = h[1]
        if any(not (s[1] <= u[0] or s[0] >= u[1]) for u in used):
            continue
        out.append(h)
        used.append(s)
    return out


def title_strip(name):
    parts = name.split()
    while parts and parts[0].lower().rstrip(".") in TITLES:
        parts = parts[1:]
    return " ".join(parts).strip() or None


def extract_recipient(text):
    m = re.search(
        r"\b(?:to|send(?:\s+\w+){0,3}?)\s+(?:my\s+(?:" + "|".join(RELATIONS) + r")\s+)?"
        r"(?:(?:" + "|".join(TITLES) + r")\.?\s+)?([A-Za-z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        text,
        re.I,
    )
    if m:
        name = title_strip(m.group(1) if False else m.group(0))
    # simpler: capture after to/for
    m = re.search(
        r"\b(?:to|for|send|transfer)\s+(?:my\s+(?:" + "|".join(RELATIONS) + r")\s+)?"
        r"((?:" + "|".join(TITLES) + r")\.?\s+)?([A-Za-z][A-Za-z'-]+(?:\s+[A-Z][a-z]+){0,2})",
        text,
        re.I,
    )
    if m:
        raw = ((m.group(1) or "") + " " + m.group(2)).strip()
        raw = re.sub(r"\s+(?:through|using|on|via|from|with)\b.*", "", raw, flags=re.I)
        name = title_strip(raw)
        first = name.split()[0].lower() if name else ""
        if (
            name
            and name.lower() not in STOP
            and name.lower() not in RELATIONS
            and first not in STOP
            and first not in NUM_WORDS
            and first not in ("money", "cash")
        ):
            return name.title() if name.islower() else name
    m = re.search(
        r"\b(?:my\s+(?:" + "|".join(RELATIONS) + r")\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        text,
    )
    if m:
        return title_strip(m.group(1))
    return None


def extract_location(text):
    m = re.search(
        r"\b(?:in|around|at|from|near|for|to)\s+(?:the\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})(?:\s+[Mm]arket)?",
        text,
    )
    if m:
        loc = re.sub(r"\s+(pls|please|thanks|cheers|market)$", "", m.group(1), flags=re.I).strip()
        if loc.lower() not in STOP and "help" not in loc.lower() and loc.lower() != "your help":
            return loc
    m = re.search(
        r"\b(?:in|around|at|from|near|for)\s+(?:the\s+)?([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+){0,2})",
        text,
        re.I,
    )
    if m:
        loc = re.sub(r"\s+(pls|please|thanks|cheers|market)$", "", m.group(1), flags=re.I).strip()
        if loc.lower() not in STOP:
            return loc.title()
    m = re.search(r"\b(?:weather|forecast|rain)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    if m and m.group(1).lower() not in STOP | {"this", "today", "tomorrow"}:
        return m.group(1)
    m = re.search(r"\bWeather\s+([A-Za-z]+)\b", text)
    if m and m.group(1).lower() not in STOP:
        return m.group(1).title()
    m = re.search(r"\bI'm (?:in|going to)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)", text)
    if m:
        return m.group(1)
    return None


def iso_of(token):
    t = re.sub(r"\s+", " ", token.lower().strip())
    if t in CURRENCY_ISO:
        return CURRENCY_ISO[t]
    for k, v in sorted(CURRENCY_ISO.items(), key=lambda x: -len(x[0])):
        if v and (t == k or t.startswith(k + " ") or k.startswith(t) and len(t) >= 4):
            return v
    if re.fullmatch(r"[A-Za-z]{3}", t):
        return t.upper()
    return None


def extract_currencies(text):
    names = []
    pats = [
        (r"ghana(?:ian)?\s+cedis?", "GHS"),
        (r"kenyan\s+shillings?|kenya\s+shillings?", "KES"),
        (r"ugandan\s+shillings?|uganda\s+shillings?", "UGX"),
        (r"tanzanian\s+shillings?", "TZS"),
        (r"rwandan\s+francs?|rwanda\s+francs?", "RWF"),
        (r"ethiopian\s+birr", "ETB"),
        (r"naira", "NGN"), (r"cedis?", "GHS"), (r"\bbob\b", "KES"),
        (r"rands?", "ZAR"), (r"kwacha", "ZMW"), (r"birr", "ETB"),
        (r"us dollars?", "USD"), (r"dollars?", "USD"), (r"euros?", "EUR"), (r"pounds?", "GBP"),
        (r"\bNGN\b", "NGN"), (r"\bGHS\b", "GHS"), (r"\bKES\b", "KES"),
        (r"\bKSh\b", "KES"), (r"\bUGX\b", "UGX"), (r"\bTZS\b", "TZS"),
        (r"\bTSh\b", "TZS"), (r"\bRWF\b", "RWF"), (r"\bZAR\b", "ZAR"),
        (r"\bZMW\b", "ZMW"), (r"\bETB\b", "ETB"), (r"\bUSD\b", "USD"),
        (r"\bEUR\b", "EUR"), (r"\bGBP\b", "GBP"),
        (r"\$", "USD"), (r"€", "EUR"), (r"£", "GBP"), (r"₦", "NGN"),
    ]
    for pat, iso in pats:
        for m in re.finditer(pat, text, re.I):
            names.append((iso, m.span()))
    names.sort(key=lambda x: x[1][0])
    out = []
    for iso, sp in names:
        if not out or out[-1][0] != iso or sp[0] - out[-1][1][1] > 2:
            out.append((iso, sp))
    return out


def detect_intents_in_text(text, tools):
    hits = []
    tl = text.lower()
    has_money = bool(re.search(r"\b(naira|cedi|rand|kwacha|birr|dollar|usd|ngn|kes|zmw|ugx|tzs|rwf|zar|etb|gbp|eur|shilling|bob)\b", tl))
    has_crop = bool(extract_crops(text))
    for name, score, pat in INTENT_PATTERNS:
        if name not in tools:
            continue
        for m in re.finditer(pat, text, re.I):
            sc = score
            if name == "convert_currency" and has_crop and not has_money:
                continue
            if name == "get_crop_price" and has_money and not has_crop:
                sc -= 5
            hits.append((m.start(), sc, name))
    # airtime vs data
    t = text.lower()
    if "buy_electricity_token" in tools and re.search(r"\b(meter|token|electric|units|prepaid)\b", t) and re.search(
        r"\b(buy|top\s*up|recharge|purchase|get|load)\b", t
    ):
        hits.append((0, 12, "buy_electricity_token"))
    if "buy_data" in tools and re.search(r"\b(data|bundle|\d\s*gb|\d\s*mb|internet)\b", t):
        if "buy_airtime" in tools and re.search(r"\b(airtime|call credit)\b", t):
            pass
        elif re.search(r"\b(data|bundle|gb|mb|internet)\b", t) and not re.search(r"\bmeter\b", t):
            hits.append((0, 8, "buy_data"))
    hits.sort(key=lambda x: x[0])
    # unique by position window
    ordered = []
    for pos, sc, name in hits:
        if ordered and ordered[-1] == name and pos - 0 < 5:
            continue
        if not ordered or ordered[-1] != name:
            # don't duplicate same tool unless far
            if name in ordered:
                # allow same tool if later (multi)
                last_i = len(ordered) - 1 - ordered[::-1].index(name)
                # keep if different later mention
                ordered.append(name)
            else:
                ordered.append(name)
    # collapse consecutive dupes
    compact = []
    for n in ordered:
        if not compact or compact[-1] != n:
            compact.append(n)
    return compact


def fill_params(tool, request, inherit=None):
    inherit = inherit or {}
    amounts = extract_amounts(request)
    phones = extract_phones(request)
    nets = extract_network(request)
    params = {k: None for k in SCHEMAS[tool]}

    def first_amount():
        for a, c, sp, *_ in amounts:
            window = request[max(0, sp[0] - 6) : sp[1] + 6].lower()
            if re.search(r"\b(gb|mb)\b", window):
                continue
            if a >= 1e8:
                continue
            return a, c
        return None, None

    if tool == "send_money":
        params["recipient"] = extract_recipient(request)
        a, c = first_amount()
        params["amount"] = a
        params["currency"] = c
        if not c:
            curs = extract_currencies(request)
            if curs:
                params["currency"] = curs[0][0]
        if nets:
            params["provider"] = nets[0][0]
        elif inherit.get("provider"):
            if re.search(r"\b(from it|same|from there|using it)\b", request, re.I):
                params["provider"] = inherit["provider"]
        if phones and not params["recipient"]:
            params["recipient"] = phones[0][0]
    elif tool in ("buy_airtime", "buy_data"):
        if phones:
            params["phone"] = phones[0][0]
        a, _ = first_amount()
        params["amount"] = a
        if nets:
            params["network"] = nets[0][0]
    elif tool == "check_balance":
        if nets:
            params["provider"] = nets[0][0]
    elif tool == "buy_electricity_token":
        meters = extract_meter(request)
        if meters:
            params["meter_number"] = meters[0][0]
        a, c = first_amount()
        # don't treat meter chunks as amount
        if a is not None and meters:
            mval = meters[0][0]
            if str(int(a) if isinstance(a, float) and a == int(a) else a) in mval:
                a, c = None, None
        params["amount"] = a
        params["currency"] = c
    elif tool == "report_outage":
        params["location"] = extract_location(request)
    elif tool == "get_crop_price":
        crops = extract_crops(request)
        if crops:
            params["crop"] = crops[0][0]
        else:
            m = re.search(
                r"\b(?:price of|cost of|how much (?:is|are))\s+(?:a\s+(?:bag|kilo)\s+of\s+)?([a-z]+)(?:\s+(?:at|in|around)\b)?",
                request,
                re.I,
            )
            if m and m.group(1).lower() not in STOP:
                params["crop"] = m.group(1).lower()
        params["location"] = extract_location(request)
    elif tool == "get_weather":
        params["location"] = extract_location(request)
        params["date"] = extract_date(request)
    elif tool == "convert_currency":
        curs = extract_currencies(request)
        a, c = first_amount()
        params["amount"] = a
        if c:
            params["from_currency"] = c
        m = re.search(
            r"\b([A-Za-z]{3}|naira|cedis|rand|kwacha|birr|dollars?|euros?|pounds?|bob|"
            r"ghana(?:ian)?\s+cedis?|kenyan\s+shillings?|ugandan\s+shillings?|"
            r"tanzanian\s+shillings?|rwandan\s+francs?)\s+to\s+"
            r"([A-Za-z]{3}|naira|cedis|rand|kwacha|birr|dollars?|euros?|pounds?|bob|"
            r"ugandan\s+shillings?|tanzanian\s+shillings?|rwandan\s+francs?|"
            r"kenyan\s+shillings?|ghana(?:ian)?\s+cedis?)",
            request,
            re.I,
        )
        if m:
            f, to = iso_of(m.group(1)), iso_of(m.group(2))
            if f:
                params["from_currency"] = f
            if to:
                params["to_currency"] = to
        if not params.get("from_currency") and curs:
            params["from_currency"] = curs[0][0]
        m_in = re.search(
            r"\b(?:in|to|into|worth in)\s+(USD|EUR|GBP|NGN|GHS|KES|UGX|TZS|RWF|ZAR|ZMW|ETB|"
            r"naira|cedis|dollars?|euros?|pounds?|rand|kwacha|birr|rwandan\s+francs?)\b",
            request,
            re.I,
        )
        if m_in:
            params["to_currency"] = iso_of(m_in.group(1)) or params.get("to_currency")
        if not params.get("to_currency") and len(curs) >= 2:
            params["to_currency"] = curs[-1][0]
            if not params.get("from_currency"):
                params["from_currency"] = curs[0][0]
    elif tool == "set_reminder":
        params["date"] = extract_date(request)
        params["time"] = extract_time(request)
        task = None
        m = re.search(
            r"(?:remind me to|don't let me forget to|dont let me forget to|nudge me to|"
            r"ping me to|make sure i(?: remember to)?|a reminder (?:for|to)|remind me)\s+(.+)",
            request,
            re.I,
        )
        if m:
            task = m.group(1)
        else:
            m = re.search(r"forgetting to\s+(.+?)(?:\.|$)", request, re.I)
            if m:
                task = m.group(1)
        if task:
            task = re.sub(
                r"\s+(?:on|at|by|this|tomorrow|tmrw|today|monday|tuesday|wednesday|"
                r"thursday|friday|saturday|sunday|in the).*$",
                "",
                task,
                flags=re.I,
            )
            task = re.sub(r"[.?!]+$", "", task).strip()
            # drop leading "to "
            task = re.sub(r"^to\s+", "", task, flags=re.I)
            params["task"] = task or None
    return params


def split_clauses(request):
    # keep trigger words on the following clause
    parts = re.split(
        r"\b(?=(?:then|after that|also,|also\b|and then|"
        r"and remind|and how much|and (?:show|check|send|convert|buy|report|transfer)))",
        request,
        flags=re.I,
    )
    return [p.strip(" .") for p in parts if len(p.strip()) > 4]


def predict_one(request, tools):
    tools = list(tools)
    t = request.lower()

    # convert X to A and to B
    if "convert_currency" in tools:
        curs = extract_currencies(request)
        if re.search(r"\bto\b.+\band\s+to\b", t) and len(curs) >= 3:
            amounts = extract_amounts(request)
            amt = amounts[0][0] if amounts else None
            frm = curs[0][0]
            return [
                {"tool": "convert_currency", "parameters": {"amount": amt, "from_currency": frm, "to_currency": curs[1][0]}},
                {"tool": "convert_currency", "parameters": {"amount": amt, "from_currency": frm, "to_currency": curs[2][0]}},
            ]

    if "get_crop_price" in tools:
        crops = extract_crops(request)
        if len(crops) >= 2 and re.search(r"\b(price|cost|how much)\b", t):
            loc = extract_location(request)
            return [
                {"tool": "get_crop_price", "parameters": {"crop": c[0], "location": loc}}
                for c in crops[:2]
            ]

    if "get_weather" in tools:
        m = re.search(r"\bin\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)", request)
        if m and re.search(r"\b(rain|weather|forecast)\b", t):
            date = extract_date(request)
            return [
                {"tool": "get_weather", "parameters": {"location": m.group(1), "date": date}},
                {"tool": "get_weather", "parameters": {"location": m.group(2), "date": date}},
            ]

    if "send_money" in tools:
        recs = re.findall(
            r"to\s+(?:my\s+\w+\s+)?(?:(?:mr|mrs|ms|dr|aunty|uncle|madam)\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            request,
        )
        recs = [title_strip(r) for r in recs]
        recs = [r for r in recs if r]
        amounts = extract_amounts(request)
        nets = extract_network(request)
        prov = nets[0][0] if nets else None
        if len(recs) >= 2 and len(amounts) >= 2 and re.search(r"\b(send|transfer)\b", t):
            return [
                {
                    "tool": "send_money",
                    "parameters": {
                        "recipient": recs[i],
                        "amount": amounts[i][0],
                        "currency": amounts[i][1],
                        "provider": prov,
                    },
                }
                for i in range(min(len(recs), len(amounts), 3))
            ]

    if "check_balance" in tools:
        nets = extract_network(request)
        if len(nets) >= 2 and re.search(r"\bbalance", t):
            return [{"tool": "check_balance", "parameters": {"provider": n[0]}} for n in nets[:2]]

    if "buy_airtime" in tools and "buy_data" in tools and re.search(r"\bairtime\b", t) and re.search(
        r"\b(data|bundle)\b", t
    ):
        phones = extract_phones(request)
        phone = phones[0][0] if phones else None
        nets = extract_network(request)
        net = nets[0][0] if nets else None
        amts = []
        for a, c, sp, *_ in extract_amounts(request):
            window = request[max(0, sp[0] - 4) : sp[1] + 4].lower()
            if re.search(r"\b(gb|mb)\b", window) or a >= 1e8:
                continue
            amts.append(a)
        a1 = amts[0] if amts else None
        a2 = amts[1] if len(amts) > 1 else a1
        return [
            {"tool": "buy_airtime", "parameters": {"phone": phone, "amount": a1, "network": net}},
            {"tool": "buy_data", "parameters": {"phone": phone, "amount": a2, "network": net}},
        ]

    clauses = split_clauses(request)
    if len(clauses) >= 2:
        calls = []
        inherit = {}
        for ch in clauses:
            intents = detect_intents_in_text(ch, tools)
            if not intents:
                continue
            tool = intents[0]
            params = fill_params(tool, ch, inherit)
            # fill from full request if missing shared
            if tool == "send_money" and not params.get("provider"):
                full = fill_params(tool, request, inherit)
                if full.get("provider") and re.search(r"\b(from it|from there)\b", request, re.I):
                    params["provider"] = inherit.get("provider") or full.get("provider")
                if params.get("currency") is None and full.get("currency"):
                    params["currency"] = full["currency"]
            calls.append({"tool": tool, "parameters": params})
            if tool == "check_balance" and params.get("provider"):
                inherit["provider"] = params["provider"]
        if len(calls) >= 2:
            return calls

    intents = detect_intents_in_text(request, tools)
    if len(intents) >= 2:
        inherit = {}
        calls = []
        for tool in intents:
            params = fill_params(tool, request, inherit)
            calls.append({"tool": tool, "parameters": params})
            if tool == "check_balance" and params.get("provider"):
                inherit["provider"] = params["provider"]
        # if second call looks empty vs first being only, still return multi if request has connectors
        if re.search(r"\b(then|also|after that|and then)\b", t):
            return calls

    tool = intents[0] if intents else tools[0]
    return {"tool": tool, "parameters": fill_params(tool, request)}


def gold_of(ex):
    if "tool_calls" in ex:
        return ex["tool_calls"]
    return {"tool": ex["tool"], "parameters": ex["parameters"]}


def evaluate_train(path="data/train.jsonl", limit=None):
    n = ok = 0
    by_cat = {}
    misses = []
    with open(path) as f:
        for line in f:
            ex = json.loads(line)
            n += 1
            if limit and n > limit:
                break
            pred = predict_one(ex["request"], ex["tools"])
            gold = gold_of(ex)
            cat = (ex.get("meta") or {}).get("category", "?")
            by_cat.setdefault(cat, [0, 0])
            by_cat[cat][1] += 1
            if answers_equal(pred, gold):
                ok += 1
                by_cat[cat][0] += 1
            elif len(misses) < 20:
                misses.append((ex["id"], ex["request"], pred, gold, cat))
    return ok, n, by_cat, misses


def write_submission(dev_path="data/dev.jsonl", out_path="submission.json"):
    sub = {}
    with open(dev_path) as f:
        for line in f:
            ex = json.loads(line)
            sub[ex["id"]] = predict_one(ex["request"], ex["tools"])
    Path(out_path).write_text(json.dumps(sub, indent=1))
    return out_path


if __name__ == "__main__":
    import sys
    if "--submit" in sys.argv:
        print("wrote", write_submission())
    else:
        lim = 2000 if "--quick" in sys.argv else None
        ok, n, by_cat, misses = evaluate_train(limit=lim)
        print(f"acc {ok}/{n} = {ok/n:.4f}")
        print(by_cat)
        for m in misses[:15]:
            print("---", m[0], m[4])
            print("Q:", m[1][:200])
            print("P:", json.dumps(m[2], ensure_ascii=False)[:320])
            print("G:", json.dumps(m[3], ensure_ascii=False)[:320])
