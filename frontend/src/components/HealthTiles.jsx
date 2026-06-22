/**
 * HealthTiles.jsx
 * ===============
 * Shows the 5 service health tiles at the top of the dashboard.
 * Each tile is colored by status: green (ok), yellow (degraded), red (down).
 *
 * Data comes from GET /api/services, polled every few seconds.
 */

import { Row, Col, Card, Badge } from "react-bootstrap";

// Maps service status to a Bootstrap color + label
// (colors chosen to match ui-tokens.md: healthy/degraded/down)
const STATUS_STYLE = {
  ok:       { bg: "#1D9E75", label: "HEALTHY",  badge: "success" },
  degraded: { bg: "#BA7517", label: "DEGRADED", badge: "warning" },
  down:     { bg: "#E24B4A", label: "DOWN",     badge: "danger"  },
};

export function HealthTiles({ servicesData }) {
  // servicesData is what GET /api/services returns:
  // { services: { auth: {...}, cart: {...}, ... }, summary: {...} }

  if (!servicesData || !servicesData.services) {
    return <p className="text-muted">Loading services...</p>;
  }

  const services = servicesData.services;

  return (
    <Row className="g-3 mb-4">
      {Object.entries(services).map(([name, health]) => {
        const style = STATUS_STYLE[health.status] || STATUS_STYLE.down;

        return (
          <Col key={name} xs={6} md={4} lg>
            <Card
              style={{ backgroundColor: style.bg, color: "white", border: "none" }}
              className="h-100 shadow-sm"
            >
              <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <Card.Title className="mb-0 text-capitalize">{name}</Card.Title>
                  <Badge bg={style.badge}>{style.label}</Badge>
                </div>
                <div style={{ fontSize: "0.85rem", opacity: 0.9 }}>
                  <div>CPU: {health.cpu}% | Mem: {health.memory}%</div>
                  <div>Response: {health.response_time_ms}ms</div>
                  <div>Errors: {(health.error_rate * 100).toFixed(0)}%</div>
                </div>
              </Card.Body>
            </Card>
          </Col>
        );
      })}
    </Row>
  );
}