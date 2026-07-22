"""apex → agent-harness port adapters (agent-harness spec §7).

These wire apex infrastructure to the harness ports. They implement the harness Protocols and depend
on the harness core, never the reverse (agent-harness ADR-0005). Audit/observability/human-review are
emitted through structlog here; a production build swaps in Postgres/queue adapters without touching
the harness or the agents.
"""

from __future__ import annotations

from typing import Any

import structlog
from agent_harness.adapters import redact
from agent_harness.ports.governance import (
    AuditEntry,
    InvocationMetric,
    ReviewItem,
    SecurityEvent,
)

_log = structlog.get_logger("apex.agents")


class StructlogAudit:
    """Append-only audit sink (spec §7.3). Emits redacted structured events; never updates/deletes."""

    def __init__(self, logger: Any | None = None) -> None:
        self._log = logger or _log

    def record(self, entry: AuditEntry) -> None:
        self._log.info(
            "agent.decision.audit",
            agent=entry.agent_name,
            tenant=entry.tenant_id,
            action=entry.action,
            confidence=entry.confidence,
            auto_enforced=entry.auto_enforced,
            outcome=entry.outcome,
            rationale=redact(entry.rationale),
            correlation_id=entry.correlation_id,
        )

    def record_security_event(self, event: SecurityEvent) -> None:
        self._log.warning(
            "agent.security_event",
            agent=event.agent_name,
            tenant=event.tenant_id,
            kind=event.kind,
            detail=redact(event.detail),
            correlation_id=event.correlation_id,
        )


class StructlogHumanReview:
    """Routes non-enforcing decisions to a human (spec §7.4). Logs; a real build enqueues to a queue."""

    def __init__(self, logger: Any | None = None) -> None:
        self._log = logger or _log

    def enqueue(self, item: ReviewItem) -> None:
        self._log.warning(
            "agent.human_review.enqueued",
            agent=item.agent_name,
            tenant=item.request.tenant_id,
            action=item.decision.action.value,
            confidence=item.decision.confidence,
            reason=item.reason,
            sla_seconds=item.sla_seconds,
            correlation_id=item.request.correlation_id,
        )


class StructlogObservability:
    """Per-invocation metrics + counters (spec §7.5, §4.2). Tracks counters in-process and logs them."""

    def __init__(self, logger: Any | None = None) -> None:
        self._log = logger or _log
        self._counters: dict[str, int] = {}

    def emit(self, metric: InvocationMetric) -> None:
        self._log.info(
            "agent.metric",
            agent=metric.agent_name,
            action=metric.action,
            confidence=metric.confidence,
            duration_ms=round(metric.duration_ms, 3),
            outcome=metric.outcome,
            correlation_id=metric.correlation_id,
        )

    def increment_counter(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value
        # A non-zero confidence_gate_bypass_total is a critical governance incident (spec §4.2).
        self._log.error("agent.counter", name=name, value=self._counters[name])

    def counter(self, name: str) -> int:
        return self._counters.get(name, 0)


class FlagKillSwitch:
    """System-wide stop without a deploy (spec §7.6). Backed by a simple flag; wire to Redis/settings in prod."""

    def __init__(self, engaged: bool = False) -> None:
        self._engaged = engaged

    def is_engaged(self) -> bool:
        return self._engaged

    def engage(self) -> None:
        self._engaged = True

    def disengage(self) -> None:
        self._engaged = False
