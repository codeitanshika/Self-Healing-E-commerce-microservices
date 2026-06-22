/**
 * StatsCards.jsx
 * ==============
 * The row of 4 summary metric cards below the health tiles.
 * Shows: avg MTTR, manual baseline, revenue protected, incidents resolved.
 *
 * Data comes from GET /api/stats, polled every few seconds.
 */

import { Row, Col, Card } from "react-bootstrap";

export function StatsCards({ statsData }) {
  // statsData is what GET /api/stats returns:
  // { avg_mttr_seconds, baseline_mttr_seconds, total_revenue_protected, ... }

  if (!statsData) {
    return <p className="text-muted">Loading stats...</p>;
  }

  // Define the 4 cards we want to show
  const cards = [
    {
      label: "Avg Recovery Time",
      value: `${statsData.avg_mttr_seconds}s`,
      sub: "your system (MTTR)",
      color: "#534AB7",
    },
    {
      label: "Manual Baseline",
      value: `${statsData.baseline_mttr_seconds}s`,
      sub: "human response time",
      color: "#6c757d",
    },
    {
      label: "Revenue Protected",
      value: `₹${statsData.total_revenue_protected.toLocaleString()}`,
      sub: "vs manual baseline",
      color: "#1D9E75",
    },
    {
      label: "Incidents Resolved",
      value: `${statsData.incidents_resolved} / ${statsData.total_incidents}`,
      sub: "auto-healed",
      color: "#0d6efd",
    },
  ];

  return (
    <Row className="g-3 mb-4">
      {cards.map((card, i) => (
        <Col key={i} xs={6} lg={3}>
          <Card className="h-100 shadow-sm" style={{ borderTop: `4px solid ${card.color}` }}>
            <Card.Body>
              <div className="text-muted" style={{ fontSize: "0.8rem", textTransform: "uppercase" }}>
                {card.label}
              </div>
              <div style={{ fontSize: "1.8rem", fontWeight: "bold", color: card.color }}>
                {card.value}
              </div>
              <div className="text-muted" style={{ fontSize: "0.75rem" }}>
                {card.sub}
              </div>
            </Card.Body>
          </Card>
        </Col>
      ))}
    </Row>
  );
}