import type { Farm, FarmSummary } from '../types';
import { Row, TableShell, Tbody, Td, Th, Thead, TotalRow } from './DataTable';
import { VariancePill, fmtT } from './primitives';

interface ProductionTableProps {
  summaries: FarmSummary[];
  farms?: Farm[];
}

/**
 * Production view showing all 20 farms, expected capacities, planned mixes,
 * actual segment deliveries, per-segment variances, and local market residuals.
 */
export function ProductionTable({ summaries, farms }: ProductionTableProps) {
  // Map farm_id to planned mix percentages if raw dataset is provided
  const farmMixMap = new Map<string, string>();
  if (farms) {
    for (const f of farms) {
      const mixStr = `${Math.round(f.expected_A_pct * 100)}/${Math.round(f.expected_B_pct * 100)}/${Math.round(f.expected_C_pct * 100)}/${Math.round(f.expected_D_pct * 100)}%`;
      farmMixMap.set(f.farm_id, mixStr);
    }
  }

  const totalExpected = summaries.reduce((acc, f) => acc + f.expected_capacity, 0);
  const totalActual = summaries.reduce((acc, f) => acc + f.actual_total, 0);
  const totalVariance = summaries.reduce((acc, f) => acc + f.variance_total, 0);
  const totalResidual = summaries.reduce((acc, f) => acc + f.local_residual_t, 0);

  return (
    <TableShell>
      <Thead>
        <Th>Farm ID</Th>
        <Th>Farm Name</Th>
        <Th align="right">Expected (t)</Th>
        <Th align="right">Planned Mix (A/B/C/D)</Th>
        <Th align="right">Actual A / B / C / D (t)</Th>
        <Th align="center">Segment Variance</Th>
        <Th align="right">Local Residual</Th>
      </Thead>
      <Tbody>
        {summaries.map((f) => {
          const mixLabel = farmMixMap.get(f.farm_id) || '—';
          return (
            <Row key={f.farm_id}>
              <Td mono>{f.farm_id}</Td>
              <Td>{f.farm_name}</Td>
              <Td mono align="right">
                {fmtT(f.expected_capacity)}
              </Td>
              <Td mono align="right" muted>
                {mixLabel}
              </Td>
              <Td mono align="right">
                {f.actual_A.toFixed(1)} / {f.actual_B.toFixed(1)} / {f.actual_C.toFixed(1)} /{' '}
                {f.actual_D.toFixed(1)}
              </Td>
              <Td align="center">
                <div className="variance-group">
                  <VariancePill value={f.variance_A} />
                  <VariancePill value={f.variance_B} />
                  <VariancePill value={f.variance_C} />
                  <VariancePill value={f.variance_D} />
                </div>
              </Td>
              <Td mono align="right">
                {fmtT(f.local_residual_t)}
              </Td>
            </Row>
          );
        })}
      </Tbody>
      <TotalRow>
        <Td>
          <span className="label-caps">Total</span>
        </Td>
        <Td>{summaries.length} Farms</Td>
        <Td mono align="right">
          {fmtT(totalExpected)}
        </Td>
        <Td />
        <Td mono align="right">
          {fmtT(totalActual)}
        </Td>
        <Td align="center" mono>
          <span className={totalVariance < 0 ? 'text-negative' : 'text-positive'}>
            {totalVariance > 0 ? '+' : ''}
            {totalVariance.toFixed(1)}t
          </span>
        </Td>
        <Td mono align="right">
          {fmtT(totalResidual)}
        </Td>
      </TotalRow>
    </TableShell>
  );
}
