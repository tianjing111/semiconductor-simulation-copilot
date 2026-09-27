# Bounded Tool-Use Evaluation

This generated report covers a frozen synthetic 30-task regression set.
It does not measure production autonomy or semiconductor expertise.

| Policy | Tasks | Tool selection | Expected status | Citation support | Unsafe calls | Mean calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed_dispatch | 30 | 1.000 | 1.000 | 1.000 | 0 | 1.00 |
| bounded_router_no_rag | 30 | 1.000 | 0.800 | 0.833 | 0 | 1.00 |
| bounded_router_rag | 30 | 1.000 | 1.000 | 1.000 | 0 | 1.00 |

## Interpretation

The fixed workflow remains a strong option when intent is already structured.
Natural-language routing does not replace deterministic validation. Retrieval
adds source support to open-ended knowledge requests, while all parameter and
safety decisions remain in code.

## Limitations

- The benchmark is a deterministic public regression set, not a production workload.
- The optional OpenAI-compatible planner is not scored without a configured endpoint.
- Fixed dispatch receives the explicit task family and is an intentionally strong baseline.
