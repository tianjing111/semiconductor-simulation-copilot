# Bounded Tool-Use Benchmark

This synthetic 30-task regression set evaluates workflow routing and safety,
not semiconductor expertise or production autonomy. It covers six knowledge
requests, six configuration checks, six dry-run plans, six run inspections and
six result summaries.

Three policies are compared:

1. `fixed_dispatch` receives an explicit task family and calls the matching
   deterministic tool. It is an intentionally strong workflow baseline.
2. `bounded_router_no_rag` routes natural language but withholds retrieved
   evidence for knowledge questions.
3. `bounded_router_rag` routes natural language and can use the grounded
   knowledge tool.

Metrics are tool-selection accuracy, expected-status accuracy, citation
support on answerable knowledge tasks, unsafe tool calls and mean tool calls.
The benchmark is frozen before release and contains synthetic inputs only.
