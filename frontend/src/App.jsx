import { Container, Row, Col, Card, Button } from "react-bootstrap";
import { useState } from "react";
import { usePolling } from "./usePolling";
import { HealthTiles } from "./components/HealthTiles";
import { StatsCards } from "./components/StatsCards";
import { IncidentTable } from "./components/IncidentTable";
import { MttrChart } from "./components/MttrChart";

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const { data: servicesData } = usePolling("/api/services", 3000);
  const { data: statsData } = usePolling("/api/stats", 4000);
  const { data: incidentsData } = usePolling("/api/incidents", 4000);
  const { data: chartData } = usePolling("/api/mttr-chart", 5000);

  const [selectedService, setSelectedService] = useState("payment");
  const [selectedFault, setSelectedFault] = useState("crash");

  const injectFault = async () => {
    try {
      await fetch(
        `${API_URL}/api/services/${selectedService}/fault/${selectedFault}`,
        { method: "POST" }
      );
    } catch (err) {
      console.error("Failed to inject fault:", err);
    }
  };

  return (
    <div style={{ backgroundColor: "#0E0E10", minHeight: "100vh", paddingBottom: "2rem" }}>
      <Container className="py-4">

        <div className="mb-4">
          <h1 style={{ color: "#F5F5F5", fontWeight: "bold" }}>
            Self-Healing E-Commerce Monitor
          </h1>
          <p style={{ color: "#A0A0A5" }}>
            Autonomous fault detection, diagnosis, and recovery using multi-agent AI
          </p>
        </div>

        <HealthTiles servicesData={servicesData} />

        <StatsCards statsData={statsData} />

        <Card className="shadow-sm mb-4" style={{ backgroundColor: "#1A1A1D", border: "none" }}>
          <Card.Body>
            <p style={{ color: "#F5F5F5", fontWeight: "bold", marginBottom: "1rem" }}>
              Demo Controls
            </p>
            <div className="d-flex gap-3 align-items-end flex-wrap">
              <div>
                <label style={{ color: "#A0A0A5", fontSize: "0.85rem", display: "block", marginBottom: "4px" }}>
                  Service
                </label>
                <select
                  value={selectedService}
                  onChange={(e) => setSelectedService(e.target.value)}
                  className="form-select"
                  style={{ minWidth: "150px" }}
                >
                  <option value="auth">auth</option>
                  <option value="cart">cart</option>
                  <option value="payment">payment</option>
                  <option value="inventory">inventory</option>
                  <option value="notification">notification</option>
                </select>
              </div>
              <div>
                <label style={{ color: "#A0A0A5", fontSize: "0.85rem", display: "block", marginBottom: "4px" }}>
                  Fault Type
                </label>
                <select
                  value={selectedFault}
                  onChange={(e) => setSelectedFault(e.target.value)}
                  className="form-select"
                  style={{ minWidth: "150px" }}
                >
                  <option value="crash">crash</option>
                  <option value="slow">slow</option>
                  <option value="memory">memory</option>
                  <option value="error">error</option>
                </select>
              </div>
              <button
                className="btn btn-danger"
                onClick={injectFault}
              >
                Inject Fault
              </button>
            </div>
          </Card.Body>
        </Card>

        <IncidentTable incidentsData={incidentsData} />

        <MttrChart chartData={chartData} />

      </Container>
    </div>
  );
}

export default App;