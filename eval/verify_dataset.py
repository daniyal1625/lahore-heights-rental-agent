#!/usr/bin/env python3
"""Consistency checks for the Lahore Heights dataset.

Usage (from the repo root):
    python eval/verify_dataset.py
    python eval/verify_dataset.py --guide data/local_guide/wikivoyage_lahore.txt

What it checks
  1. scenarios.json structure, unique ids, category counts
  2. every manual section a scenario cites really exists in the manual
  3. every `manual_evidence` string really appears in the manual
  4. `expected_available_listing_ids` match the availability computed from the fixtures
  5. "gap" topics that must stay OUT of the manual (so escalation tests stay valid)
  6. reservation fixture arithmetic (totals, extra guest fees, balances)
  7. (optional) every `guide_evidence` string appears in your Wikivoyage snapshot
Exit code is 1 if any hard check fails.
"""
import argparse, datetime as dt, json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--guide", help="path to the saved Wikivoyage Lahore text snapshot")
args = ap.parse_args()

errors, warnings = [], []
def err(m): errors.append(m)
def warn(m): warnings.append(m)

def norm(t):
    t = t.lower().replace("\u2019", "'").replace("\u2011", "-")
    t = re.sub(r"[*`_>|]", " ", t).replace(",", "")
    return re.sub(r"\s+", " ", t)

manual_raw = (ROOT / "data/house_manual/lahore_heights_house_manual.md").read_text(encoding="utf-8")
manual = norm(manual_raw)
sections = set(re.findall(r"^#{2,3}\s+(\d+(?:\.\d+)?)\.?\s", manual_raw, flags=re.M))

data = json.loads((ROOT / "eval/scenarios.json").read_text(encoding="utf-8"))
scen = data["scenarios"]
listings = json.loads((ROOT / "data/fixtures/listings.json").read_text(encoding="utf-8"))["result"]
res = json.loads((ROOT / "data/fixtures/reservations_fixed.json").read_text(encoding="utf-8"))["result"]

# 1 structure
REQ = ["id", "category", "guest_message", "thread_context", "required_tools", "optional_tools",
       "required_facts", "must_escalate_to_host", "reference_answer", "difficulty"]
ids = [s["id"] for s in scen]
if len(ids) != len(set(ids)): err("duplicate scenario ids")
for s in scen:
    for k in REQ:
        if k not in s: err(f"{s.get('id')}: missing key {k}")
    for t in s["required_tools"] + s["optional_tools"]:
        if t not in data["meta"]["tool_signatures"]: err(f"{s['id']}: unknown tool {t}")
print("scenarios:", len(scen), dict(Counter(s["category"] for s in scen)))
print("difficulty:", dict(Counter(s["difficulty"] for s in scen)))

# 2 + 3 manual refs / evidence
for s in scen:
    for sec in s.get("manual_sections", []):
        if sec not in sections: err(f"{s['id']}: manual section {sec} not found")
    for ev in s.get("manual_evidence", []):
        if norm(ev) not in manual: err(f"{s['id']}: evidence not in manual: {ev!r}")

# 4 availability
L = {l["id"]: l for l in listings}
def avail(ci, co, guests=None):
    ci, co = dt.date.fromisoformat(ci), dt.date.fromisoformat(co)
    out = []
    for l in listings:
        if guests and guests > l["personCapacity"]: continue
        busy = any(r["listingMapId"] == l["id"] and r["status"] != "cancelled"
                   and dt.date.fromisoformat(r["arrivalDate"]) < co and ci < dt.date.fromisoformat(r["departureDate"])
                   for r in res)
        if not busy: out.append(l["id"])
    return out
for s in scen:
    exp = s.get("expected_available_listing_ids")
    a = s["expected_args"].get("check_availability")
    if exp is not None and a:
        got = avail(a["check_in"], a["check_out"], a.get("guests"))
        if got != exp: err(f"{s['id']}: availability mismatch expected {exp} got {got}")

# 5 gap topics must not be in the manual
GAPS = ["airport", "chef", "charger", "charging", "sim card", "playstation", "board game", "baby monitor",
        "baby bath", "rent a car", "with a driver", "invoice", "ntn", "dentist", "child-proof", "childproof",
        "stair gate", "socket cover", "weather forecast"]
for g in GAPS:
    if g in manual: err(f"gap keyword present in manual (breaks an escalation test): {g!r}")

# 6 fixtures
for r in res:
    L_ = L[r["listingMapId"]]
    n = (dt.date.fromisoformat(r["departureDate"]) - dt.date.fromisoformat(r["arrivalDate"])).days
    if n != r["nights"]: err(f"res {r['id']}: nights mismatch")
    if r["status"] in ("ownerStay",): continue
    extra = max(0, r["numberOfGuests"] - L_["guestsIncluded"]) * n * L_["extraGuestFee"]
    if r["totalPrice"] != n * L_["price"] + extra: err(f"res {r['id']}: total mismatch")
    if r["numberOfGuests"] > L_["personCapacity"]: err(f"res {r['id']}: over capacity")
    if r["status"] != "cancelled" and r["totalPrice"] - r["paidAmount"] != r["balanceDue"]: err(f"res {r['id']}: balance mismatch")
# no double bookings in fixtures
act = [r for r in res if r["status"] != "cancelled"]
for i, a in enumerate(act):
    for b in act[i + 1:]:
        if a["listingMapId"] == b["listingMapId"] and a["arrivalDate"] < b["departureDate"] and b["arrivalDate"] < a["departureDate"]:
            err(f"fixture overlap: {a['id']} vs {b['id']}")

# 7 guide evidence
if args.guide:
    g = norm(Path(args.guide).read_text(encoding="utf-8"))
    for s in scen:
        for ev in s.get("guide_evidence", []):
            if norm(ev) not in g: warn(f"{s['id']}: guide evidence not found in snapshot: {ev!r} (fix the scenario or reword)")
else:
    n = sum(1 for s in scen if s.get("guide_evidence"))
    warn(f"{n} scenarios cite the Wikivoyage guide; re-run with --guide <snapshot.txt> once you have saved it")

for w in warnings: print("WARN ", w)
for e in errors: print("ERROR", e)
print("OK" if not errors else f"FAILED ({len(errors)} errors)")
sys.exit(1 if errors else 0)
