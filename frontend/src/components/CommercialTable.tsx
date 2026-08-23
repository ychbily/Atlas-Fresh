import type { Client, ClientStatus } from '../types';
import { Row, TableShell, Tbody, Td, Th, Thead, TotalRow } from './DataTable';
import { Pill, fmtEur, fmtT } from './primitives';

interface CommercialTableProps {
  statuses: ClientStatus[];
  clients?: Client[];
}

/**
 * Commercial view showing 10 clients sorted by priority price, demand vs allocation,
 * revenue earned, fulfillment status badges, and root cause shortage explanations.
 */
export function CommercialTable({ statuses, clients }: CommercialTableProps) {
  // Map client metadata (price, segment, acceptance mode)
  const clientMetaMap = new Map<string, Client>();
  if (clients) {
    for (const c of clients) {
      clientMetaMap.set(c.client_id, c);
    }
  }

  // Sort by priority price descending (if client metadata available), then client_id
  const sortedStatuses = [...statuses].sort((a, b) => {
    const metaA = clientMetaMap.get(a.client_id);
    const metaB = clientMetaMap.get(b.client_id);
    if (metaA && metaB) {
      if (metaB.export_price_per_t_eur !== metaA.export_price_per_t_eur) {
        return metaB.export_price_per_t_eur - metaA.export_price_per_t_eur;
      }
    }
    return a.client_id.localeCompare(b.client_id);
  });

  const totalDemand = statuses.reduce((acc, c) => acc + c.demand, 0);
  const totalAllocated = statuses.reduce((acc, c) => acc + c.allocated, 0);
  const totalRevenue = statuses.reduce((acc, c) => acc + c.revenue, 0);

  return (
    <TableShell>
      <Thead>
        <Th>Client ID</Th>
        <Th>Client Name</Th>
        <Th align="right">Priority Price</Th>
        <Th align="center">Segment</Th>
        <Th>Mode</Th>
        <Th align="right">Demand (t)</Th>
        <Th align="right">Allocated (t)</Th>
        <Th align="right">Revenue</Th>
        <Th>Status</Th>
        <Th>Shortage Reason</Th>
      </Thead>
      <Tbody>
        {sortedStatuses.map((cs) => {
          const meta = clientMetaMap.get(cs.client_id);
          const price = meta ? fmtEur(meta.export_price_per_t_eur) : '—';
          const segment = meta ? meta.requested_segment : '—';
          const mode = meta ? meta.acceptance_mode : '—';

          return (
            <Row key={cs.client_id}>
              <Td mono>{cs.client_id}</Td>
              <Td>{cs.client_name}</Td>
              <Td mono align="right">
                {price}
              </Td>
              <Td align="center">
                <Pill>{segment}</Pill>
              </Td>
              <Td muted>{mode}</Td>
              <Td mono align="right">
                {fmtT(cs.demand)}
              </Td>
              <Td
                mono
                align="right"
                className={cs.status !== 'COMPLETE' ? 'text-warning' : ''}
              >
                {fmtT(cs.allocated)}
              </Td>
              <Td mono align="right">
                {fmtEur(cs.revenue)}
              </Td>
              <Td>
                <Pill tone={cs.status === 'COMPLETE' ? 'positive' : 'warning'}>
                  {cs.status}
                </Pill>
              </Td>
              <Td muted style={{ whiteSpace: 'normal', maxWidth: '320px' }}>
                {cs.reason || '—'}
              </Td>
            </Row>
          );
        })}
      </Tbody>
      <TotalRow>
        <Td>
          <span className="label-caps">Total</span>
        </Td>
        <Td>{statuses.length} Clients</Td>
        <Td />
        <Td />
        <Td />
        <Td mono align="right">
          {fmtT(totalDemand)}
        </Td>
        <Td mono align="right">
          {fmtT(totalAllocated)}
        </Td>
        <Td mono align="right">
          {fmtEur(totalRevenue)}
        </Td>
        <Td />
        <Td />
      </TotalRow>
    </TableShell>
  );
}
