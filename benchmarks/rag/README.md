# RAG Evaluation Protocol

The benchmark is frozen before retrieval results are inspected. It uses only
the synthetic public knowledge base.

## Cases

- 22 answerable parameter, workflow, error and acceptance questions;
- 8 ambiguous requests that require clarification;
- 6 out-of-scope questions that require abstention;
- 4 questions with deliberately conflicting canonical and deprecated evidence.

## Retrieval metrics

- `Recall@5`: the expected file and section appear in the first five chunks;
- `MRR`: reciprocal rank of the first expected file-section pair.

Keyword, local TF-IDF sparse-vector and hybrid retrieval are evaluated on the
same index and questions.

## Answer metrics

- status accuracy across answered, clarification, insufficient-evidence and
  conflicting-evidence outcomes;
- citation support: an answered case cites an expected file-section pair;
- abstention accuracy on ambiguous and out-of-scope cases;
- conflict detection accuracy on the four deprecated-note cases.

This benchmark does not measure production correctness or semantic-embedding
quality. It is a small regression suite for the public portfolio system.
