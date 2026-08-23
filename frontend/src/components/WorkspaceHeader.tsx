import { Pill } from './primitives';

interface WorkspaceHeaderProps {
  statusLabel: string;
  validated: boolean;
  isReloading?: boolean;
  onReload: () => void;
  assistantOpen: boolean;
  onToggleAssistant: () => void;
}

/**
 * Top operational header displaying brand title, data validation status,
 * reload action button, and assistant drawer toggle.
 */
export function WorkspaceHeader({
  statusLabel,
  validated,
  isReloading = false,
  onReload,
  assistantOpen,
  onToggleAssistant,
}: WorkspaceHeaderProps) {
  return (
    <header className="workspace-header">
      <div className="header-container">
        <div className="header-brand">
          <h1 className="brand-title">
            Atlas Fresh <span className="brand-dot">•</span>
            <span className="brand-subtitle">Daily Planning Workspace</span>
          </h1>
          <span className="header-status-pill">
            <Pill tone={validated ? 'positive' : 'warning'}>
              {validated ? '✓ ' : '! '}
              {statusLabel}
            </Pill>
          </span>
        </div>

        <div className="header-actions">
          <button
            type="button"
            onClick={onReload}
            disabled={isReloading}
            className="btn btn-secondary font-mono"
            title="Reload dataset and re-run planning engine"
          >
            {isReloading ? '↻ Reloading...' : '↻ Reload Data'}
          </button>
          <button
            type="button"
            onClick={onToggleAssistant}
            className={`btn ${assistantOpen ? 'btn-primary' : 'btn-secondary'}`}
          >
            {assistantOpen ? 'Hide Assistant' : 'Show Assistant'}
          </button>
        </div>
      </div>
    </header>
  );
}

