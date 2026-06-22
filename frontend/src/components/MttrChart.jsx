/**
 * MttrChart.jsx
 * =============
 * Bar chart comparing your system's MTTR per fault type against
 * the 900-second manual baseline (drawn as a dashed reference line).
 *
 * The visual gap between the short bars and the high baseline line
 * IS the core result of this project.
 *
 * Data comes from GET /api/mttr-chart, polled every few seconds.
 */

import { Card } from "react-bootstrap";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend,
} from "recharts";

export function MttrChart({ chartData }) {
  // chartData is what GET /api/mttr-chart returns:
  // { data: [ {root_cause, avg_mttr, count}, ... ] }

  if (!chartData || !chartData.data) {
    return <p className="text-muted">Loading chart...</p>;
  }

  const data = chartData.data;

  if (data.length === 0) {
    return (
      <Card className="shadow-sm mb-4">
        <Card.Header className="fw-bold">Recovery Time by Fault Type</Card.Header>
        <Card.Body className="text-center text-muted py-5">
          No data yet — resolve some incidents to see the chart.
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm mb-4">
      <Card.Header className="fw-bold">
        Recovery Time by Fault Type (vs Manual Baseline)
      </Card.Header>
      <Card.Body>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="root_cause" />
            <YAxis label={{ value: "Seconds", angle: -90, position: "insideLeft" }} />
            <Tooltip />
            <Legend />

            {/* Your system's actual recovery times */}
            <Bar dataKey="avg_mttr" fill="#534AB7" name="Your System (MTTR)" />

            {/* The 900s manual baseline as a dashed reference line */}
            <ReferenceLine
              y={900}
              stroke="#E24B4A"
              strokeDasharray="6 6"
              label={{ value: "Manual Baseline (900s)", position: "top", fill: "#E24B4A" }}
            />
          </BarChart>
        </ResponsiveContainer>
      </Card.Body>
    </Card>
  );
}