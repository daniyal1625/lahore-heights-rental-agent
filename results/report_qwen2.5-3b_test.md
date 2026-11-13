# Stage 5 scoring report

Generated: 2026-11-12T11:48:01+00:00
Model: `qwen2.5:3b`
Variants: llm, rag, agent_v1, agent_v2b
Primary split: test

## Main results

| Variant | n | Accuracy (95% CI) | Tool correct | Tool args | Halluc strict | Halluc combined | Over-escalation | Source hit | Latency median / p95 / mean (s) | Tokens (prompt/completion) | Errors |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| llm | 55 | 0.093 (0.040-0.199) | n/a | n/a | 0.036 | 0.182 | 0.073 | n/a | 7.777 / 14.889 / 8.781 | 345.0 / 26.8 | 0 |
| rag | 55 | 0.407 (0.287-0.540) | n/a | n/a | 0.000 | 0.036 | 0.145 | 0.914 | 43.339 / 59.473 / 44.729 | 1385.5 / 40.6 | 0 |
| agent_v1 | 55 | 0.481 (0.354-0.612) | 0.600 | 0.982 | 0.018 | 0.091 | 0.000 | 0.571 | 41.034 / 79.852 / 44.533 | 2196.3 / 92.4 | 0 |
| agent_v2b | 55 | 0.518 (0.389-0.646) | 0.654 | 0.927 | 0.000 | 0.000 | 0.091 | 0.714 | 46.556 / 158.308 / 61.891 | 2820.6 / 187.1 | 0 |

## Per category

| Variant | Category | n | Accuracy (95% CI) | Halluc combined | Over-escalation |
|---|---|---:|---|---:|---:|
| llm | availability_only | 6 | 0.000 (0.000-0.390) | 0.167 | 0.167 |
| llm | edge_adversarial | 6 | 0.000 (0.000-0.434) | 0.167 | 0.333 |
| llm | guide_only | 6 | 0.167 (0.030-0.564) | 0.167 | 0.000 |
| llm | manual_only | 13 | 0.308 (0.127-0.576) | 0.231 | 0.000 |
| llm | multi_tool | 10 | 0.000 (0.000-0.278) | 0.200 | 0.100 |
| llm | must_escalate | 8 | 0.000 (0.000-0.324) | 0.000 | 0.000 |
| llm | reservation_only | 6 | 0.000 (0.000-0.390) | 0.333 | 0.000 |
| rag | availability_only | 6 | 0.000 (0.000-0.390) | 0.167 | 0.500 |
| rag | edge_adversarial | 6 | 0.200 (0.036-0.625) | 0.000 | 0.333 |
| rag | guide_only | 6 | 0.833 (0.436-0.970) | 0.000 | 0.167 |
| rag | manual_only | 13 | 0.923 (0.667-0.986) | 0.000 | 0.000 |
| rag | multi_tool | 10 | 0.300 (0.108-0.603) | 0.000 | 0.100 |
| rag | must_escalate | 8 | 0.125 (0.022-0.471) | 0.125 | 0.000 |
| rag | reservation_only | 6 | 0.000 (0.000-0.390) | 0.000 | 0.167 |
| agent_v1 | availability_only | 6 | 0.833 (0.436-0.970) | 0.167 | 0.000 |
| agent_v1 | edge_adversarial | 6 | 0.000 (0.000-0.434) | 0.167 | 0.000 |
| agent_v1 | guide_only | 6 | 0.667 (0.300-0.903) | 0.000 | 0.000 |
| agent_v1 | manual_only | 13 | 0.769 (0.497-0.918) | 0.077 | 0.000 |
| agent_v1 | multi_tool | 10 | 0.100 (0.018-0.404) | 0.200 | 0.000 |
| agent_v1 | must_escalate | 8 | 0.125 (0.022-0.471) | 0.000 | 0.000 |
| agent_v1 | reservation_only | 6 | 0.833 (0.436-0.970) | 0.000 | 0.000 |
| agent_v2b | availability_only | 6 | 0.500 (0.188-0.812) | 0.000 | 0.000 |
| agent_v2b | edge_adversarial | 6 | 0.400 (0.118-0.769) | 0.000 | 0.167 |
| agent_v2b | guide_only | 6 | 0.833 (0.436-0.970) | 0.000 | 0.000 |
| agent_v2b | manual_only | 13 | 0.846 (0.578-0.957) | 0.000 | 0.077 |
| agent_v2b | multi_tool | 10 | 0.100 (0.018-0.404) | 0.000 | 0.100 |
| agent_v2b | must_escalate | 8 | 0.375 (0.137-0.694) | 0.000 | 0.000 |
| agent_v2b | reservation_only | 6 | 0.500 (0.188-0.812) | 0.000 | 0.333 |

## Per difficulty

| Variant | Difficulty | n | Accuracy (95% CI) |
|---|---|---:|---|
| llm | easy | 23 | 0.217 (0.097-0.419) |
| llm | hard | 14 | 0.000 (0.000-0.215) |
| llm | medium | 18 | 0.000 (0.000-0.184) |
| rag | easy | 23 | 0.652 (0.449-0.812) |
| rag | hard | 14 | 0.214 (0.076-0.476) |
| rag | medium | 18 | 0.235 (0.096-0.473) |
| agent_v1 | easy | 23 | 0.826 (0.629-0.930) |
| agent_v1 | hard | 14 | 0.071 (0.013-0.315) |
| agent_v1 | medium | 18 | 0.353 (0.173-0.587) |
| agent_v2b | easy | 23 | 0.739 (0.535-0.875) |
| agent_v2b | hard | 14 | 0.286 (0.117-0.546) |
| agent_v2b | medium | 18 | 0.412 (0.216-0.640) |

## Paired comparison

| Pair | n paired | A pass / B fail | A fail / B pass | Both pass | Both fail | McNemar exact p |
|---|---:|---:|---:|---:|---:|---:|
| llm vs rag | 54 | 0 | 17 | 5 | 32 | 0.0000 |
| llm vs agent_v1 | 54 | 0 | 21 | 5 | 28 | 0.0000 |
| llm vs agent_v2b | 54 | 0 | 23 | 5 | 26 | 0.0000 |
| rag vs agent_v1 | 54 | 7 | 11 | 15 | 21 | 0.4807 |
| rag vs agent_v2b | 54 | 5 | 11 | 17 | 21 | 0.2101 |
| agent_v1 vs agent_v2b | 54 | 6 | 8 | 20 | 20 | 0.7905 |

## Per-scenario details

Omitted: this split reports aggregates only.
