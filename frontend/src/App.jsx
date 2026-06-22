/**
 * App.jsx
 * =======
 * The main dashboard — assembles all components and feeds them
 * live data from the backend via the usePolling hook.
 *
 * Layout (top to bottom, per ui-rules.md):
 *   1. Title
 *   2. Service health tiles
 *   3. Summary metric cards
 *   4. Fault injection controls (demo buttons)
 *   5. Incident history table
 *   6. MTTR comparison chart
 */

import { Container, Row, Col, Card, Button, Form } from "react-bootstrap";
import { useState } from "react";

import { usePolling } from "./usePolling";
import { HealthTiles } from "./components/HealthTiles";
import { StatsCards } from "./components/StatsCards";
import { IncidentTable } from "./components/IncidentTable";
import { MttrChart } from "./components/MttrChart";

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  // Poll all four data sources at different intervals
  const { data: servicesData } = usePolling("/api/services", 3000);
  const { data: statsData } = usePolling("/api/stats", 4000);
  const { data: incidentsData } = usePolling("/api/incidents", 4000);
  const { data: chartData } = usePolling("/api/mttr-chart", 5000);

  // State for the fault injection controls
  const [selectedService, setSelectedService] = useState("payment");
  const [selectedFault, setSelectedFault] = useState("crash");

  // Inject a fault by calling the backend
  const injectFault = async () => {
    try {
      await fetch(
        `${API_URL}/api/services/${selectedService}/fault/${selectedFault}`,
        { method: "POST" }
      );
      console.log(`Injected ${selectedFault} into ${selectedService}`);
    } catch (err) {
      console.error("Failed to inject fault:", err);
    }
  };

  return (
    <div style={{ backgroundColor: "#0E0E10", minHeight: "100vh", paddingBottom: "2rem" }}>
      <Container className="py-4">

        {/* 1. Title */}
        <div className="mb-4">
          <h1 style={{ color: "#F5F5F5", fontWeight: "bold" }}>
            Self-Healing E-Commerce Monitor
          </h1>
          <p style={{ color: "#A0A0A5" }}>
            Autonomous fault detection, diagnosis, and recovery using multi-agent AI
          </p>
        </div>

        {/* 2. Service health tiles */}
        <HealthTiles servicesData={servicesData} />

        {/* 3. Summary metric cards */}
        <StatsCards statsData={statsData} />

      </Container>
    </div>
  );
}

export default App;