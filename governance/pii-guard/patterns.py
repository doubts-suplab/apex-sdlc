"""
APEX PII Guard — Regex Pattern Library

Patterns used for local pre-scan before calling AWS Comprehend.
Local scan is fast and catches obvious cases; Comprehend handles
nuanced NLP-based detection (names, organisations, addresses).
"""

import re

# ---------------------------------------------------------------------------
# Pattern definitions
# Each entry: (label, compiled_regex)
# ---------------------------------------------------------------------------

EMAIL = (
    "EMAIL",
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
)

# UK, US, and international phone formats
PHONE = (
    "PHONE",
    re.compile(
        r"(?:\+?\d{1,3}[\s\-.]?)?"
        r"(?:\(?\d{2,4}\)?[\s\-.]?)?"
        r"\d{3,4}[\s\-.]?\d{3,4}"
        r"(?:[\s\-.]?\d{1,4})?"
    ),
)

# UK National Insurance Number
NINO = (
    "NINO",
    re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b", re.IGNORECASE),
)

# US SSN
SSN = (
    "SSN",
    re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
)

# UK Sort Code
SORT_CODE = (
    "SORT_CODE",
    re.compile(r"\b\d{2}[-\s]?\d{2}[-\s]?\d{2}\b"),
)

# Bank account number (UK 8-digit)
BANK_ACCOUNT = (
    "BANK_ACCOUNT",
    re.compile(r"\b\d{8}\b"),
)

# Credit card (Luhn not validated — pattern only)
CREDIT_CARD = (
    "CREDIT_CARD",
    re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"),
)

# UK postcode
UK_POSTCODE = (
    "UK_POSTCODE",
    re.compile(
        r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b",
        re.IGNORECASE,
    ),
)

# US ZIP code
US_ZIP = (
    "US_ZIP",
    re.compile(r"\b\d{5}(?:-\d{4})?\b"),
)

# IPv4 address (internal/external)
IP_ADDRESS = (
    "IP_ADDRESS",
    re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ),
)

# AWS account IDs (12 digits — frequently pasted in error)
AWS_ACCOUNT_ID = (
    "AWS_ACCOUNT_ID",
    re.compile(r"\b\d{12}\b"),
)

# AWS ARNs
AWS_ARN = (
    "AWS_ARN",
    re.compile(r"arn:aws[a-z\-]*:[a-z0-9\-]*:[a-z0-9\-]*:\d{12}:[^\s]+"),
)

# Generic API keys / secrets heuristic (high entropy strings 32+ chars with no spaces)
SECRET_HEURISTIC = (
    "SECRET",
    re.compile(r"\b[A-Za-z0-9+/=_\-]{32,}\b"),
)

# Date of birth patterns
DATE_OF_BIRTH = (
    "DOB",
    re.compile(
        r"\b(?:0?[1-9]|[12]\d|3[01])"
        r"[\s/\-.]"
        r"(?:0?[1-9]|1[0-2])"
        r"[\s/\-.]"
        r"(?:19|20)\d{2}\b"
    ),
)

# All patterns for local scan — ordered by specificity (most specific first)
ALL_PATTERNS: list[tuple[str, re.Pattern]] = [
    EMAIL,
    NINO,
    SSN,
    AWS_ARN,
    AWS_ACCOUNT_ID,
    CREDIT_CARD,
    BANK_ACCOUNT,
    SORT_CODE,
    UK_POSTCODE,
    US_ZIP,
    IP_ADDRESS,
    DATE_OF_BIRTH,
    PHONE,
    SECRET_HEURISTIC,
]

# Patterns that are HIGH confidence (always redact without Comprehend confirmation)
HIGH_CONFIDENCE_LABELS = {"EMAIL", "NINO", "SSN", "CREDIT_CARD", "AWS_ARN", "SECRET"}
