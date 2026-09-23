# Publishing to GitHub

This directory is the public, synthetic-only edition. Do not publish files from
the private research workspace or copy real simulator artifacts into this
repository.

## Pre-publication checks

1. Replace `tianjing111` in `README.md` with the GitHub account name. The
   preparation helper performs this replacement automatically.
2. Optionally replace `Simulation Copilot Contributors` in `LICENSE` and
   `pyproject.toml` with the maintainer's public name.
3. Run `./scripts/check.sh` and require `PUBLIC_AUDIT_PASS`. The preparation
   helper also refreshes and verifies `PUBLIC_RELEASE_MANIFEST.sha256`.
4. Review `git status --short` and confirm that `data/`, `outputs/`, model
   checkpoints, layout files and real logs are absent.

## Create the repository

Create an empty public GitHub repository named
`semiconductor-simulation-copilot`. Do not add a README, license or `.gitignore`
in the GitHub form because those files already exist locally.

The helper performs the placeholder replacement, release checks, local Git
initialization and staging. It does not commit or connect to GitHub:

```bash
./scripts/prepare_github.sh tianjing111
```

Review the output, then run:

```bash
git status --short
git commit -m "Initial public release"
git remote add origin https://github.com/tianjing111/semiconductor-simulation-copilot.git
git push -u origin main
```

GitHub may request browser authentication or a personal access token. Never put
a token in a repository file or shell script.

## Recommended repository settings

- Description: `Evidence-grounded AI copilot for semiconductor simulation workflows`
- Topics: `ai-agent`, `rag`, `scientific-computing`, `semiconductor`,
  `simulation`, `human-in-the-loop`, `python`
- Enable Actions, secret scanning and dependency alerts.
- Keep the repository public only while it contains synthetic examples.

## Before every future push

```bash
./scripts/check.sh
git diff --cached
```

Never force-add files ignored by `.gitignore` without reviewing the public data
policy and release audit.
