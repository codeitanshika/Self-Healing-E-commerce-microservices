import { MttrByCause, MttrTrend, RevenueArea, ServiceBreakdown } from "./Charts";

/** The chart grid. Loaded lazily so the charting library does not delay first paint. */
export default function Performance({ mttr, baseline, revenue, incidents, breakdown }) {
  return (
    <div className="grid cols-2">
      <MttrByCause data={mttr} baseline={baseline} />
      <RevenueArea data={revenue} />
      <MttrTrend incidents={incidents} />
      <ServiceBreakdown data={breakdown} />
    </div>
  );
}
