import type { Allocation, LocalDetail } from '../types';
import { Row, TableShell, Tbody, Td, Th, Thead, TotalRow } from './DataTable';
import { Pill, fmtEur, fmtT } from './primitives';

interface TraceabilityTableProps {
  allocations: Allocation[];
  localDetails: LocalDetail[];
}

/**
 * Traceability view showing granular 5t-step export allocations from farms to clients,
 * quality upgrades, and residual fruit diverted to local markets at 10% value.
 */
export function TraceabilityTable({ allocations, localDetails }: TraceabilityTableProps) {
  const totalAllocatedTonnes = allocations.reduce((acc, a) => acc + a.tonnes, 0);
  const totalExportRevenue = allocations.reduce((acc, a) => acc + a.export_revenue, 0);

  const totalLocalTonnes = localDetails.reduce((acc, l) => acc + l.tonnes, 0);
  const totalLocalValue = localDetails.reduce((acc, l) => acc + l.local_value, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div>
        <h3 className="label-caps" style={{ marginBottom: '12px', fontSize: '12px' }}>
          Export Allocation Traceability ({allocations.length} Batches)
        </h3>
        <TableShell>
          <Thead>
            <Th>Farm ID</Th>
            <Th align="center">Segment</Th>
            <Th>Client ID</Th>
            <Th align="right">Tonnes Allocated</Th>
            <Th align="center">Quality Upgrade</Th>
            <Th align="right">Export Revenue</Th>
          </Thead>
          <Tbody>
            {allocations.map((alloc, idx) => (
              <Row key={`${alloc.farm_id}-${alloc.client_id}-${alloc.segment}-${idx}`}>
                <Td mono>{alloc.farm_id}</Td>
                <Td align="center">
                  <Pill>{alloc.segment}</Pill>
                </Td>
                <Td mono>{alloc.client_id}</Td>
                <Td mono align="right">
                  {fmtT(alloc.tonnes)}
                </Td>
                <Td align="center">
                  {alloc.quality_upgrade ? (
                    <Pill tone="positive">UPGRADE</Pill>
                  ) : (
                    <span className="text-subtle">—</span>
                  )}
                </Td>
                <Td mono align="right">
                  {fmtEur(alloc.export_revenue)}
                </Td>
              </Row>
            ))}
          </Tbody>
          <TotalRow>
            <Td>
              <span className="label-caps">Total Export</span>
            </Td>
            <Td />
            <Td />
            <Td mono align="right">
              {fmtT(totalAllocatedTonnes)}
            </Td>
            <Td />
            <Td mono align="right">
              {fmtEur(totalExportRevenue)}
            </Td>
          </TotalRow>
        </TableShell>
      </div>

      <div>
        <h3 className="label-caps" style={{ marginBottom: '12px', fontSize: '12px' }}>
          Local Market Residual Breakdown (10% Value Realization)
        </h3>
        <TableShell>
          <Thead>
            <Th>Farm ID</Th>
            <Th align="center">Segment</Th>
            <Th align="right">Volume (t)</Th>
            <Th align="right">Ref Price (€/t)</Th>
            <Th align="right">Realized Value (10%)</Th>
          </Thead>
          <Tbody>
            {localDetails.map((item, idx) => (
              <Row key={`${item.farm_id}-${item.segment}-${idx}`}>
                <Td mono>{item.farm_id}</Td>
                <Td align="center">
                  <Pill>{item.segment}</Pill>
                </Td>
                <Td mono align="right">
                  {fmtT(item.tonnes)}
                </Td>
                <Td mono align="right" muted>
                  {fmtEur(item.reference_price)}
                </Td>
                <Td mono align="right">
                  {fmtEur(item.local_value)}
                </Td>
              </Row>
            ))}
          </Tbody>
          <TotalRow>
            <Td>
              <span className="label-caps">Total Local</span>
            </Td>
            <Td />
            <Td mono align="right">
              {fmtT(totalLocalTonnes)}
            </Td>
            <Td />
            <Td mono align="right">
              {fmtEur(totalLocalValue)}
            </Td>
          </TotalRow>
        </TableShell>
      </div>
    </div>
  );
}
