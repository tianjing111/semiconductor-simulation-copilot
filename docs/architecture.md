# Architecture

```text
browser
  -> read-only HTTP API
      -> deterministic failure classifier
      -> source-linked evidence retrieval
      -> synthetic experiment memory
      -> dry-run plan validator
      -> bounded workflow agent
          -> allowlisted tool registry
          -> optional tool-name selection
      -> optional grounded narrative generator
```

The optional language model only summarizes frozen findings and retrieved
evidence. It cannot select actions, create executable commands or modify tool
permissions. If the endpoint fails, the application uses deterministic text.

The workflow agent has a separate optional OpenAI-compatible planner. The
planner may select exactly one registered tool. It does not supply process
parameters: configuration and run identifiers come from structured application
context, and deterministic code validates them. The default planner is a local,
reproducible intent router.

## Tool boundary

| Tool | Effect |
| --- | --- |
| `search_docs` | Reads the public evidence index and returns citations. |
| `validate_config` | Validates synthetic parameters and budgets in memory. |
| `create_dry_run` | Returns argument arrays with mandatory `--dry-run`. |
| `inspect_run` | Reads synthetic experiment cards. |
| `summarize_results` | Formats frozen metrics from an experiment card. |

No tool launches a process, writes a plan to disk or changes an experiment.

## Security boundaries

- POST bodies are limited to 2 MiB.
- Uploaded text is not persisted.
- Static-file requests are checked against path traversal.
- Every retrieved source carries a SHA-256 content hash.
- The demo plan must use argument arrays and contain `--dry-run`.
- Tool names are checked against an explicit five-tool allowlist.
- Model-generated parameter values are never passed to configuration tools.
- There is no live simulator-launch endpoint.
