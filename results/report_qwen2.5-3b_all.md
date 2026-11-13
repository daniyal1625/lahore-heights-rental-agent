# Stage 5 scoring report

Generated: 2026-11-12T11:48:43+00:00
Model: `qwen2.5:3b`
Variants: llm, rag, agent_v1, agent_v2b
Primary split: all

## Main results

| Variant | n | Accuracy (95% CI) | Tool correct | Tool args | Halluc strict | Halluc combined | Over-escalation | Source hit | Latency median / p95 / mean (s) | Tokens (prompt/completion) | Errors |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| llm | 87 | 0.093 (0.048-0.173) | n/a | n/a | 0.023 | 0.184 | 0.058 | n/a | 7.835 / 14.853 / 8.936 | 345.1 / 28.1 | 0 |
| rag | 87 | 0.395 (0.299-0.501) | n/a | n/a | 0.011 | 0.046 | 0.126 | 0.904 | 42.738 / 58.992 / 44.095 | 1371.8 / 40.9 | 0 |
| agent_v1 | 87 | 0.477 (0.374-0.581) | 0.586 | 0.989 | 0.035 | 0.103 | 0.023 | 0.558 | 42.771 / 83.057 / 46.572 | 2211.3 / 98.4 | 0 |
| agent_v2b | 87 | 0.535 (0.430-0.636) | 0.678 | 0.931 | 0.000 | 0.023 | 0.126 | 0.731 | 47.175 / 178.375 / 69.369 | 2911.7 / 210.3 | 0 |

## Per category

| Variant | Category | n | Accuracy (95% CI) | Halluc combined | Over-escalation |
|---|---|---:|---|---:|---:|
| llm | availability_only | 10 | 0.000 (0.000-0.278) | 0.200 | 0.200 |
| llm | edge_adversarial | 10 | 0.222 (0.063-0.547) | 0.200 | 0.200 |
| llm | guide_only | 10 | 0.100 (0.018-0.404) | 0.300 | 0.000 |
| llm | manual_only | 20 | 0.200 (0.081-0.416) | 0.200 | 0.000 |
| llm | multi_tool | 15 | 0.000 (0.000-0.204) | 0.200 | 0.067 |
| llm | must_escalate | 12 | 0.083 (0.015-0.354) | 0.000 | 0.000 |
| llm | reservation_only | 10 | 0.000 (0.000-0.278) | 0.200 | 0.000 |
| rag | availability_only | 10 | 0.000 (0.000-0.278) | 0.100 | 0.400 |
| rag | edge_adversarial | 10 | 0.333 (0.121-0.646) | 0.000 | 0.300 |
| rag | guide_only | 10 | 0.800 (0.490-0.943) | 0.000 | 0.100 |
| rag | manual_only | 20 | 0.800 (0.584-0.919) | 0.000 | 0.000 |
| rag | multi_tool | 15 | 0.333 (0.152-0.583) | 0.067 | 0.133 |
| rag | must_escalate | 12 | 0.083 (0.015-0.354) | 0.167 | 0.000 |
| rag | reservation_only | 10 | 0.100 (0.018-0.404) | 0.000 | 0.100 |
| agent_v1 | availability_only | 10 | 0.800 (0.490-0.943) | 0.100 | 0.000 |
| agent_v1 | edge_adversarial | 10 | 0.111 (0.020-0.435) | 0.300 | 0.100 |
| agent_v1 | guide_only | 10 | 0.800 (0.490-0.943) | 0.100 | 0.000 |
| agent_v1 | manual_only | 20 | 0.650 (0.433-0.819) | 0.050 | 0.000 |
| agent_v1 | multi_tool | 15 | 0.133 (0.037-0.379) | 0.200 | 0.067 |
| agent_v1 | must_escalate | 12 | 0.083 (0.015-0.354) | 0.000 | 0.000 |
| agent_v1 | reservation_only | 10 | 0.800 (0.490-0.943) | 0.000 | 0.000 |
| agent_v2b | availability_only | 10 | 0.500 (0.237-0.763) | 0.100 | 0.100 |
| agent_v2b | edge_adversarial | 10 | 0.444 (0.189-0.733) | 0.000 | 0.400 |
| agent_v2b | guide_only | 10 | 0.700 (0.397-0.892) | 0.000 | 0.000 |
| agent_v2b | manual_only | 20 | 0.800 (0.584-0.919) | 0.000 | 0.050 |
| agent_v2b | multi_tool | 15 | 0.200 (0.070-0.452) | 0.067 | 0.133 |
| agent_v2b | must_escalate | 12 | 0.417 (0.193-0.680) | 0.000 | 0.000 |
| agent_v2b | reservation_only | 10 | 0.600 (0.313-0.832) | 0.000 | 0.300 |

## Per difficulty

| Variant | Difficulty | n | Accuracy (95% CI) |
|---|---|---:|---|
| llm | easy | 35 | 0.143 (0.063-0.294) |
| llm | hard | 19 | 0.000 (0.000-0.168) |
| llm | medium | 33 | 0.094 (0.032-0.242) |
| rag | easy | 35 | 0.571 (0.409-0.720) |
| rag | hard | 19 | 0.263 (0.118-0.488) |
| rag | medium | 33 | 0.281 (0.156-0.454) |
| agent_v1 | easy | 35 | 0.771 (0.610-0.879) |
| agent_v1 | hard | 19 | 0.105 (0.029-0.314) |
| agent_v1 | medium | 33 | 0.375 (0.229-0.547) |
| agent_v2b | easy | 35 | 0.714 (0.549-0.837) |
| agent_v2b | hard | 19 | 0.316 (0.154-0.540) |
| agent_v2b | medium | 33 | 0.469 (0.309-0.635) |

## Paired comparison

| Pair | n paired | A pass / B fail | A fail / B pass | Both pass | Both fail | McNemar exact p |
|---|---:|---:|---:|---:|---:|---:|
| llm vs rag | 86 | 2 | 28 | 6 | 50 | 0.0000 |
| llm vs agent_v1 | 86 | 3 | 36 | 5 | 42 | 0.0000 |
| llm vs agent_v2b | 86 | 2 | 40 | 6 | 38 | 0.0000 |
| rag vs agent_v1 | 86 | 13 | 20 | 21 | 32 | 0.2962 |
| rag vs agent_v2b | 86 | 7 | 19 | 27 | 33 | 0.0290 |
| agent_v1 vs agent_v2b | 86 | 13 | 18 | 28 | 27 | 0.4731 |

## Per-scenario details

Omitted: this split reports aggregates only.
