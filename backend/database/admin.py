"""
admin.py
========
Destructive maintenance operations, deliberately kept out of queries.py
(which is read-only) and out of the agents (only the Report Agent writes
incident rows). Used by the dashboard's "Reset demo data" control.
"""
from sqlmodel import Session, delete, select, func

from database.models import Incident, IncidentStage, engine


def reset_all() -> dict:
    """Delete every incident and its stage timeline. Returns what was removed."""
    with Session(engine) as session:
        incidents = session.exec(select(func.count()).select_from(Incident)).one()
        stages = session.exec(select(func.count()).select_from(IncidentStage)).one()
        session.exec(delete(IncidentStage))
        session.exec(delete(Incident))
        session.commit()
    return {"incidents_deleted": incidents, "stages_deleted": stages}
