"""
events.py
=========
All event topic names used across the system, defined as constants.

WHY CONSTANTS INSTEAD OF PLAIN STRINGS?
If you type "ANOMALY_DETECTED" as a string in 5 different files,
one typo ("ANOMOLY_DETECTED") and the event silently never fires.
Using constants means Python catches the typo immediately as a
NameError. Safer, cleaner, easier to refactor.

These topic names match exactly what is in architecture.md.
"""

# ── Published by Monitor Agent ───────────────────────────────────
ANOMALY_DETECTED = "ANOMALY_DETECTED"
# payload: { service, fault_type, metrics, timestamp }

# ── Published by Orchestrator ────────────────────────────────────
DIAGNOSE_REQUEST = "DIAGNOSE_REQUEST"
# payload: { service, metrics, incident_id }

FIX_REQUEST = "FIX_REQUEST"
# payload: { service, fix, incident_id }

VALIDATE_REQUEST = "VALIDATE_REQUEST"
# payload: { service, incident_id, detected_at }

# ── Published by Diagnosis Agent ─────────────────────────────────
DIAGNOSIS_READY = "DIAGNOSIS_READY"
# payload: { service, root_cause, confidence, fix,
#            business_impact, explanation, incident_id }

# ── Published by Fix Agent ───────────────────────────────────────
FIX_APPLIED = "FIX_APPLIED"
# payload: { service, fix_applied, fix_time, incident_id }

# ── Published by Validation Agent ────────────────────────────────
VALIDATION_RESULT = "VALIDATION_RESULT"
# payload: { service, result (RECOVERED/STILL_BROKEN),
#            mttr_seconds, incident_id }

# ── Published by Report Agent ────────────────────────────────────
INCIDENT_LOGGED = "INCIDENT_LOGGED"
# payload: { incident_id, service, result, mttr_seconds }