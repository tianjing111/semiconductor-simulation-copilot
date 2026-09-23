# Diagnostic Playbook

This public playbook uses synthetic examples. Recommendations are review steps,
not execution commands.

## Dataset and split failures

Symptoms include "No usable samples found" or a missing split name. Verify the
dataset root, inspect the split manifest, and confirm that sample identifiers
follow the expected naming contract. Do not change the split after observing
test performance.

## Checkpoint compatibility

Modern framework versions may reject serialized Python objects by default.
Confirm that the checkpoint is trusted, record the producing framework version,
and use an explicit compatibility path. Never overwrite the only checkpoint
while testing a loader change.

## Accelerator memory

First inspect current device ownership. Then reduce batch size, crop size or
activation memory. Record the changed resource configuration in the experiment
card so performance comparisons remain reproducible.

## Interrupted runs

An interrupted process is not automatically resumable. Check that the
checkpoint, optimizer state, metrics and artifact manifest are complete before
continuing from the recorded state.

