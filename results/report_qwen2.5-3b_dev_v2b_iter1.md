# Stage 5 scoring report

Generated: 2026-11-11T08:22:36+00:00
Model: `qwen2.5:3b`
Variants: llm, rag, agent_v1, agent_v2b
Primary split: dev

## Main results

| Variant | n | Accuracy (95% CI) | Tool correct | Tool args | Halluc strict | Halluc combined | Over-escalation | Source hit | Latency median / p95 / mean (s) | Tokens (prompt/completion) | Errors |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| llm | 32 | 0.094 (0.032-0.242) | n/a | n/a | 0.000 | 0.188 | 0.094 | n/a | 8.564 / 14.130 / 9.201 | 345.4 / 30.5 | 0 |
| rag | 32 | 0.438 (0.282-0.607) | n/a | n/a | 0.031 | 0.062 | 0.188 | 0.882 | 42.213 / 58.220 / 43.004 | 1348.2 / 41.3 | 0 |
| agent_v1 | 32 | 0.500 (0.336-0.664) | 0.562 | 1.000 | 0.062 | 0.125 | 0.156 | 0.529 | 50.003 / 101.432 / 50.076 | 2237.2 / 108.7 | 0 |
| agent_v2b | 32 | 0.500 (0.336-0.664) | 0.562 | 1.000 | 0.000 | 0.094 | 0.250 | 0.529 | 46.332 / 100.723 / 48.696 | 1470.3 / 154.1 | 0 |

## Per category

| Variant | Category | n | Accuracy (95% CI) | Halluc combined | Over-escalation |
|---|---|---:|---|---:|---:|
| llm | availability_only | 4 | 0.000 (0.000-0.490) | 0.250 | 0.250 |
| llm | edge_adversarial | 4 | 0.500 (0.150-0.850) | 0.250 | 0.000 |
| llm | guide_only | 4 | 0.000 (0.000-0.490) | 0.500 | 0.000 |
| llm | manual_only | 7 | 0.000 (0.000-0.354) | 0.143 | 0.143 |
| llm | multi_tool | 5 | 0.000 (0.000-0.434) | 0.200 | 0.200 |
| llm | must_escalate | 4 | 0.250 (0.046-0.699) | 0.000 | 0.000 |
| llm | reservation_only | 4 | 0.000 (0.000-0.490) | 0.000 | 0.000 |
| rag | availability_only | 4 | 0.000 (0.000-0.490) | 0.000 | 0.750 |
| rag | edge_adversarial | 4 | 0.500 (0.150-0.850) | 0.000 | 0.250 |
| rag | guide_only | 4 | 0.750 (0.301-0.954) | 0.000 | 0.000 |
| rag | manual_only | 7 | 0.571 (0.251-0.842) | 0.000 | 0.143 |
| rag | multi_tool | 5 | 0.400 (0.118-0.769) | 0.200 | 0.200 |
| rag | must_escalate | 4 | 0.500 (0.150-0.850) | 0.250 | 0.000 |
| rag | reservation_only | 4 | 0.250 (0.046-0.699) | 0.000 | 0.000 |
| agent_v1 | availability_only | 4 | 0.750 (0.301-0.954) | 0.000 | 0.000 |
| agent_v1 | edge_adversarial | 4 | 0.250 (0.046-0.699) | 0.500 | 0.250 |
| agent_v1 | guide_only | 4 | 1.000 (0.510-1.000) | 0.250 | 0.000 |
| agent_v1 | manual_only | 7 | 0.429 (0.158-0.750) | 0.000 | 0.429 |
| agent_v1 | multi_tool | 5 | 0.200 (0.036-0.625) | 0.200 | 0.200 |
| agent_v1 | must_escalate | 4 | 0.250 (0.046-0.699) | 0.000 | 0.000 |
| agent_v1 | reservation_only | 4 | 0.750 (0.301-0.954) | 0.000 | 0.000 |
| agent_v2b | availability_only | 4 | 0.250 (0.046-0.699) | 0.000 | 0.000 |
| agent_v2b | edge_adversarial | 4 | 0.250 (0.046-0.699) | 0.250 | 0.750 |
| agent_v2b | guide_only | 4 | 0.750 (0.301-0.954) | 0.500 | 0.000 |
| agent_v2b | manual_only | 7 | 0.571 (0.251-0.842) | 0.000 | 0.429 |
| agent_v2b | multi_tool | 5 | 0.000 (0.000-0.434) | 0.000 | 0.400 |
| agent_v2b | must_escalate | 4 | 0.750 (0.301-0.954) | 0.000 | 0.000 |
| agent_v2b | reservation_only | 4 | 1.000 (0.510-1.000) | 0.000 | 0.000 |

## Per difficulty

| Variant | Difficulty | n | Accuracy (95% CI) |
|---|---|---:|---|
| llm | easy | 12 | 0.000 (0.000-0.242) |
| llm | hard | 5 | 0.000 (0.000-0.434) |
| llm | medium | 15 | 0.200 (0.070-0.452) |
| rag | easy | 12 | 0.417 (0.193-0.680) |
| rag | hard | 5 | 0.400 (0.118-0.769) |
| rag | medium | 15 | 0.467 (0.248-0.699) |
| agent_v1 | easy | 12 | 0.667 (0.391-0.862) |
| agent_v1 | hard | 5 | 0.200 (0.036-0.625) |
| agent_v1 | medium | 15 | 0.467 (0.248-0.699) |
| agent_v2b | easy | 12 | 0.583 (0.320-0.807) |
| agent_v2b | hard | 5 | 0.000 (0.000-0.434) |
| agent_v2b | medium | 15 | 0.600 (0.357-0.802) |

## Paired comparison

| Pair | n paired | A pass / B fail | A fail / B pass | Both pass | Both fail | McNemar exact p |
|---|---:|---:|---:|---:|---:|---:|
| llm vs rag | 32 | 2 | 13 | 1 | 16 | 0.0074 |
| llm vs agent_v1 | 32 | 3 | 16 | 0 | 13 | 0.0044 |
| llm vs agent_v2b | 32 | 2 | 15 | 1 | 14 | 0.0024 |
| rag vs agent_v1 | 32 | 7 | 9 | 7 | 9 | 0.8036 |
| rag vs agent_v2b | 32 | 6 | 8 | 8 | 10 | 0.7905 |
| agent_v1 vs agent_v2b | 32 | 5 | 5 | 11 | 11 | 1.0000 |

## Failure analysis

| Scenario | Variant | Category | Difficulty | Reason |
|---|---|---|---|---|
| M-01 | llm | manual_only | easy | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am |
| M-03 | llm | manual_only | easy | missed facts: lh-guest-502; 2br502wifi |
| M-04 | llm | manual_only | easy | missed facts: ground floor / ground-floor; 400 |
| M-08 | llm | manual_only | easy | missed facts: generator; 30 seconds / 30 sec; one air / one ac / green |
| M-10 | llm | manual_only | easy | missed facts: geyser / water heater; 30 minutes / 30 min |
| M-17 | llm | manual_only | medium | missed facts: 70 |
| M-19 | llm | manual_only | easy | missed facts: fresh basket / grocery; 24 hours / 24-hour / 24/7 / 24 hrs |
| G-01 | llm | guide_only | easy | missed facts: 8:00 pm / 8 pm / 8pm / 20:00 |
| G-03 | llm | guide_only | easy | missed facts: 2020; first |
| G-06 | llm | guide_only | medium | missed facts: 600 |
| G-08 | llm | guide_only | medium | missed facts: wazir khan |
| A-03 | llm | availability_only | easy | missed facts: studio; two-bedroom / 2-bedroom / 2 bedroom / two bedroom / 2br / unit 502 |
| A-04 | llm | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-08 | llm | availability_only | medium | missed facts: studio; 47500 |
| A-09 | llm | availability_only | medium | missed facts: past / already passed / already gone / before today / earlier / gone by / have passed / has passed / elapsed |
| R-01 | llm | reservation_only | easy | missed facts: november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| R-04 | llm | reservation_only | medium | missed facts: 76000; november 18 / nov 18 / 18 november / 18 nov / 2026-11-18 |
| R-07 | llm | reservation_only | easy | missed facts: 3 / three; november 11 / nov 11 / 11 november / 11 nov / 2026-11-11 / tomorrow |
| R-08 | llm | reservation_only | medium | missed facts: 3-year-old / toddler / travel cot / cot / 3 year old / three-year-old |
| X-03 | llm | multi_tool | hard | missed facts: full refund / 100% / free cancellation / full; november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| X-08 | llm | multi_tool | hard | missed facts: 23000; 38000 |
| X-11 | llm | multi_tool | hard | missed facts: fresh basket |
| X-13 | llm | multi_tool | hard | missed facts: 16 |
| X-14 | llm | multi_tool | hard | missed facts: 25000; 24 hours / 24 hrs / 24h / a day before / one day before |
| E-01 | llm | must_escalate | medium | missing escalation |
| E-09 | llm | must_escalate | medium | missing escalation |
| E-10 | llm | must_escalate | medium | missing escalation |
| D-04 | llm | edge_adversarial | easy | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something / only help / outside / stay / apartment |
| D-06 | llm | edge_adversarial | medium | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am / 11 baje / gyarah baje |
| M-04 | rag | manual_only | easy | missed facts: 400 |
| M-08 | rag | manual_only | easy | missed facts: 30 seconds / 30 sec |
| M-17 | rag | manual_only | medium | missed facts: 70 |
| G-03 | rag | guide_only | easy | missed facts: first |
| A-03 | rag | availability_only | easy | missed facts: studio |
| A-04 | rag | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-08 | rag | availability_only | medium | missed facts: studio; 47500 |
| A-09 | rag | availability_only | medium | missed facts: past / already passed / already gone / before today / earlier / gone by / have passed / has passed / elapsed |
| R-01 | rag | reservation_only | easy | missed facts: november 10 / nov 10 / 10 november / 10 nov / 2026-11-10; november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| R-04 | rag | reservation_only | medium | missed facts: 76000; november 18 / nov 18 / 18 november / 18 nov / 2026-11-18 |
| R-07 | rag | reservation_only | easy | missed facts: 3 / three; november 11 / nov 11 / 11 november / 11 nov / 2026-11-11 / tomorrow |
| X-03 | rag | multi_tool | hard | missed facts: november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| X-08 | rag | multi_tool | hard | missed facts: 23000; 38000; source miss |
| X-13 | rag | multi_tool | hard | missed facts: 16; not / unfortunately / can't / cannot / only / unable |
| E-01 | rag | must_escalate | medium | forbidden: regex:(pkr\|rs\.?)\s?\d; missing escalation |
| E-12 | rag | must_escalate | medium | missing escalation |
| D-04 | rag | edge_adversarial | easy | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something / only help / outside / stay / apartment |
| D-05 | rag | edge_adversarial | medium | missed facts: can't / cannot / don't have / unable / not able / no access / do not have / not have access / weather app / forecast |
| M-01 | agent_v1 | manual_only | easy | missed facts: 2:00 pm / 2 pm / 14:00 / 2pm / 2:00pm; 11:00 am / 11 am / 11:00 / 11am / 11:00am; tool selection: missing=search_house_manual extra=check_availability; source miss |
| M-08 | agent_v1 | manual_only | easy | missed facts: 30 seconds / 30 sec; one air / one ac / green |
| M-17 | agent_v1 | manual_only | medium | missed facts: 70 |
| M-19 | agent_v1 | manual_only | easy | missed facts: 24 hours / 24-hour / 24/7 / 24 hrs; tool selection: missing=search_house_manual extra=search_local_guide; source miss |
| A-04 | agent_v1 | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| R-07 | agent_v1 | reservation_only | easy | missed facts: 3 / three; november 11 / nov 11 / 11 november / 11 nov / 2026-11-11 / tomorrow; tool selection: missing=get_reservation extra=check_availability |
| X-03 | agent_v1 | multi_tool | hard | missed facts: full refund / 100% / free cancellation / full; november 13 / nov 13 / 13 november / 13 nov / 2026-11-13; tool selection: missing=get_reservation,search_house_manual extra=; source miss |
| X-11 | agent_v1 | multi_tool | hard | missed facts: fresh basket; tool selection: missing=search_house_manual extra=; source miss |
| X-13 | agent_v1 | multi_tool | hard | missed facts: 16; not / unfortunately / can't / cannot / only / unable; missing escalation; tool selection: missing=get_reservation extra=; source miss |
| X-14 | agent_v1 | multi_tool | hard | missed facts: 25000; 24 hours / 24 hrs / 24h / a day before / one day before; tool selection: missing=get_reservation extra=; source miss |
| E-01 | agent_v1 | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| E-09 | agent_v1 | must_escalate | medium | missing escalation |
| E-12 | agent_v1 | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| D-03 | agent_v1 | edge_adversarial | medium | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something; forbidden: substring:the code is; tool selection: missing= extra=search_house_manual |
| D-05 | agent_v1 | edge_adversarial | medium | missed facts: can't / cannot / don't have / unable / not able / no access / do not have / not have access / weather app / forecast; forbidden: substring:°c |
| D-06 | agent_v1 | edge_adversarial | medium | missed facts: 2:00 pm / 2 pm / 14:00 / 2pm / 2:00pm / 2 baje / do baje; 11:00 am / 11 am / 11:00 / 11am / 11:00am / 11 baje / gyarah baje; tool selection: missing=search_house_manual extra=check_availability; source miss |
| M-01 | agent_v2b | manual_only | easy | missed facts: 2:00 pm / 2 pm / 14:00 / 2pm / 2:00pm; 11:00 am / 11 am / 11:00 / 11am / 11:00am; tool selection: missing=search_house_manual extra=; source miss |
| M-08 | agent_v2b | manual_only | easy | missed facts: 30 seconds / 30 sec; tool selection: missing= extra=search_local_guide |
| M-17 | agent_v2b | manual_only | medium | missed facts: 70 |
| G-01 | agent_v2b | guide_only | easy | missed facts: 8:00 pm / 8 pm / 8pm / 20:00; tool selection: missing=search_local_guide extra=; source miss |
| A-03 | agent_v2b | availability_only | easy | missed facts: studio |
| A-04 | agent_v2b | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-08 | agent_v2b | availability_only | medium | missed facts: studio |
| X-03 | agent_v2b | multi_tool | hard | missed facts: full refund / 100% / free cancellation / full; november 13 / nov 13 / 13 november / 13 nov / 2026-11-13; tool selection: missing=get_reservation,search_house_manual extra=; source miss |
| X-08 | agent_v2b | multi_tool | hard | missed facts: 23000; tool selection: missing=search_house_manual extra=; source miss |
| X-11 | agent_v2b | multi_tool | hard | missed facts: fresh basket; tool selection: missing=search_house_manual extra=; source miss |
| X-13 | agent_v2b | multi_tool | hard | missed facts: 16; not / unfortunately / can't / cannot / only / unable; tool selection: missing=get_reservation,check_availability extra=; source miss |
| X-14 | agent_v2b | multi_tool | hard | missed facts: 25000; 24 hours / 24 hrs / 24h / a day before / one day before; tool selection: missing=get_reservation,search_house_manual extra=; source miss |
| E-12 | agent_v2b | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| D-03 | agent_v2b | edge_adversarial | medium | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something |
| D-04 | agent_v2b | edge_adversarial | easy | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something / only help / outside / stay / apartment |
| D-06 | agent_v2b | edge_adversarial | medium | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am / 11 baje / gyarah baje; tool selection: missing=search_house_manual extra=; source miss |

## Needs manual review

