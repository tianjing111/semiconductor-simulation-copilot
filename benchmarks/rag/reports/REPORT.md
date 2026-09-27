# RAG Evaluation Report

This report is generated from the frozen synthetic 40-question benchmark.
It is a regression result, not a production-quality claim.

## Retrieval

| Mode | Cases | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| keyword | 26 | 0.846 | 0.629 |
| tfidf | 26 | 1.000 | 0.912 |
| hybrid | 26 | 0.962 | 0.859 |

## Grounded answering

| Metric | Value |
| --- | ---: |
| Status accuracy | 1.000 |
| Citation support rate | 1.000 |
| Abstention accuracy | 1.000 |
| Conflict detection accuracy | 1.000 |

## Failed cases

| Case | Expected | Observed | Hybrid retrieval | Citation |
| --- | --- | --- | --- | --- |
| rag-004 | ANSWERED | ANSWERED | False | True |

Full per-case outputs are available in `results.json`.
