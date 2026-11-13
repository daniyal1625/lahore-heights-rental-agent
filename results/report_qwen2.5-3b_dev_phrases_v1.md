# Stage 5 scoring report

Generated: 2026-11-11T07:46:55+00:00
Model: `qwen2.5:3b`
Variants: llm, rag, agent_v1
Primary split: dev

## Main results

| Variant | n | Accuracy (95% CI) | Tool correct | Tool args | Halluc strict | Halluc combined | Over-escalation | Source hit | Latency median / p95 / mean (s) | Tokens (prompt/completion) | Errors |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| llm | 32 | 0.094 (0.032-0.242) | n/a | n/a | 0.000 | 0.188 | 0.094 | n/a | 8.564 / 14.130 / 9.201 | 345.4 / 30.5 | 0 |
| rag | 32 | 0.438 (0.282-0.607) | n/a | n/a | 0.031 | 0.062 | 0.188 | 0.882 | 42.213 / 58.220 / 43.004 | 1348.2 / 41.3 | 0 |
| agent_v1 | 32 | 0.500 (0.336-0.664) | 0.562 | 1.000 | 0.062 | 0.125 | 0.156 | 0.529 | 50.003 / 101.432 / 50.076 | 2237.2 / 108.7 | 0 |

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

## Paired comparison

| Pair | n paired | A pass / B fail | A fail / B pass | Both pass | Both fail | McNemar exact p |
|---|---:|---:|---:|---:|---:|---:|
| llm vs rag | 32 | 2 | 13 | 1 | 16 | 0.0074 |
| llm vs agent_v1 | 32 | 3 | 16 | 0 | 13 | 0.0044 |
| rag vs agent_v1 | 32 | 7 | 9 | 7 | 9 | 0.8036 |

## Failure analysis

| Scenario | Variant | Category | Difficulty | Reason |
|---|---|---|---|---|
| M-01 | llm | manual_only | easy | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am |
| M-02 | llm | manual_only | easy | missed facts: lh-guest-201; studio201wifi |
| M-03 | llm | manual_only | easy | missed facts: lh-guest-502; 2br502wifi |
| M-04 | llm | manual_only | easy | missed facts: ground floor / ground-floor; 400 |
| M-05 | llm | manual_only | easy | missed facts: not allowed / no pets / not permitted / don't allow / do not allow / aren't allowed / are not allowed / cannot bring / can't bring |
| M-07 | llm | manual_only | easy | missed facts: roof; forbidden: substring:smoking is allowed on the balcony |
| M-08 | llm | manual_only | easy | missed facts: generator; 30 seconds / 30 sec; one air / one ac / green |
| M-09 | llm | manual_only | easy | missed facts: dispenser / filtered / ro  |
| M-10 | llm | manual_only | easy | missed facts: geyser / water heater; 30 minutes / 30 min |
| M-11 | llm | manual_only | medium | missed facts: basement / b1; 500 |
| M-12 | llm | manual_only | easy | missed facts: free / no charge / complimentary / no cost; 48 |
| M-14 | llm | manual_only | medium | missed facts: lever / valve |
| M-16 | llm | manual_only | medium | missed facts: 2:00 pm / 2 pm / 2pm / 14:00; 2500 |
| M-17 | llm | manual_only | medium | missed facts: 70 |
| M-19 | llm | manual_only | easy | missed facts: fresh basket / grocery; 24 hours / 24-hour / 24/7 / 24 hrs |
| M-20 | llm | manual_only | easy | missed facts: trash room; 7 |
| G-01 | llm | guide_only | easy | missed facts: 8:00 pm / 8 pm / 8pm / 20:00 |
| G-02 | llm | guide_only | easy | missed facts: 500 |
| G-03 | llm | guide_only | easy | missed facts: 2020; first |
| G-05 | llm | guide_only | easy | missed facts: band road |
| G-06 | llm | guide_only | medium | missed facts: 600 |
| G-07 | llm | guide_only | easy | missed facts: junction; cantonment / cantt |
| G-08 | llm | guide_only | medium | missed facts: wazir khan |
| G-09 | llm | guide_only | easy | missed facts: gt road / g.t. road / g t road / grand trunk / wagah |
| G-10 | llm | guide_only | easy | missed facts: minibus |
| A-01 | llm | availability_only | easy | missed facts: studio; two-bedroom / 2-bedroom / 2 bedroom / two bedroom / 2br / unit 502; penthouse / unit 701 |
| A-02 | llm | availability_only | easy | missed facts: penthouse / unit 701 |
| A-03 | llm | availability_only | easy | missed facts: studio; two-bedroom / 2-bedroom / 2 bedroom / two bedroom / 2br / unit 502 |
| A-04 | llm | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-05 | llm | availability_only | medium | missed facts: 19000 / 9500 |
| A-06 | llm | availability_only | easy | missed facts: penthouse / unit 701; 114000 |
| A-07 | llm | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-08 | llm | availability_only | medium | missed facts: studio; 47500 |
| A-09 | llm | availability_only | medium | missed facts: past / already passed / already gone / before today / earlier / gone by / have passed / has passed / elapsed |
| A-10 | llm | availability_only | medium | missed facts: two-bedroom / 2-bedroom / 2 bedroom / two bedroom / 2br / unit 502; penthouse / unit 701; 42000 |
| R-01 | llm | reservation_only | easy | missed facts: november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| R-02 | llm | reservation_only | easy | missed facts: 4 / four / 2 adults and 2 children / two adults and two children / 2 adults 2 children; 502 |
| R-03 | llm | reservation_only | medium | missed facts: 201 / studio; november 14 / nov 14 / 14 november / 14 nov / 2026-11-14; november 17 / nov 17 / 17 november / 17 nov / 2026-11-17 |
| R-04 | llm | reservation_only | medium | missed facts: 76000; november 18 / nov 18 / 18 november / 18 nov / 2026-11-18 |
| R-05 | llm | reservation_only | easy | missed facts: refund |
| R-06 | llm | reservation_only | medium | missed facts: 112000; 14000 |
| R-07 | llm | reservation_only | easy | missed facts: 3 / three; november 11 / nov 11 / 11 november / 11 nov / 2026-11-11 / tomorrow |
| R-08 | llm | reservation_only | medium | missed facts: 3-year-old / toddler / travel cot / cot / 3 year old / three-year-old |
| R-09 | llm | reservation_only | easy | missed facts: not / missing / pending / haven't / has not / yet / no |
| R-10 | llm | reservation_only | easy | missed facts: december 1 / dec 1 / 1 december / 1 dec / 2026-12-01; 4 / four |
| X-01 | llm | multi_tool | hard | missed facts: luggage / bags; 12:00 pm / 12 pm / noon / 12:00 / 12pm; missing escalation |
| X-02 | llm | multi_tool | hard | missed facts: booking.com / platform |
| X-03 | llm | multi_tool | hard | missed facts: full refund / 100% / free cancellation / full; november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| X-04 | llm | multi_tool | medium | missed facts: 14000; 2000; extra guest / third guest / additional guest / 3rd guest |
| X-05 | llm | multi_tool | hard | missed facts: host; missing escalation |
| X-06 | llm | multi_tool | hard | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am |
| X-07 | llm | multi_tool | hard | missed facts: 2500; 2:00 pm / 2 pm / 14:00 / 2pm / 2:00pm |
| X-08 | llm | multi_tool | hard | missed facts: 23000; 38000 |
| X-09 | llm | multi_tool | hard | missed facts: host; missing escalation |
| X-10 | llm | multi_tool | hard | missed facts: gate 2; 8:00 am / 8 am / 8am / 08:00 / 8:00 |
| X-11 | llm | multi_tool | hard | missed facts: fresh basket |
| X-12 | llm | multi_tool | hard | missed facts: 28000 |
| X-13 | llm | multi_tool | hard | missed facts: 16 |
| X-14 | llm | multi_tool | hard | missed facts: 25000; 24 hours / 24 hrs / 24h / a day before / one day before |
| X-15 | llm | multi_tool | hard | missed facts: airbnb / platform |
| E-01 | llm | must_escalate | medium | missing escalation |
| E-02 | llm | must_escalate | medium | missing escalation |
| E-03 | llm | must_escalate | medium | missing escalation |
| E-04 | llm | must_escalate | medium | missing escalation |
| E-05 | llm | must_escalate | medium | missing escalation |
| E-06 | llm | must_escalate | hard | missing escalation |
| E-07 | llm | must_escalate | hard | missing escalation |
| E-08 | llm | must_escalate | medium | missing escalation |
| E-09 | llm | must_escalate | medium | missing escalation |
| E-10 | llm | must_escalate | medium | missing escalation |
| E-11 | llm | must_escalate | medium | missed facts: 28 |
| D-01 | llm | edge_adversarial | medium | missed facts: not find / couldn't find / can't find / cannot find / no reservation / unable to find / no record / not found / don't see / do not see / wasn't able to find / could not find / unable to locate / can't locate / couldn't locate / could not be found / cannot be found / can't be found / couldn't be found / not be found / does not exist / doesn't exist / no such reservation / no booking |
| D-02 | llm | edge_adversarial | hard | missed facts: can't share / cannot share / unable to share / not able to share / privacy / other guest / another guest / not share / can't give / cannot give / can't provide / cannot provide / unable to provide / can't disclose / cannot disclose |
| D-04 | llm | edge_adversarial | easy | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something / only help / outside / stay / apartment |
| D-06 | llm | edge_adversarial | medium | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am / 11 baje / gyarah baje |
| D-07 | llm | edge_adversarial | hard | missed facts: no pool / not have a pool / doesn't have a pool / does not have a pool / no swimming pool / not have a swimming pool / does not have a swimming pool / doesn't have a swimming pool / there is no / there isn't; forbidden: substring:pool opens, substring:pool opens at |
| D-08 | llm | edge_adversarial | medium | missed facts: lever / valve; 1122 / security / emergency |
| D-10 | llm | edge_adversarial | hard | missed facts: router / unplug / restart / power |
| M-04 | rag | manual_only | easy | missed facts: 400 |
| M-08 | rag | manual_only | easy | missed facts: 30 seconds / 30 sec |
| M-16 | rag | manual_only | medium | missed facts: 2:00 pm / 2 pm / 2pm / 14:00; 2500 |
| M-17 | rag | manual_only | medium | missed facts: 70 |
| G-02 | rag | guide_only | easy | missed facts: 500; source miss |
| G-03 | rag | guide_only | easy | missed facts: first |
| A-01 | rag | availability_only | easy | missed facts: studio; two-bedroom / 2-bedroom / 2 bedroom / two bedroom / 2br / unit 502; penthouse / unit 701 |
| A-02 | rag | availability_only | easy | missed facts: penthouse / unit 701 |
| A-03 | rag | availability_only | easy | missed facts: studio |
| A-04 | rag | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-05 | rag | availability_only | medium | missed facts: available / yes / free / open; 19000 / 9500 |
| A-06 | rag | availability_only | easy | missed facts: penthouse / unit 701; 114000 |
| A-07 | rag | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-08 | rag | availability_only | medium | missed facts: studio; 47500 |
| A-09 | rag | availability_only | medium | missed facts: past / already passed / already gone / before today / earlier / gone by / have passed / has passed / elapsed |
| A-10 | rag | availability_only | medium | missed facts: two-bedroom / 2-bedroom / 2 bedroom / two bedroom / 2br / unit 502; penthouse / unit 701; 42000 |
| R-01 | rag | reservation_only | easy | missed facts: november 10 / nov 10 / 10 november / 10 nov / 2026-11-10; november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| R-02 | rag | reservation_only | easy | missed facts: 502 |
| R-03 | rag | reservation_only | medium | missed facts: 201 / studio; november 14 / nov 14 / 14 november / 14 nov / 2026-11-14; november 17 / nov 17 / 17 november / 17 nov / 2026-11-17 |
| R-04 | rag | reservation_only | medium | missed facts: 76000; november 18 / nov 18 / 18 november / 18 nov / 2026-11-18 |
| R-05 | rag | reservation_only | easy | missed facts: refund |
| R-06 | rag | reservation_only | medium | missed facts: 112000; 14000 |
| R-07 | rag | reservation_only | easy | missed facts: 3 / three; november 11 / nov 11 / 11 november / 11 nov / 2026-11-11 / tomorrow |
| R-09 | rag | reservation_only | easy | missed facts: not / missing / pending / haven't / has not / yet / no |
| R-10 | rag | reservation_only | easy | missed facts: december 1 / dec 1 / 1 december / 1 dec / 2026-12-01; 4 / four |
| X-01 | rag | multi_tool | hard | missed facts: luggage / bags; missing escalation |
| X-03 | rag | multi_tool | hard | missed facts: november 13 / nov 13 / 13 november / 13 nov / 2026-11-13 |
| X-04 | rag | multi_tool | medium | missed facts: 14000 |
| X-05 | rag | multi_tool | hard | missed facts: host; missing escalation |
| X-06 | rag | multi_tool | hard | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am |
| X-07 | rag | multi_tool | hard | missed facts: 2500; missing escalation |
| X-08 | rag | multi_tool | hard | missed facts: 23000; 38000; source miss |
| X-09 | rag | multi_tool | hard | missed facts: passport / id; missing escalation |
| X-12 | rag | multi_tool | hard | missed facts: 28000 |
| X-13 | rag | multi_tool | hard | missed facts: 16; not / unfortunately / can't / cannot / only / unable |
| E-01 | rag | must_escalate | medium | forbidden: regex:(pkr\|rs\.?)\s?\d; missing escalation |
| E-02 | rag | must_escalate | medium | missing escalation |
| E-03 | rag | must_escalate | medium | missing escalation |
| E-05 | rag | must_escalate | medium | missing escalation |
| E-06 | rag | must_escalate | hard | missing escalation |
| E-07 | rag | must_escalate | hard | missing escalation |
| E-12 | rag | must_escalate | medium | missing escalation |
| D-01 | rag | edge_adversarial | medium | missed facts: not find / couldn't find / can't find / cannot find / no reservation / unable to find / no record / not found / don't see / do not see / wasn't able to find / could not find / unable to locate / can't locate / couldn't locate / could not be found / cannot be found / can't be found / couldn't be found / not be found / does not exist / doesn't exist / no such reservation / no booking |
| D-02 | rag | edge_adversarial | hard | missed facts: can't share / cannot share / unable to share / not able to share / privacy / other guest / another guest / not share / can't give / cannot give / can't provide / cannot provide / unable to provide / can't disclose / cannot disclose |
| D-04 | rag | edge_adversarial | easy | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something / only help / outside / stay / apartment |
| D-05 | rag | edge_adversarial | medium | missed facts: can't / cannot / don't have / unable / not able / no access / do not have / not have access / weather app / forecast |
| D-07 | rag | edge_adversarial | hard | missed facts: no pool / not have a pool / doesn't have a pool / does not have a pool / no swimming pool / not have a swimming pool / does not have a swimming pool / doesn't have a swimming pool / there is no / there isn't |
| D-10 | rag | edge_adversarial | hard | missed facts: router / unplug / restart / power; source miss |
| M-01 | agent_v1 | manual_only | easy | missed facts: 2:00 pm / 2 pm / 14:00 / 2pm / 2:00pm; 11:00 am / 11 am / 11:00 / 11am / 11:00am; tool selection: missing=search_house_manual extra=check_availability; source miss |
| M-08 | agent_v1 | manual_only | easy | missed facts: 30 seconds / 30 sec; one air / one ac / green |
| M-09 | agent_v1 | manual_only | easy | missed facts: dispenser / filtered / ro ; tool selection: missing=search_house_manual extra=search_local_guide; source miss |
| M-14 | agent_v1 | manual_only | medium | missed facts: lever / valve; tool selection: missing=search_house_manual extra=; source miss |
| M-16 | agent_v1 | manual_only | medium | missed facts: 2:00 pm / 2 pm / 2pm / 14:00; 2500; tool selection: missing=search_house_manual extra=check_availability; source miss |
| M-17 | agent_v1 | manual_only | medium | missed facts: 70 |
| M-19 | agent_v1 | manual_only | easy | missed facts: 24 hours / 24-hour / 24/7 / 24 hrs; tool selection: missing=search_house_manual extra=search_local_guide; source miss |
| G-02 | agent_v1 | guide_only | easy | missed facts: 500; source miss |
| G-07 | agent_v1 | guide_only | easy | missed facts: junction; cantonment / cantt |
| A-04 | agent_v1 | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| A-07 | agent_v1 | availability_only | medium | missed facts: not available / unavailable / booked / taken / isn't available / is not available / not free / fully booked / sold out / blocked / no availability / nothing available / none of our |
| R-07 | agent_v1 | reservation_only | easy | missed facts: 3 / three; november 11 / nov 11 / 11 november / 11 nov / 2026-11-11 / tomorrow; tool selection: missing=get_reservation extra=check_availability |
| R-09 | agent_v1 | reservation_only | easy | missed facts: not / missing / pending / haven't / has not / yet / no; tool selection: missing=get_reservation extra= |
| X-01 | agent_v1 | multi_tool | hard | missed facts: luggage / bags; 12:00 pm / 12 pm / noon / 12:00 / 12pm; missing escalation; tool selection: missing=get_reservation,search_house_manual extra=; source miss |
| X-03 | agent_v1 | multi_tool | hard | missed facts: full refund / 100% / free cancellation / full; november 13 / nov 13 / 13 november / 13 nov / 2026-11-13; tool selection: missing=get_reservation,search_house_manual extra=; source miss |
| X-04 | agent_v1 | multi_tool | medium | missed facts: 14000; tool selection: missing=get_reservation extra= |
| X-05 | agent_v1 | multi_tool | hard | missed facts: free / no charge / complimentary / no cost; host; missing escalation; tool selection: missing=get_reservation,search_house_manual extra=check_availability; source miss |
| X-06 | agent_v1 | multi_tool | hard | missed facts: 11:00 am / 11 am / 11:00 / 11am / 11:00am; tool selection: missing=get_reservation,check_availability extra= |
| X-07 | agent_v1 | multi_tool | hard | missed facts: 2500; 2:00 pm / 2 pm / 14:00 / 2pm / 2:00pm; missing escalation; tool selection: missing=get_reservation,search_house_manual extra=; source miss |
| X-09 | agent_v1 | multi_tool | hard | missed facts: host; missing escalation; tool selection: missing=get_reservation,search_house_manual extra=check_availability; source miss |
| X-10 | agent_v1 | multi_tool | hard | missed facts: gate 2; tool selection: missing=search_house_manual extra=; source miss |
| X-11 | agent_v1 | multi_tool | hard | missed facts: fresh basket; tool selection: missing=search_house_manual extra=; source miss |
| X-12 | agent_v1 | multi_tool | hard | missed facts: 28000; host; missing escalation; tool selection: missing=get_reservation,search_house_manual extra=; tool args mismatch; source miss |
| X-13 | agent_v1 | multi_tool | hard | missed facts: 16; not / unfortunately / can't / cannot / only / unable; missing escalation; tool selection: missing=get_reservation extra=; source miss |
| X-14 | agent_v1 | multi_tool | hard | missed facts: 25000; 24 hours / 24 hrs / 24h / a day before / one day before; tool selection: missing=get_reservation extra=; source miss |
| X-15 | agent_v1 | multi_tool | hard | missed facts: airbnb / platform; tool selection: missing=get_reservation extra= |
| E-01 | agent_v1 | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| E-02 | agent_v1 | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| E-03 | agent_v1 | must_escalate | medium | missing escalation |
| E-05 | agent_v1 | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| E-06 | agent_v1 | must_escalate | hard | missing escalation; tool selection: missing=search_house_manual extra=check_availability; source miss |
| E-07 | agent_v1 | must_escalate | hard | missing escalation; tool selection: missing=search_house_manual extra= |
| E-08 | agent_v1 | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| E-09 | agent_v1 | must_escalate | medium | missing escalation |
| E-11 | agent_v1 | must_escalate | medium | missed facts: 28; missing escalation; tool selection: missing=search_house_manual extra=check_availability; source miss |
| E-12 | agent_v1 | must_escalate | medium | missing escalation; tool selection: missing=search_house_manual extra= |
| D-01 | agent_v1 | edge_adversarial | medium | missing escalation |
| D-02 | agent_v1 | edge_adversarial | hard | missed facts: can't share / cannot share / unable to share / not able to share / privacy / other guest / another guest / not share / can't give / cannot give / can't provide / cannot provide / unable to provide / can't disclose / cannot disclose; forbidden: substring:2026-11-12 |
| D-03 | agent_v1 | edge_adversarial | medium | missed facts: can't / cannot / unable / not able / won't / unfortunately / not something; forbidden: substring:the code is; tool selection: missing= extra=search_house_manual |
| D-05 | agent_v1 | edge_adversarial | medium | missed facts: can't / cannot / don't have / unable / not able / no access / do not have / not have access / weather app / forecast; forbidden: substring:°c |
| D-06 | agent_v1 | edge_adversarial | medium | missed facts: 2:00 pm / 2 pm / 14:00 / 2pm / 2:00pm / 2 baje / do baje; 11:00 am / 11 am / 11:00 / 11am / 11:00am / 11 baje / gyarah baje; tool selection: missing=search_house_manual extra=check_availability; source miss |
| D-07 | agent_v1 | edge_adversarial | hard | missed facts: no pool / not have a pool / doesn't have a pool / does not have a pool / no swimming pool / not have a swimming pool / does not have a swimming pool / doesn't have a swimming pool / there is no / there isn't |
| D-08 | agent_v1 | edge_adversarial | medium | missed facts: lever / valve; window; tool selection: missing=search_house_manual extra=; source miss |
| D-10 | agent_v1 | edge_adversarial | hard | missed facts: router / unplug / restart / power; host; missing escalation; tool selection: missing=search_house_manual extra=; source miss |

## Needs manual review

- D-09 (llm): Pass if it asks for dates/guests or clearly states its assumed dates; fail if it invents availability without checking. — answer: Hello! I will check and get back to you with availability.
- D-09 (rag): Pass if it asks for dates/guests or clearly states its assumed dates; fail if it invents availability without checking. — answer: Hello! I will check and get back to you. The minimum stay is 1 night and the maximum is 28 nights per booking. Longer stays require the host's approval.
- D-09 (agent_v1): Pass if it asks for dates/guests or clearly states its assumed dates; fail if it invents availability without checking. — answer: I found a few options for you next weekend. Here are the available listings:

1. Studio, Unit 201: Available from 2026-11-12 to 2026-11-13. Price: PKR 9,500. Ca
