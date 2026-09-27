# RAG Evaluation Report

This report is generated from the frozen synthetic 40-question benchmark.
It is a regression result, not a production-quality claim.

## Retrieval

| Mode | Cases | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| keyword | 26 | 0.885 | 0.686 |
| tfidf | 26 | 1.000 | 0.933 |
| hybrid | 26 | 1.000 | 0.926 |

## Grounded answering

| Metric | Value |
| --- | ---: |
| Status accuracy | 1.000 |
| Citation support rate | 1.000 |
| Abstention accuracy | 1.000 |
| Conflict detection accuracy | 1.000 |

## Failed cases

No failures on the frozen public regression set.

Full per-case outputs are available in `results.json`.
