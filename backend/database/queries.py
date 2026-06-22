"""
queries.py
==========
Read-only database queries for the dashboard.

REMEMBER the rule from code-standards.md:
Only the Report Agent WRITES to the database.
This file only READS. The dashboard uses these via REST endpoints.
"""

from sqlmodel import Session, select
from database.models import Incident, engine
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

        return [
            {
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
            for inc in incidents
        ]


def get_stats() -> dict:
    """
    Returns aggregate statistics for the summary metric cards.
    Computed across ALL incidents in the database.
    """
    with Session(engine) as session:
        all_incidents = session.exec(select(Incident)).all()

    if not all_incidents:
        # no incidents yet — return zeros so the dashboard shows empty state
        return {
            "total_incidents":         0,
            "incidents_resolved":      0,
            "avg_mttr_seconds":        0.0,
            "baseline_mttr_seconds":   MANUAL_BASELINE_SECONDS,
            "total_revenue_protected": 0.0,
            "diagnosis_accuracy":      0.0,
        }

    # only count RECOVERED incidents for MTTR average
    # (escalated/broken ones didn't recover, so their MTTR isn't a "recovery time")
    recovered = [i for i in all_incidents if i.result == "RECOVERED"]

    avg_mttr = (
        sum(i.mttr_seconds for i in recovered) / len(recovered)
        if recovered else 0.0
    )

    total_revenue = sum(i.revenue_protected for i in all_incidents)

    return {
        "total_incidents":         len(all_incidents),
        "incidents_resolved":      len(recovered),
        "avg_mttr_seconds":        round(avg_mttr, 2),
        "baseline_mttr_seconds":   MANUAL_BASELINE_SECONDS,
        "total_revenue_protected": round(total_revenue, 2),
        # diagnosis accuracy is computed in Phase 6 experiments;
        # placeholder here keeps the API shape stable
        "diagnosis_accuracy":      0.0,
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