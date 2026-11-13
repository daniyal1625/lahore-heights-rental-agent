# Retrieval evaluation

Generated: 2026-11-11T04:34:34+00:00

## Configuration

- Embedding model: `BAAI/bge-small-en-v1.5`
- Chroma directory: `<project-root>\.chroma`
- Evaluation k: 5
- Hybrid fusion: weighted Reciprocal Rank Fusion, k=60 (dense weight 1.5, BM25 weight 1.0)
- Hybrid candidate depth: manual 5, guide 20
- Scenarios: 87
- Index build time: not rebuilt

## Index

| Source | Chunks | Avg words | Max words | Min words |
|---|---:|---:|---:|---:|
| Manual | 100 | 81.67 | 218 | 27 |
| Guide | 56 | 166.64 | 240 | 17 |
| **Total** | **156** | — | — | — |

## Dense vs hybrid

| Source | Category | n | Mode | hit@1 | hit@3 | hit@5 | recall@5 | MRR |
|---|---|---:|---|---:|---:|---:|---:|---:|
| Manual | overall | 42 | dense | 0.786 | 0.929 | 0.976 | 0.905 | 0.859 |
| Manual | overall | 42 | hybrid | 0.786 | 0.929 | 0.976 | 0.905 | 0.864 |
| Manual | edge_adversarial | 4 | dense | 0.250 | 0.750 | 1.000 | 0.750 | 0.508 |
| Manual | edge_adversarial | 4 | hybrid | 0.250 | 0.750 | 1.000 | 0.750 | 0.562 |
| Manual | manual_only | 20 | dense | 0.850 | 0.950 | 0.950 | 0.900 | 0.900 |
| Manual | manual_only | 20 | hybrid | 0.850 | 0.950 | 0.950 | 0.900 | 0.900 |
| Manual | multi_tool | 15 | dense | 0.867 | 0.933 | 1.000 | 0.967 | 0.913 |
| Manual | multi_tool | 15 | hybrid | 0.933 | 0.933 | 1.000 | 0.967 | 0.947 |
| Manual | must_escalate | 3 | dense | 0.667 | 1.000 | 1.000 | 0.833 | 0.778 |
| Manual | must_escalate | 3 | hybrid | 0.333 | 1.000 | 1.000 | 0.833 | 0.611 |
| Guide | overall | 12 | dense | 0.667 | 0.833 | 0.833 | — | 0.722 |
| Guide | overall | 12 | hybrid | 0.667 | 0.833 | 0.917 | — | 0.739 |
| Guide | guide_only | 10 | dense | 0.700 | 0.900 | 0.900 | — | 0.767 |
| Guide | guide_only | 10 | hybrid | 0.700 | 0.900 | 0.900 | — | 0.767 |
| Guide | multi_tool | 2 | dense | 0.500 | 0.500 | 0.500 | — | 0.500 |
| Guide | multi_tool | 2 | hybrid | 0.500 | 0.500 | 1.000 | — | 0.600 |

### Guide union fallback

- Dense: single-chunk hit@5 = 10 scenarios; union fallback = 0; miss@5 = 2.
- Hybrid: single-chunk hit@5 = 11 scenarios; union fallback = 0; miss@5 = 1.

### Guide hit types (dense)

| Scenario | Category | hit@5 type | Missing evidence |
|---|---|---|---|
| G-01 | guide_only | single | — |
| G-02 | guide_only | miss | non-pakistanis |
| G-03 | guide_only | single | — |
| G-04 | guide_only | single | — |
| G-05 | guide_only | single | — |
| G-06 | guide_only | single | — |
| G-07 | guide_only | single | — |
| G-08 | guide_only | single | — |
| G-09 | guide_only | single | — |
| G-10 | guide_only | single | — |
| X-10 | multi_tool | single | — |
| X-11 | multi_tool | miss | wazir khan |

### Guide hit types (hybrid)

| Scenario | Category | hit@5 type | Missing evidence |
|---|---|---|---|
| G-01 | guide_only | single | — |
| G-02 | guide_only | miss | non-pakistanis |
| G-03 | guide_only | single | — |
| G-04 | guide_only | single | — |
| G-05 | guide_only | single | — |
| G-06 | guide_only | single | — |
| G-07 | guide_only | single | — |
| G-08 | guide_only | single | — |
| G-09 | guide_only | single | — |
| G-10 | guide_only | single | — |
| X-10 | multi_tool | single | — |
| X-11 | multi_tool | single | — |

## Query latency

| Mode | Scope | Queries | Median ms | p95 ms | Min ms | Max ms |
|---|---|---:|---:|---:|---:|---:|
| dense | overall | 54 | 67.90 | 76.03 | 55.87 | 3061.50 |
| dense | manual | 42 | 66.98 | 74.55 | 55.87 | 3061.50 |
| dense | guide | 12 | 71.47 | 79.83 | 64.48 | 84.42 |
| hybrid | overall | 54 | 67.47 | 83.07 | 48.38 | 95.56 |
| hybrid | manual | 42 | 68.00 | 83.17 | 48.38 | 95.56 |
| hybrid | guide | 12 | 63.87 | 77.98 | 49.62 | 79.32 |

## 10 hardest cases (dense)

True hit@5 misses first; the table is filled with the lowest-MRR near misses when fewer than 10 queries miss.

| # | Miss? | MRR | Source | Scenario | Query | Expected | Top 3 retrieved (label — score) |
|---:|---|---:|---|---|---|---|---|
| 1 | yes | 0.000 | manual | M-18 | Do you provide a hair dryer and an iron? | 4.1; 4.2; 4.3; 4.4 | 8.3 (Supplies) — 0.5715; 9.1 (Washing your clothes) — 0.5564; 9.2 (Linens and towels) — 0.5549 |
| 2 | yes | 0.000 | guide | G-02 | How much does Lahore Fort cost for a foreign tourist? | non-pakistanis; 500 | Lahore (Lahore) — 0.7131; Lahore > Sleep > Budget (Budget) — 0.7071; Lahore (Lahore) — 0.6999 |
| 3 | yes | 0.000 | guide | X-11 | Where can we buy groceries nearby, and what should we see in the Walled City? | wazir khan; lahore fort | Lahore > Eat > Budget (Budget) — 0.6274; Lahore > See > Walled City (Walled City) — 0.6168; Lahore > Buy > Other (Other) — 0.6152 |
| 4 | near | 0.200 | manual | D-06 | Assalam o alaikum, check-in ka time kya hai aur check-out kab karna hai? | 3.5; 14.1 | 20.5 (First-time visitors to Pakistan) — 0.6084; 17 (Nearby Essentials (the host's short list)) — 0.6060; 21 (Key Facts at a Glance) — 0.6038 |
| 5 | near | 0.200 | manual | X-08 | Do you have a place for 5 of us on Nov 12-13, and what would it cost? | 2.2 | 18 (Quick FAQ) — 0.5682; 2.7 (Changing or extending your stay) — 0.5621; 14.3 (Late check-out) — 0.5584 |
| 6 | near | 0.333 | guide | G-08 | Is Lahore Fort a UNESCO site? And what else is there to see in the Walled City? | unesco; wazir khan | Lahore > See > Walled City (Walled City) — 0.7952; Lahore (Lahore) — 0.7888; Lahore (Lahore) — 0.7660 |
| 7 | near | 0.333 | guide | G-09 | Where are the Shalimar Gardens? | shalimar gardens; wagah | Lahore (Lahore) — 0.6390; Lahore (Lahore) — 0.6337; Lahore > See > Other sights (Other sights) — 0.6121 |
| 8 | near | 0.333 | manual | D-10 | This is unacceptable!! The wifi has been down for an hour and I'm working. I want a refund right now. | 5.1; 2.8 | 13.2 (How fast we respond) — 0.6065; 13.3 (Quick fixes) — 0.6057; 5.1 (Wi-Fi) — 0.6018 |
| 9 | near | 0.333 | manual | E-06 | The AC in our bedroom didn't cool properly last night. Can I get a refund for one night? | 2.8; 13.3 | 18 (Quick FAQ) — 0.6557; 2.6 (Cancellation policy) — 0.6485; 13.3 (Quick fixes) — 0.6472 |
| 10 | near | 0.500 | manual | D-07 | I read in your manual that there's a rooftop swimming pool. What time does it open? | 10.2; 10.3 | 18 (Quick FAQ) — 0.6719; 10.3 (What the building does not have) — 0.6665; 7.4 (Water supply) — 0.6378 |

## 10 hardest cases (hybrid)

True hit@5 misses first; the table is filled with the lowest-MRR near misses when fewer than 10 queries miss.

| # | Miss? | MRR | Source | Scenario | Query | Expected | Top 3 retrieved (label — score) |
|---:|---|---:|---|---|---|---|---|
| 1 | yes | 0.000 | manual | M-18 | Do you provide a hair dryer and an iron? | 4.1; 4.2; 4.3; 4.4 | 8.3 (Supplies) — 0.0405; 8.1 (Cooking equipment) — 0.0395; 9.1 (Washing your clothes) — 0.0242 |
| 2 | yes | 0.000 | guide | G-02 | How much does Lahore Fort cost for a foreign tourist? | non-pakistanis; 500 | Lahore (Lahore) — 0.0400; Lahore > Do (Do) — 0.0395; Lahore > Sleep > Budget (Budget) — 0.0393 |
| 3 | near | 0.200 | guide | X-11 | Where can we buy groceries nearby, and what should we see in the Walled City? | wazir khan; lahore fort | Lahore > See > Walled City (Walled City) — 0.0383; Lahore > Buy > Other (Other) — 0.0373; Lahore > Buy > Other (Other) — 0.0373 |
| 4 | near | 0.200 | manual | X-08 | Do you have a place for 5 of us on Nov 12-13, and what would it cost? | 2.2 | 18 (Quick FAQ) — 0.0246; 2.7 (Changing or extending your stay) — 0.0242; 14.3 (Late check-out) — 0.0238 |
| 5 | near | 0.250 | manual | D-10 | This is unacceptable!! The wifi has been down for an hour and I'm working. I want a refund right now. | 5.1; 2.8 | 18 (Quick FAQ) — 0.0398; 13.2 (How fast we respond) — 0.0246; 13.3 (Quick fixes) — 0.0242 |
| 6 | near | 0.333 | guide | G-08 | Is Lahore Fort a UNESCO site? And what else is there to see in the Walled City? | unesco; wazir khan | Lahore > See > Walled City (Walled City) — 0.0410; Lahore (Lahore) — 0.0403; Lahore (Lahore) — 0.0397 |
| 7 | near | 0.333 | guide | G-09 | Where are the Shalimar Gardens? | shalimar gardens; wagah | Lahore (Lahore) — 0.0406; Lahore > See > Other sights (Other sights) — 0.0399; Lahore (Lahore) — 0.0395 |
| 8 | near | 0.333 | manual | E-06 | The AC in our bedroom didn't cool properly last night. Can I get a refund for one night? | 2.8; 13.3 | 18 (Quick FAQ) — 0.0410; 2.6 (Cancellation policy) — 0.0242; 13.3 (Quick fixes) — 0.0238 |
| 9 | near | 0.500 | manual | D-06 | Assalam o alaikum, check-in ka time kya hai aur check-out kab karna hai? | 3.5; 14.1 | 21 (Key Facts at a Glance) — 0.0399; 14.1 (Check-out time) — 0.0395; 18 (Quick FAQ) — 0.0391 |
| 10 | near | 0.500 | manual | D-07 | I read in your manual that there's a rooftop swimming pool. What time does it open? | 10.2; 10.3 | 18 (Quick FAQ) — 0.0410; 10.3 (What the building does not have) — 0.0403; 7.4 (Water supply) — 0.0394 |
