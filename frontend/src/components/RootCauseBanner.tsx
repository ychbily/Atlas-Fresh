import type { PlanResult } from '../types';
import { TaggedText } from './primitives';

interface RootCauseBannerProps {
  plan?: PlanResult | null;
  title?: string;
  body?: string;
}

/**
 * Operational alert banner dynamically summarizing daily shortages and root causes.
 */
export function RootCauseBanner({ plan, title, body }: RootCauseBannerProps) {
  let displayTitle = title;
  let displayBody = body;

  if (!displayTitle || !displayBody) {
    if (!plan || plan.kpis.at_risk_clients === 0) {
      displayTitle = 'Operational Status: Fully Allocated';
      displayBody = plan
        ? `All ${plan.client_statuses.length} client orders are 100% fulfilled. Export volume is ${plan.kpis.export_volume_t}t with ${plan.kpis.local_volume_t}t routed locally.`
        : 'All client demands are fulfilled.';
    } else {
      const atRisk = plan.client_statuses.filter((cs) => cs.status !== 'COMPLETE');
      displayTitle = `Daily Shortage Alert (${atRisk.length} Client${atRisk.length > 1 ? 's' : ''} at Risk)`;

      const descriptions = atRisk.map(
        (cs) =>
          `[${cs.client_id}] received ${cs.allocated.toFixed(1)}t of ${cs.demand.toFixed(1)}t demand (${cs.remaining.toFixed(1)}t shortage — ${cs.reason || 'unfulfilled'})`
      );

      displayBody = descriptions.join('. ') + '.';
    }
  }

  return (
    <div className="root-cause-banner">
      <div className="banner-indicator" />
      <div className="banner-text">
        <span className="banner-title">{displayTitle}: </span>
        <TaggedText text={displayBody} />
      </div>
    </div>
  );
}
