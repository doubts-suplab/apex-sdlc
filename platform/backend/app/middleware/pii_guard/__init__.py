"""PII guard — detect and redact PII on agent I/O (absorbed from governance/pii-guard/).

Regex-based, offline, no AWS dependency. A production build may add an AWS Comprehend NLP layer for
names/addresses; this core covers high-confidence structured patterns (email, SSN, cards, secrets…).
"""

from __future__ import annotations

from app.middleware.pii_guard.guard import PiiFinding, PiiGuard, ScanResult

__all__ = ["PiiGuard", "PiiFinding", "ScanResult"]
