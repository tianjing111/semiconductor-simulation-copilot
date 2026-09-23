# Public Data Policy

This repository contains synthetic demonstration data only.

The public package must not contain:

- proprietary simulator binaries, APIs, manuals or configuration containers;
- production layouts, process recipes or material parameters;
- real customer, laboratory or employee identifiers;
- absolute workstation paths;
- model checkpoints or high-fidelity field arrays;
- access tokens, license-server settings or credentials.

Generated indexes inherit the same policy. Run `scripts/public_audit.py` before
every release.

