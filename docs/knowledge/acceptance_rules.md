# Synthetic Result Acceptance Rules

Acceptance is a deterministic check over structured records and existing
artifacts. Language-model output cannot override these rules.

## Completion state

The task status must be exactly `COMPLETED`. `RUNNING`, `FAILED`, `INTERRUPTED`
or an unknown state cannot pass final acceptance. The presence of an output
file alone does not prove completion.

## Required artifacts

Every artifact declared by the task contract must exist, be non-empty and have
a recorded SHA-256 digest. Undeclared extra files do not replace a missing
required artifact.

## Finite metrics

Required metrics must parse as finite numeric values. `NaN`, positive infinity,
negative infinity and missing values fail acceptance.

## Budget compliance

Observed solver calls must not exceed `max_solver_calls`. A scientifically
valid result can still fail operational acceptance when it violates the frozen
budget.

## Provenance completeness

The result must identify its task ID, configuration digest, code revision and
artifact manifest. Missing provenance produces `REVIEW_REQUIRED`, not `PASS`.

## Acceptance outcome

`PASS` requires every mandatory rule to pass. Any failed mandatory rule yields
`FAIL`; incomplete or conflicting evidence yields `REVIEW_REQUIRED`. The report
must list each rule, status and supporting source.
