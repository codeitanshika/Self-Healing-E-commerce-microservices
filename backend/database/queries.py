"""
queries.py
==========
Read-only database queries for the dashboard.

REMEMBER the rule from code-standards.md:
Only the Report Agent WRITES to the database.
This file only READS. The dashboard uses these via REST endpoints.
"""

from sqlmodel import Session, select
from database.models import Incident, IncidentStage, engine
from shared.config import MANUAL_BASELINE_SECONDS


def get_all_incidents(limit: int = 50) -> list[dict]:
    """
    Returns the most recent incidents, newest first.
    Used by the dashboard's incident history table.
    """
    with Session(engine) as session:
        incidents = session.exec(
            select(Incident).order_by(Incident.timestamp.desc()).limit(limit)
        ).all()

        return [_incident_row(inc) for inc in incidents]


def _incident_row(inc: Incident) -> dict:
    return {
        "id":                inc.id,
        "service":           inc.service,
        "fault_type":        inc.fault_type,
        "root_cause":        inc.root_cause,
        "confidence":        inc.confidence,
        "fix_applied":       inc.fix_applied,
        "retry_count":       inc.retry_count,
        "result":            inc.result,
        "mttr_seconds":      inc.mttr_seconds,
        "revenue_protected": inc.revenue_protected,
        "business_impact":   inc.business_impact,
        "timestamp":         inc.timestamp,
    }


# What a correct diagnosis looks like for each injected/observed fault.
EXPECTED_ROOT_CAUSE = {
    "crash":  "service_crash",
    "slow":   "cpu_overload",
    "memory": "memory_leak",
    "error":  "error_spike",
}


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolated percentile of an already-sorted list."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def get_stats() -> dict:
    """
    Aggregate statistics for the summary cards, computed across ALL
    incidents in the database.
    """
    with Session(engine) as session:
        all_incidents = session.exec(select(Incident)).all()

    empty = {
        "total_incidents":         0,
        "incidents_resolved":      0,
        "incidents_escalated":     0,
        "avg_mttr_seconds":        0.0,
        "p50_mttr_seconds":        0.0,
        "p95_mttr_seconds":        0.0,
        "baseline_mttr_seconds":   MANUAL_BASELINE_SECONDS,
        "speedup_vs_baseline":     0.0,
        "total_revenue_protected": 0.0,
        "diagnosis_accuracy":      0.0,
        "recovery_rate":           0.0,
        "first_try_rate":          0.0,
        "avg_confidence":          0.0,
    }
    if not all_incidents:
        return empty

    # only RECOVERED incidents count toward MTTR (an escalated one never
    # recovered, so its elapsed time is not a "recovery time")
    recovered = [i for i in all_incidents if i.result == "RECOVERED"]
    escalated = [i for i in all_incidents if i.result == "ESCALATED"]
    mttrs = sorted(i.mttr_seconds for i in recovered)
    avg_mttr = sum(mttrs) / len(mttrs) if mttrs else 0.0

    judged = [i for i in all_incidents if i.fault_type in EXPECTED_ROOT_CAUSE]
    correct = [i for i in judged
               if i.root_cause == EXPECTED_ROOT_CAUSE[i.fault_type]]

    return {
        "total_incidents":         len(all_incidents),
        "incidents_resolved":      len(recovered),
        "incidents_escalated":     len(escalated),
        "avg_mttr_seconds":        round(avg_mttr, 2),
        "p50_mttr_seconds":        round(_percentile(mttrs, 50), 2),
        "p95_mttr_seconds":        round(_percentile(mttrs, 95), 2),
        "baseline_mttr_seconds":   MANUAL_BASELINE_SECONDS,
        "speedup_vs_baseline":     round(MANUAL_BASELINE_SECONDS / avg_mttr, 1) if avg_mttr else 0.0,
        "total_revenue_protected": round(sum(i.revenue_protected for i in all_incidents), 2),
        "diagnosis_accuracy":      round(len(correct) / len(judged), 4) if judged else 0.0,
        "recovery_rate":           round(len(recovered) / len(all_incidents), 4),
        "first_try_rate":          round(
            len([i for i in recovered if i.retry_count == 0]) / len(all_incidents), 4),
        "avg_confidence":          round(
            sum(i.confidence for i in all_incidents) / len(all_incidents), 1),
    }


def get_revenue_series() -> list[dict]:
    """Cumulative revenue protected over time (one point per incident)."""
    with Session(engine) as session:
        rows = session.exec(select(Incident).order_by(Incident.timestamp)).all()

    total, points = 0.0, []
    for inc in rows:
        total += inc.revenue_protected
        points.append({
            "timestamp":  inc.timestamp,
            "service":    inc.service,
            "increment":  round(inc.revenue_protected, 2),
            "cumulative": round(total, 2),
        })
    return points


def get_breakdown() -> dict:
    """Counts and mean MTTR grouped by service, fix, and outcome."""
    with Session(engine) as session:
        rows = session.exec(select(Incident)).all()

    def group(key):
        buckets: dict[str, list[Incident]] = {}
        for inc in rows:
            buckets.setdefault(key(inc), []).append(inc)
        out = []
        for name, items in sorted(buckets.items()):
            rec = [i.mttr_seconds for i in items if i.result == "RECOVERED"]
            out.append({
                "name":      name,
                "count":     len(items),
                "avg_mttr":  round(sum(rec) / len(rec), 2) if rec else 0.0,
                "recovered": len(rec),
            })
        return out

    return {
        "by_service": group(lambda i: i.service),
        "by_fix":     group(lambda i: i.fix_applied),
        "by_result":  group(lambda i: i.result),
    }


def get_mttr_by_fault_type() -> list[dict]:
    """
    Returns average MTTR grouped by root cause.
    Used by the dashboard's MTTR comparison bar chart.
    """
    with Session(engine) as session:
        recovered = session.exec(
            select(Incident).where(Incident.result == "RECOVERED")
        ).all()

    # group by root_cause and average the MTTR
    grouped: dict[str, list[float]] = {}
    for inc in recovered:
        grouped.setdefault(inc.root_cause, []).append(inc.mttr_seconds)

    return [
        {
            "root_cause": cause,
            "avg_mttr":   round(sum(times) / len(times), 2),
            "count":      len(times),
        }
        for cause, times in grouped.items()
    ]


def get_incident_detail(incident_id: int) -> dict | None:
    """One incident with its full stage timeline, for the detail drawer."""
    with Session(engine) as session:
        inc = session.get(Incident, incident_id)
        if inc is None:
            return None
        stages = session.exec(
            select(IncidentStage)
            .where(IncidentStage.incident_db_id == incident_id)
            .order_by(IncidentStage.ts)
        ).all()

    row = _incident_row(inc)
    row["explanation"] = inc.explanation
    row["timeline"] = [
        {"stage": s.stage, "ts": s.ts, "detail": s.detail} for s in stages
    ]
    return row
