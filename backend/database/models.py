"""
models.py
=========
Defines the Incident table using SQLModel.

Each row = one fault that was detected, diagnosed, fixed, and validated.
This table is the source of truth for:
- The dashboard's incident history table
- All research paper metrics (MTTR, accuracy, revenue protected)
"""

from sqlmodel import SQLModel, Field, create_engine
from typing import Optional
import os

# Database file lives inside backend/database/
DB_PATH = os.path.join(os.path.dirname(__file__), "incidents.db")
engine = create_engine(f"sqlite:///{DB_PATH}")


class Incident(SQLModel, table=True):
    """
    One row = one complete incident lifecycle:
    detected → diagnosed → fixed → validated → logged.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    service: str                    # which service broke (e.g. "payment")
    fault_type: str                 # what Monitor detected (e.g. "crash")

    root_cause: str                 # what Diagnosis Agent decided (e.g. "service_crash")
    confidence: int                 # LLM's confidence 0-100
    business_impact: str            # LLM's explanation of impact
    explanation: str                # LLM's reasoning

    fix_applied: str                # what Fix Agent did (e.g. "restart")
    retry_count: int = 0            # how many retries it took (0 = first try worked)

    result: str                     # "RECOVERED" | "STILL_BROKEN" | "ESCALATED"
    mttr_seconds: float             # time from detection to recovery
    revenue_protected: float        # calculated business value

    timestamp: float                # unix time when incident was logged


def init_db():
    """
    Creates the incidents.db file and the Incident table
    if they don't already exist. Safe to call every startup —
    it won't wipe existing data.
    """
    SQLModel.metadata.create_all(engine)
    print(f"✅ Database ready at {DB_PATH}")