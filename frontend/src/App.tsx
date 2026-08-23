import { useEffect, useState } from 'react';
import { AssistantPanel } from './components/AssistantPanel';
import { CommercialTable } from './components/CommercialTable';
import { KpiGrid } from './components/KpiGrid';
import { ProductionTable } from './components/ProductionTable';
import { RootCauseBanner } from './components/RootCauseBanner';
import { TraceabilityTable } from './components/TraceabilityTable';
import { WorkspaceHeader } from './components/WorkspaceHeader';
import { fetchDataset, fetchPlan } from './services/api';
import type { DatasetResponse, PlanResult } from './types';

type TabId = 'production' | 'commercial' | 'traceability';

function App() {
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [dataset, setDataset] = useState<DatasetResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isReloading, setIsReloading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>('production');
  const [assistantOpen, setAssistantOpen] = useState<boolean>(true);
  const [reloadedAt, setReloadedAt] = useState<string | null>(null);

  const loadData = async (showReloadingState = false) => {
    if (showReloadingState) {
      setIsReloading(true);
    } else {
      setIsLoading(true);
    }

    try {
      const [planData, rawDataset] = await Promise.all([fetchPlan(), fetchDataset()]);
      setPlan(planData);
      setDataset(rawDataset);
      setError(null);
      setValidationErrors([]);
      setReloadedAt(new Date().toLocaleTimeString('en-GB'));
    } catch (err: any) {
      console.error('Failed to load Atlas Fresh operational data:', err);
      setPlan(null);
      setDataset(null);

      const detail = err.response?.data?.detail;
      const mainMsg =
        err.response?.data?.message ||
        err.message ||
        'Unable to connect to the Atlas Fresh backend server. Ensure FastAPI is running on port 8000.';
      setError(mainMsg);

      if (Array.isArray(detail) && detail.length > 0) {
        const errorList = detail.map(
          (d: any) => `${d.sheet} ${d.entity_id ? `[${d.entity_id}]` : ''}: ${d.message}`
        );
        setValidationErrors(errorList);
      } else {
        setValidationErrors([]);
      }
    } finally {
      setIsLoading(false);
      setIsReloading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const atRiskTags = plan
    ? plan.client_statuses.filter((cs) => cs.status !== 'COMPLETE').map((cs) => cs.client_id)
    : [];

  const dynamicStatusLabel = error
    ? 'Data Validation Error'
    : dataset
      ? `Data Validated (${dataset.farms.length} Farms, ${dataset.clients.length} Clients, ${dataset.station.export_conditioning_capacity_t}t Station)`
      : plan
        ? `Data Validated (${plan.farm_summaries.length} Farms, ${plan.client_statuses.length} Clients, ${plan.kpis.station_capacity_t}t Station)`
        : 'Data Validated';

  const tabs: Array<{ id: TabId; label: string }> = [
    {
      id: 'production',
      label: `Production (${plan ? plan.farm_summaries.length : 20} Farms)`,
    },
    {
      id: 'commercial',
      label: `Commercial (${plan ? plan.client_statuses.length : 10} Clients)`,
    },
    {
      id: 'traceability',
      label: `Traceability (${plan ? plan.allocations.length : 0} Batches)`,
    },
  ];

  return (
    <>
      <WorkspaceHeader
        statusLabel={dynamicStatusLabel}
        validated={!error}
        isReloading={isReloading}
        onReload={() => loadData(true)}
        assistantOpen={assistantOpen}
        onToggleAssistant={() => setAssistantOpen((prev) => !prev)}
      />

      <main className="workspace-main">
        <div className="content-column">
          {isLoading && !plan && !error ? (
            <div className="state-container">
              <div className="spinner" />
              <p className="text-muted font-mono" style={{ fontSize: '13px' }}>
                Executing deterministic allocation engine and loading dataset...
              </p>
            </div>
          ) : error ? (
            <div className="state-container">
              <div className="error-card">
                <strong style={{ display: 'block', marginBottom: '8px' }}>Validation / Server Error:</strong>
                <p style={{ marginBottom: validationErrors.length > 0 ? '10px' : '0' }}>{error}</p>
                {validationErrors.length > 0 && (
                  <ul style={{ textAlign: 'left', paddingLeft: '20px', fontSize: '12.5px', marginTop: '6px' }}>
                    {validationErrors.map((errItem, idx) => (
                      <li key={idx} style={{ marginBottom: '4px' }}>
                        {errItem}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <button
                type="button"
                onClick={() => loadData(true)}
                disabled={isReloading}
                className="btn btn-secondary"
                style={{ marginTop: '12px' }}
              >
                {isReloading ? '↻ Retrying...' : '↻ Retry Connection'}
              </button>
            </div>
          ) : plan ? (
            <>
              <KpiGrid kpis={plan.kpis} atRiskTags={atRiskTags} />
              <RootCauseBanner plan={plan} />

              <div className="tab-navigation">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`tab-btn ${activeTab === tab.id ? 'tab-btn-active' : ''}`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {activeTab === 'production' && (
                <ProductionTable
                  summaries={plan.farm_summaries}
                  farms={dataset?.farms}
                />
              )}

              {activeTab === 'commercial' && (
                <CommercialTable
                  statuses={plan.client_statuses}
                  clients={dataset?.clients}
                />
              )}

              {activeTab === 'traceability' && (
                <TraceabilityTable
                  allocations={plan.allocations}
                  localDetails={plan.local_details}
                />
              )}

              {reloadedAt && (
                <p className="font-mono text-subtle" style={{ fontSize: '11px', marginTop: '12px' }}>
                  Live dataset synchronized at {reloadedAt}
                </p>
              )}
            </>
          ) : null}
        </div>

        {assistantOpen && <AssistantPanel />}
      </main>
    </>
  );
}

export default App;
