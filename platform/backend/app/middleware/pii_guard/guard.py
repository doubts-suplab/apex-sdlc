"""PiiGuard — regex PII detection and redaction on agent I/O.

Absorbed from ``governance/pii-guard/guard.py``. The root version was a two-layer scanner (regex +
AWS Comprehend); this platform version keeps **only the regex layer** so the guard is offline,
dependency-free (no ``boto3``), and deterministic — the same properties the rest of the platform
relies on for reproducible tests. A Comprehend adapter can slot in later behind this same interface.

Golden rule (backend CLAUDE.md #9): every string passed to or returned from the LLM must pass
through the guard. ``scrub`` is applied to **outgoing** prompts (PII never reaches the model);
``scan`` surfaces PII in **incoming** completions for the audit trail without mutating an artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from app.middleware.pii_guard.patterns import ALL_PATTERNS, HIGH_CONFIDENCE_LABELS

_log = structlog.get_logger("apex.pii_guard")

REDACTED = "[REDACTED]"

# Non-high-confidence matches shorter than this are dropped (a bare 6-digit sort code fragment is
# more likely a false positive than PII). High-confidence labels bypass the filter.
_MIN_LOW_CONFIDENCE_LEN = 6


@dataclass(frozen=True)
class PiiFinding:
    """A single detected PII span."""

    label: str
    matched_text: str
    start: int
    end: int
    source: str = "regex"
    confidence: float = 1.0


@dataclass
class ScanResult:
    """The outcome of a scan: the original text, its scrubbed form, and every finding."""

    original: str
    scrubbed: str
    findings: list[PiiFinding] = field(default_factory=list)

    @property
    def has_pii(self) -> bool:
        return bool(self.findings)

    @property
    def finding_count(self) -> int:
        return len(self.findings)


class PiiGuard:
    """Regex-only PII scanner. Offline, deterministic, no external calls.

    Args:
        enabled: master switch — when ``False``, ``scrub`` returns text as-is and ``scan`` is empty.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    def scrub(self, text: str) -> str:
        """Return ``text`` with every detected PII span replaced by ``[REDACTED]``."""
        if not self._enabled or not text:
            return text
        return self._scan(text).scrubbed

    def scan(self, text: str) -> list[PiiFinding]:
        """Return the PII findings in ``text`` without modifying it."""
        if not self._enabled or not text:
            return []
        return self._scan(text).findings

    def scan_and_scrub(self, text: str) -> ScanResult:
        """Return the full :class:`ScanResult` — original, scrubbed text, and findings."""
        if not self._enabled or not text:
            return ScanResult(original=text, scrubbed=text)
        return self._scan(text)

    def log_findings(self, findings: list[PiiFinding], *, source: str) -> None:
        """Emit one structured audit line per finding (matched text is never logged)."""
        for f in findings:
            _log.warning(
                "pii_detected",
                source=source,
                label=f.label,
                confidence=f.confidence,
                layer=f.source,
            )

    # -- internal -------------------------------------------------------
    def _scan(self, text: str) -> ScanResult:
        findings: list[PiiFinding] = []
        # Accepted, non-overlapping spans. ALL_PATTERNS is most-specific-first, so a tighter label
        # (e.g. SSN) claims a span before a looser one (e.g. SORT_CODE) can overlap it — keeping the
        # scrub output clean instead of producing garbled, doubly-redacted fragments.
        accepted: list[tuple[int, int]] = []

        for label, pattern in ALL_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                high = label in HIGH_CONFIDENCE_LABELS
                if not high and len(match.group()) < _MIN_LOW_CONFIDENCE_LEN:
                    continue
                if any(start < a_end and a_start < end for a_start, a_end in accepted):
                    continue  # overlaps a span already claimed by a more specific pattern
                accepted.append((start, end))
                findings.append(
                    PiiFinding(
                        label=label,
                        matched_text=match.group(),
                        start=start,
                        end=end,
                        source="regex",
                        confidence=1.0 if high else 0.7,
                    )
                )

        # Scrub right-to-left so earlier spans keep their offsets.
        scrubbed = text
        for f in sorted(findings, key=lambda f: f.start, reverse=True):
            scrubbed = scrubbed[: f.start] + REDACTED + scrubbed[f.end :]

        return ScanResult(original=text, scrubbed=scrubbed, findings=findings)
