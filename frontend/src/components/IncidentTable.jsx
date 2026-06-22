/**
 * IncidentTable.jsx
 * =================
 * The incident history table — one row per incident that the
 * system has detected and handled.
 *
 * Data comes from GET /api/incidents, polled every few seconds.
 * Newest incidents appear at the top.
 */

import { Card, Table, Badge } from "react-bootstrap";

// Color the result column based on outcome
const RESULT_BADGE = {
  RECOVERED:    "success",
  STILL_BROKEN: "warning",
  ESCALATED:    "danger",
};

export function IncidentTable({ incidentsData }) {
  // incidentsData is what GET /api/incidents returns:
  // { incidents: [ {id, service, root_cause, fix_applied, result, mttr_seconds, ...}, ... ] }

  if (!incidentsData || !incidentsData.incidents) {
    return <p className="text-muted">Loading incidents...</p>;
  }

  const incidents = incidentsData.incidents;

  // Empty state — no incidents yet (matches ui-rules.md requirement)
  if (incidents.length === 0) {
    return (
      <Card className="shadow-sm mb-4">
        <Card.Body className="text-center text-muted py-5">
          No incidents yet — inject a fault to see the system respond.
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm mb-4">
      <Card.Header className="fw-bold">Incident History</Card.Header>
      <Card.Body className="p-0">
        <Table responsive hover className="mb-0">
          <thead>
            <tr>
              <th>Service</th>
              <th>Fault</th>
              <th>Root Cause</th>
              <th>Fix Applied</th>
              <th>Result</th>
              <th>MTTR</th>
              <th>Revenue Protected</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((inc) => (
              <tr key={inc.id}>
                <td className="text-capitalize fw-semibold">{inc.service}</td>
                <td>{inc.fault_type}</td>
                <td>{inc.root_cause}</td>
                <td>
                  {inc.fix_applied}
                  {inc.retry_count > 0 && (
                    <Badge bg="secondary" className="ms-1">
                      {inc.retry_count} retries
                    </Badge>
                  )}
                </td>
                <td>
                  <Badge bg={RESULT_BADGE[inc.result] || "secondary"}>
                    {inc.result}
                  </Badge>
                </td>
                <td>{inc.mttr_seconds}s</td>
                <td>₹{inc.revenue_protected.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card.Body>
    </Card>
  );
}