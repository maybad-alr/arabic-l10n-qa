"""Report building and formatting."""

from __future__ import annotations

import json
from collections import Counter
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from .checks import CheckOptions, Issue, Severity, check_entry, check_pair


def build_report(
    source: Optional[Mapping[str, object]],
    target: Mapping[str, object],
    options: Optional[CheckOptions] = None,
) -> List[Issue]:
    """Run all checks over a target file, optionally compared to a source file."""

    options = options or CheckOptions()
    issues: List[Issue] = []

    if source is not None:
        for key in sorted(source.keys() - target.keys()):
            issues.append(
                Issue(
                    key=key,
                    code="missing.key",
                    severity=Severity.ERROR,
                    message="key exists in source but not in target",
                )
            )
        for key in sorted(target.keys() - source.keys()):
            issues.append(
                Issue(
                    key=key,
                    code="extra.key",
                    severity=Severity.WARNING,
                    message="key exists in target but not in source",
                )
            )

    for key in sorted(target.keys()):
        value = target[key]
        src_value = source.get(key) if source is not None else None
        if src_value is not None and not isinstance(src_value, str):
            src_value = json.dumps(src_value, ensure_ascii=False)
        if isinstance(value, str):
            issues.extend(check_pair(key, src_value, value, options))
        else:
            issues.extend(check_entry(key, value, options))

    issues.sort(key=lambda item: (-int(item.severity), item.key, item.code))
    return issues


def counts_by_severity(issues: Sequence[Issue]) -> Dict[str, int]:
    counter = Counter(issue.severity.label for issue in issues)
    return {severity.label: counter.get(severity.label, 0) for severity in Severity}


def format_report(
    issues: Sequence[Issue],
    fmt: str = "text",
    target_name: str = "target",
) -> str:
    """Render issues as ``text``, ``json`` or ``github`` annotations."""

    if fmt == "json":
        return json.dumps(
            {
                "summary": counts_by_severity(issues),
                "total": len(issues),
                "issues": [issue.as_dict() for issue in issues],
            },
            ensure_ascii=False,
            indent=2,
        )

    if fmt == "github":
        lines = []
        for issue in issues:
            level = "error" if issue.severity is Severity.ERROR else "warning" if issue.severity is Severity.WARNING else "notice"
            lines.append(
                f"::{level} title={issue.code},file={target_name}::{issue.key}: {issue.message}"
            )
        return "\n".join(lines)

    if fmt != "text":
        raise ValueError(f"unknown format: {fmt!r}")

    summary = counts_by_severity(issues)
    lines: List[str] = []
    for severity in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        group = [issue for issue in issues if issue.severity is severity]
        if not group:
            continue
        if lines:
            lines.append("")
        lines.append(f"{severity.label.upper()} ({len(group)})")
        for issue in group:
            lines.append(f"  {issue.key}: [{issue.code}] {issue.message}")

    if not issues:
        lines.append("No issues found.")
    lines.append("")
    lines.append(
        "Summary: {error} error(s), {warning} warning(s), {info} info".format(
            error=summary["error"], warning=summary["warning"], info=summary["info"]
        )
    )
    return "\n".join(lines)
