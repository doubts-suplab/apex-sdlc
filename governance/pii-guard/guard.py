"""
APEX PII Guard
Two-layer PII scanner:
  Layer 1 — Fast local regex scan (patterns.py)
  Layer 2 — AWS Comprehend DetectPiiEntities (NLP-based, catches names/orgs/addresses)

Usage:
    from pii_guard import PIIGuard

    guard = PIIGuard(enabled=True)

    # Scrub and get clean text
    clean = guard.scrub(user_text)

    # Get detailed findings (for audit log)
    findings = guard.scan(user_text)
    if findings:
        guard.log_findings(findings, source="jira-bridge:issue_created:PROJ-123")
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import boto3

from patterns import ALL_PATTERNS, HIGH_CONFIDENCE_LABELS

logger = logging.getLogger(__name__)

REDACTED = "[REDACTED]"

# AWS Comprehend entity types to treat as PII
COMPREHEND_PII_TYPES = {
    "NAME",
    "ADDRESS",
    "PHONE",
    "EMAIL",
    "SSN",
    "CREDIT_DEBIT_NUMBER",
    "BANK_ACCOUNT_NUMBER",
    "BANK_ROUTING",
    "PASSPORT_NUMBER",
    "DRIVER_ID",
    "DATE_TIME",
    "URL",
    "IP_ADDRESS",
    "MAC_ADDRESS",
    "AWS_ACCESS_KEY",
    "AWS_SECRET_KEY",
    "USERNAME",
    "PASSWORD",
    "UK_NATIONAL_INSURANCE_NUMBER",
    "INTERNATIONAL_BANK_ACCOUNT_NUMBER",
    "SWIFT_CODE",
}


@dataclass
class PIIFinding:
    label: str
    matched_text: str
    start: int
    end: int
    source: str  # "regex" or "comprehend"
    confidence: float = 1.0


@dataclass
class ScanResult:
    original: str
    scrubbed: str
    findings: list[PIIFinding] = field(default_factory=list)

    @property
    def has_pii(self) -> bool:
        return bool(self.findings)

    @property
    def finding_count(self) -> int:
        return len(self.findings)


class PIIGuard:
    """
    Two-layer PII scanner with optional AWS Comprehend NLP backend.

    Args:
        enabled:          Master switch — if False, scrub() returns text unchanged
        use_comprehend:   Enable AWS Comprehend layer (requires IAM permission)
        min_confidence:   Minimum Comprehend confidence score to act on (0.0–1.0)
        comprehend_region: AWS region for Comprehend calls
    """

    def __init__(
        self,
        enabled: bool = True,
        use_comprehend: bool = True,
        min_confidence: float = 0.90,
        comprehend_region: str = "eu-west-1",
    ) -> None:
        self._enabled = enabled
        self._use_comprehend = use_comprehend
        self._min_confidence = min_confidence
        self._comprehend: Optional[object] = None

        if enabled and use_comprehend:
            try:
                self._comprehend = boto3.client("comprehend", region_name=comprehend_region)
            except Exception as exc:
                logger.warning("Could not initialise Comprehend client: %s — falling back to regex only", exc)
                self._use_comprehend = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrub(self, text: str) -> str:
        """Return text with all detected PII replaced by [REDACTED]."""
        if not self._enabled or not text:
            return text
        result = self._scan_internal(text)
        return result.scrubbed

    def scan(self, text: str) -> list[PIIFinding]:
        """Return a list of PII findings without modifying text."""
        if not self._enabled or not text:
            return []
        return self._scan_internal(text).findings

    def scan_and_scrub(self, text: str) -> ScanResult:
        """Return full ScanResult with original, scrubbed text, and all findings."""
        if not self._enabled or not text:
            return ScanResult(original=text, scrubbed=text)
        return self._scan_internal(text)

    def log_findings(self, findings: list[PIIFinding], source: str) -> None:
        """Emit structured log lines for the APEX audit trail."""
        for f in findings:
            logger.warning(
                "PII_DETECTED source=%s label=%s confidence=%.2f layer=%s",
                source,
                f.label,
                f.confidence,
                f.source,
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _scan_internal(self, text: str) -> ScanResult:
        findings: list[PIIFinding] = []

        # Layer 1: regex
        regex_findings = self._regex_scan(text)
        findings.extend(regex_findings)

        # Layer 2: Comprehend (only if client available)
        if self._use_comprehend and self._comprehend:
            comprehend_findings = self._comprehend_scan(text)
            # Merge — avoid duplicate spans
            for cf in comprehend_findings:
                if not any(self._overlaps(cf, rf) for rf in findings):
                    findings.append(cf)

        # Scrub in reverse order to preserve offsets
        scrubbed = text
        for finding in sorted(findings, key=lambda f: f.start, reverse=True):
            scrubbed = scrubbed[: finding.start] + REDACTED + scrubbed[finding.end :]

        return ScanResult(original=text, scrubbed=scrubbed, findings=findings)

    def _regex_scan(self, text: str) -> list[PIIFinding]:
        findings: list[PIIFinding] = []
        seen_spans: set[tuple[int, int]] = set()

        for label, pattern in ALL_PATTERNS:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                # Skip short matches for low-confidence patterns
                if label not in HIGH_CONFIDENCE_LABELS and len(match.group()) < 6:
                    continue
                seen_spans.add(span)
                findings.append(
                    PIIFinding(
                        label=label,
                        matched_text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        source="regex",
                        confidence=1.0 if label in HIGH_CONFIDENCE_LABELS else 0.7,
                    )
                )

        return findings

    def _comprehend_scan(self, text: str) -> list[PIIFinding]:
        findings: list[PIIFinding] = []

        # Comprehend has a 5000-byte limit per call; chunk if needed
        chunks = self._chunk_text(text, max_bytes=4900)
        offset = 0

        for chunk in chunks:
            try:
                response = self._comprehend.detect_pii_entities(  # type: ignore[union-attr]
                    Text=chunk,
                    LanguageCode="en",
                )
                for entity in response.get("Entities", []):
                    if entity["Type"] not in COMPREHEND_PII_TYPES:
                        continue
                    if entity["Score"] < self._min_confidence:
                        continue
                    findings.append(
                        PIIFinding(
                            label=entity["Type"],
                            matched_text=chunk[entity["BeginOffset"] : entity["EndOffset"]],
                            start=offset + entity["BeginOffset"],
                            end=offset + entity["EndOffset"],
                            source="comprehend",
                            confidence=entity["Score"],
                        )
                    )
            except Exception as exc:
                logger.error("Comprehend scan failed: %s", exc, exc_info=True)

            offset += len(chunk.encode("utf-8"))

        return findings

    @staticmethod
    def _chunk_text(text: str, max_bytes: int) -> list[str]:
        """Split text into chunks that fit within max_bytes (UTF-8)."""
        chunks: list[str] = []
        current = ""
        for word in text.split(" "):
            candidate = current + (" " if current else "") + word
            if len(candidate.encode("utf-8")) > max_bytes:
                if current:
                    chunks.append(current)
                current = word
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks or [text]

    @staticmethod
    def _overlaps(a: PIIFinding, b: PIIFinding) -> bool:
        return not (a.end <= b.start or b.end <= a.start)
