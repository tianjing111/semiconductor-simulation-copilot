from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DiagnosticRule:
    pattern: re.Pattern[str]
    category: str
    severity: str
    message: str
    action: str
    confidence: str = "HIGH"


RULES = (
    DiagnosticRule(
        re.compile(r"No usable samples found|No samples found|split .* not found", re.I),
        "data_split_contract", "high",
        "The dataset and split contract produced no usable samples.",
        "Check the dataset root, split manifest, and sample identifiers before rerunning.",
    ),
    DiagnosticRule(
        re.compile(r"Weights only load failed|UnpicklingError|Unsupported global", re.I),
        "checkpoint_compatibility", "high",
        "The runtime rejected the checkpoint serialization contract.",
        "Verify the trusted checkpoint format and framework version without overwriting the source artifact.",
    ),
    DiagnosticRule(
        re.compile(r"CUDA out of memory|out of memory", re.I),
        "accelerator_memory", "high",
        "The run exceeded available accelerator memory.",
        "Review current device ownership, then reduce batch size or spatial workload.",
    ),
    DiagnosticRule(
        re.compile(r"ModuleNotFoundError|ImportError", re.I),
        "python_environment", "high",
        "A required Python dependency is unavailable in the active environment.",
        "Switch to the recorded environment or reconcile the dependency manifest.",
    ),
    DiagnosticRule(
        re.compile(r"FileNotFoundError|No such file or directory", re.I),
        "path_contract", "high",
        "A required path is missing.",
        "Resolve the path from the experiment manifest and validate it before rerunning.",
    ),
    DiagnosticRule(
        re.compile(r"KeyboardInterrupt|SIGTERM|terminated before normal completion", re.I),
        "interrupted_run", "medium",
        "The run ended before normal completion.",
        "Verify checkpoint and output completeness before deciding whether to resume.",
    ),
    DiagnosticRule(
        re.compile(r"status\s*[:=]\s*[\"']?COMPLETED|all .* completed|returncode=0", re.I),
        "completed_run", "info",
        "The log contains an explicit completion marker.",
        "Close the task after verifying the expected artifact manifest.",
    ),
    DiagnosticRule(
        re.compile(r"Traceback \(most recent call last\)|RuntimeError:|ValueError:|TypeError:", re.I),
        "runtime_exception", "medium",
        "A runtime exception is present, but no more specific supported signature matched.",
        "Inspect the final exception and compare it with retrieved historical evidence.",
        "MEDIUM",
    ),
)


def diagnose_text(text: str, source: str = "in_memory") -> dict[str, Any]:
    findings = []
    lines = text.splitlines() or [text]
    for line_number, line in enumerate(lines, start=1):
        for rule in RULES:
            match = rule.pattern.search(line)
            if not match:
                continue
            row = asdict(rule)
            row.pop("pattern")
            row["evidence"] = {
                "source": source,
                "line": line_number,
                "text": line.strip()[:2000],
                "matched_signature": match.group(0),
            }
            findings.append(row)
            break
    if not findings:
        findings.append({
            "category": "unclassified",
            "severity": "info",
            "message": "No supported failure signature was detected.",
            "action": "Review the complete log and label the case if it recurs.",
            "confidence": "LOW",
            "evidence": {"source": source, "line": None, "text": text[-800:], "matched_signature": None},
        })
    return {"source": source, "finding_count": len(findings), "findings": findings}

