# Simulation Workflow Guide

The public project demonstrates a human-gated workflow. It never launches an
external simulator.

## Prepare a task

A task begins with a structured configuration containing a unique task ID,
process conditions, a declared solver-call budget and expected artifacts.
Natural-language requests must be converted into this contract before any
planning tool is called.

## Validate configuration

Validation checks required fields, parameter ranges, unique run identifiers
and the declared budget. Missing or invalid values are returned to the user;
the assistant must not invent replacements.

## Create a dry-run plan

The planner emits argument arrays rather than shell strings. Every command must
contain `--dry-run`, and every condition must set `dry_run_enforced` to true.
The plan reports how many solver calls would occur, but it cannot execute them.

## Human approval boundary

Live execution is outside the public service. A human must review the validated
configuration, evidence and budget before using a separate trusted execution
environment. Retrieval results and model text never bypass this boundary.

## Inspect task state

Task state is read from structured status and artifact records. Recognized
states are `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` and `INTERRUPTED`.
Unknown or contradictory states require manual review.

## Review results

Result review applies the acceptance rules to existing artifacts. The reviewer
reports failed rules and their evidence paths. It does not reinterpret failed
checks as successful based on a language-model summary.
