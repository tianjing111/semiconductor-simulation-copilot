# Synthetic Error Catalog

These signatures are intentionally generic and are paired with bounded human
actions.

## No usable samples

The message `No usable samples found` indicates that the dataset root, split
manifest or sample identifiers do not satisfy the loader contract. Check those
three inputs before rerunning. Do not change a test split after observing test
performance.

## Checkpoint load rejected

`Weights only load failed` indicates a checkpoint compatibility or trust
boundary. Confirm that the checkpoint came from a trusted source and record
the producing framework version. Never disable safe loading for an untrusted
checkpoint.

## Resource exhaustion

`CUDA out of memory` indicates that requested device memory exceeded available
capacity. First inspect current device occupancy, then reduce batch size or
field resolution. Do not terminate unrelated processes automatically.

## Missing artifact

A completed task with a missing declared artifact fails acceptance. Confirm
the expected artifact path and producing stage. Do not fabricate an empty file
to satisfy the manifest.

## Interrupted task

An `INTERRUPTED` task is not complete even when partial artifacts exist. Record
the interruption, preserve available logs and require an explicit decision to
resume or restart.

## Budget exceeded

If planned solver calls exceed `max_solver_calls`, planning must stop before a
command is approved. Increasing the budget requires a new human-reviewed task
configuration.
