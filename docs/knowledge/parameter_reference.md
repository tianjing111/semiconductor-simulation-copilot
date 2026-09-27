# Synthetic Parameter Reference

This reference defines parameters for the bundled public demonstration only.
The values are not process recommendations and do not describe a commercial
simulator.

## Dose

`dose` is a scalar exposure-control variable expressed in arbitrary units in
the public demo. The accepted demonstration range is 40 to 50 inclusive. A
value outside this interval must fail configuration validation rather than be
silently clipped.

## Focus

`focus` is a signed focal-offset variable expressed in arbitrary units. The
accepted demonstration range is -0.05 to +0.05 inclusive. Negative and
positive values must retain their sign in run identifiers and audit records.

## Grid size

`grid_size` controls the square field resolution. Supported public values are
64, 128 and 256. Larger values are deliberately unsupported because this demo
does not model production memory requirements.

## Simulation budget

`max_solver_calls` is the maximum number of external solver invocations a plan
would require if it were approved outside this public service. The demo budget
must be a positive integer no greater than 25. Planning fails when the sum of
`solver_calls_if_live` exceeds this declared budget.

## Run identifiers

Every condition requires a unique `run_id`. Identifiers may contain lowercase
letters, digits and underscores. Reusing a run identifier is invalid because
it makes provenance and artifact ownership ambiguous.
