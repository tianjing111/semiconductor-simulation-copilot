# Architecture

```text
browser
  -> read-only HTTP API
      -> deterministic failure classifier
      -> source-linked evidence retrieval
      -> synthetic experiment memory
      -> dry-run plan validator
      -> optional grounded narrative generator
```

The optional language model only summarizes frozen findings and retrieved
evidence. It cannot select actions, create executable commands or modify tool
permissions. If the endpoint fails, the application uses deterministic text.

## Security boundaries

- POST bodies are limited to 2 MiB.
- Uploaded text is not persisted.
- Static-file requests are checked against path traversal.
- Every retrieved source carries a SHA-256 content hash.
- The demo plan must use argument arrays and contain `--dry-run`.
- There is no live simulator-launch endpoint.

