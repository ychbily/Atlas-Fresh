import type { KPIs } from '../types';
import { Pill, fmtEur, fmtPct, fmtT } from './primitives';

interface KpiItem {
  label: string;
  value: string;
  delta?: string;
  deltaTone?: 'positive' | 'negative' | 'warning';
  note?: string;
  tone?: 'positive' | 'warning';
  tags?: string[];
}

/**
 * 7 Executive KPI summary cards visualizing supply variance, station capacity,
 * export rate, total revenue, local losses, and at-risk clients.
 */
export function KpiGrid({ kpis, atRiskTags = [] }: { kpis: KPIs; atRiskTags?: string[] }) {
  const deliveryDelta = kpis.actual_received_t - kpis.expected_plan_t;
  const stationUsagePct = (kpis.export_volume_t / kpis.station_capacity_t) * 100;

  const items: KpiItem[] = [
    {
      label: 'Planned / Actual',
      value: fmtT(kpis.actual_received_t),
      delta: `${deliveryDelta > 0 ? '+' : ''}${fmtT(deliveryDelta)}`,
      deltaTone: deliveryDelta < 0 ? 'negative' : 'positive',
      note: `Target: ${fmtT(kpis.expected_plan_t)}`,
    },
    {
      label: 'Station Usage',
      value: fmtPct(stationUsagePct),
      note: `${fmtT(kpis.export_volume_t)} / ${fmtT(kpis.station_capacity_t)} Capacity`,
    },
    {
      label: 'Export Rate',
      value: fmtPct(kpis.export_rate_pct),
      tone: 'positive',
      note: 'Overall Harvest Ratio',
    },
    {
      label: 'Export Revenue',
      value: fmtEur(kpis.export_revenue_eur),
      note: 'Fulfillable Client Orders',
    },
    {
      label: 'Local Loss',
      value: fmtT(kpis.local_volume_t),
      delta: `(${fmtEur(kpis.local_value_eur)})`,
      deltaTone: 'warning',
      note: '10% Reference Value',
    },
    {
      label: 'Total Value',
      value: fmtEur(kpis.total_value_eur),
      note: 'Export + Local Combined',
    },
    {
      label: 'At-Risk Clients',
      value: String(kpis.at_risk_clients),
      tone: kpis.at_risk_clients > 0 ? 'warning' : 'positive',
      tags: atRiskTags.length > 0 ? atRiskTags : undefined,
    },
  ];

  return (
    <div className="kpi-grid">
      {items.map((item) => (
        <div key={item.label} className="kpi-card">
          <span className="label-caps">{item.label}</span>
          <div className="kpi-value-row">
            <span
              className={`kpi-value ${
                item.tone === 'positive'
                  ? 'text-positive'
                  : item.tone === 'warning'
                    ? 'text-warning'
                    : ''
              }`}
            >
              {item.value}
            </span>
            {item.delta && (
              <span
                className={`kpi-delta ${
                  item.deltaTone === 'negative'
                    ? 'text-negative'
                    : item.deltaTone === 'warning'
                      ? 'text-warning'
                      : 'text-positive'
                }`}
              >
                {item.delta}
              </span>
            )}
            {item.tags && (
              <div style={{ display: 'flex', gap: '4px' }}>
                {item.tags.map((tag) => (
                  <Pill key={tag} tone="warning">
                    {tag}
                  </Pill>
                ))}
              </div>
            )}
          </div>
          {item.note && <span className="kpi-note">{item.note}</span>}
        </div>
      ))}
    </div>
  );
}
