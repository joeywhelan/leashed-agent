#!/usr/bin/env python3
"""Emit a synthetic product catalog as NDJSON on stdout, with planted quality defects.

Defects (deterministic via the seed):
  40 duplicate SKUs         the same record emitted twice
  30 missing price          price field absent
  12 negative price
 150 category casing        Title Case or UPPER instead of lower
  60 whitespace in name     leading and/or trailing spaces
"""
import json
import random

random.seed(11)
N = 5_000
PREFIXES = ["AB", "CD", "EF", "GH", "JK"]
SUFFIXES = ["X", "Y", "Z"]
CATEGORIES = ["audio", "cable", "case", "charger", "mount", "sensor"]
BRANDS = ["Acme", "Globex", "Initech", "Umbrella", "Vandelay"]

docs, seen = [], set()
while len(docs) < N:
    sku = f"{random.choice(PREFIXES)}-{random.randint(1000, 4999):04d}-{random.choice(SUFFIXES)}"
    if sku in seen:
        continue
    seen.add(sku)
    cat = random.choice(CATEGORIES)
    docs.append({
        "sku": sku,
        "name": f"{random.choice(BRANDS)} {cat} {sku[-1]}{sku[3:7]}",
        "category": cat,
        "price": round(random.uniform(4.99, 499.99), 2),
        "in_stock": random.random() > 0.15,
        "description": f"{cat.capitalize()} unit, model {sku}. Ships in 2-3 business days.",
        "updated_at": f"2026-0{random.randint(1, 8)}-{random.randint(1, 28):02d}T{random.randint(0, 23):02d}:00:00Z",
    })

idx = list(range(N))
random.shuffle(idx)
for i in idx[0:30]:
    del docs[i]["price"]
for i in idx[30:42]:
    docs[i]["price"] = -abs(docs[i]["price"])
for i in idx[42:192]:
    c = docs[i]["category"]
    docs[i]["category"] = c.upper() if i % 2 else c.title()
for i in idx[192:252]:
    docs[i]["name"] = ("  " if i % 3 else "") + docs[i]["name"] + (" " if i % 2 else "   ")
duplicates = [dict(docs[i]) for i in idx[252:292]]

for d in docs + duplicates:
    print(json.dumps(d))
