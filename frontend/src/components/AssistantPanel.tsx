import { useState, useEffect } from 'react';
import type { AssistantPreset, AssistantResponse } from '../types';
import { askAssistant } from '../services/api';
import { TaggedText } from './primitives';

const ASSISTANT_PRESETS: AssistantPreset[] = [
  {
    id: 'risk',
    question: 'Which clients are at risk and why?',
  },
  {
    id: 'gaps',
    question: 'Which farm/segment gaps matter most today?',
  },
  {
    id: 'local',
    question: 'Why are 60 t going local and what is their estimated value?',
  },
];

/**
 * AI Logistics Assistant UI panel.
 * Connects to the backend Grounded Planning Assistant endpoint.
 */
export function AssistantPanel() {
  const [currentResponse, setCurrentResponse] = useState<AssistantResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [draft, setDraft] = useState<string>('');

  const executeQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    setIsLoading(true);
    try {
      const response = await askAssistant(queryText);
      setCurrentResponse(response);
    } catch (err: any) {
      console.error('Assistant query error:', err);
      setCurrentResponse({
        query: queryText,
        answer: 'Failed to connect to the logistics assistant service. Please verify that the FastAPI backend server is running.',
        source: 'deterministic_summary',
        status_label: 'Deterministic Summary (Offline)',
        cited_ids: [],
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Automatically load the primary operational risk explanation on mount
    executeQuery(ASSISTANT_PRESETS[0].question);
  }, []);

  const handlePresetClick = (preset: AssistantPreset) => {
    executeQuery(preset.question);
  };

  const handleSend = () => {
    const query = draft.trim();
    if (!query) return;
    executeQuery(query);
    setDraft('');
  };

  // Determine status dot color based on assistant resolution source
  const getStatusColor = () => {
    if (isLoading) return 'var(--text-muted)';
    if (!currentResponse) return 'var(--warning)';
    if (currentResponse.source === 'llm') return 'var(--positive)';
    if (currentResponse.source === 'deterministic_summary') return 'var(--warning)';
    return 'var(--text-muted)';
  };

  const statusLabel = isLoading
    ? 'Querying Engine...'
    : currentResponse?.status_label || 'Deterministic Summary (No API Key)';

  return (
    <aside className="assistant-sidebar">
      <div className="assistant-panel-card">
        <div className="assistant-panel-header">
          <span className="label-caps">Logistics Assistant</span>
          <div className="assistant-status-tag">
            <div
              className="status-dot"
              style={{ backgroundColor: getStatusColor() }}
            />
            <span style={{ color: getStatusColor(), fontSize: '11px' }}>
              {statusLabel}
            </span>
          </div>
        </div>

        <div className="assistant-panel-body">
          <div className="preset-queries-group">
            <span className="label-caps text-subtle">Preset Questions</span>
            {ASSISTANT_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                disabled={isLoading}
                onClick={() => handlePresetClick(preset)}
                className="preset-query-btn"
              >
                {preset.question}
              </button>
            ))}
          </div>

          <div className="assistant-response-bubble">
            {isLoading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)' }}>
                <div
                  className="spinner"
                  style={{ width: '16px', height: '16px', borderWidth: '2px' }}
                />
                <span className="font-mono" style={{ fontSize: '12px' }}>
                  Evaluating plan & generating grounded explanation...
                </span>
              </div>
            ) : currentResponse ? (
              <>
                {currentResponse.source === 'deterministic_summary' && (
                  <div className="assistant-notice-box notice-box-fallback">
                    <div className="notice-header">
                      <span>⚡ Deterministic Planning Summary</span>
                    </div>
                    <div className="notice-sub font-mono">
                      GROQ_API_KEY not configured. Displaying rule-based deterministic calculations:
                    </div>
                  </div>
                )}

                {currentResponse.source === 'llm' && (
                  <div className="assistant-notice-box notice-box-llm">
                    <div className="notice-header">
                      <span>🟢 Live AI Model ({currentResponse.model || 'openai/gpt-oss-120b'})</span>
                    </div>
                    <div className="notice-sub">
                      Grounded explanation generated from live structured context.
                    </div>
                  </div>
                )}

                {currentResponse.source === 'unsupported' && (
                  <div className="assistant-notice-box notice-box-unsupported">
                    <div className="notice-header">
                      <span>ℹ️ Guardrail Notice</span>
                    </div>
                    <div className="notice-sub">
                      Query is outside the scope of daily operational planning data.
                    </div>
                  </div>
                )}

                <div style={{ whiteSpace: 'pre-line' }}>
                  <TaggedText text={currentResponse.answer} accent />
                </div>
                {currentResponse.cited_ids && currentResponse.cited_ids.length > 0 && (
                  <div
                    style={{
                      marginTop: '12px',
                      paddingTop: '8px',
                      borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <span className="label-caps text-subtle" style={{ fontSize: '10px' }}>
                      Cited IDs:
                    </span>
                    {currentResponse.cited_ids.map((id) => (
                      <span key={id} className="tag-chip" style={{ fontSize: '11px' }}>
                        {id}
                      </span>
                    ))}
                  </div>
                )}
              </>
            ) : null}
          </div>
        </div>

        <div className="assistant-panel-footer">
          <div className="assistant-input-wrapper">
            <input
              type="text"
              value={draft}
              disabled={isLoading}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about allocation, shortages..."
              aria-label="Ask assistant"
              className="assistant-input"
            />
            <button
              type="button"
              disabled={isLoading || !draft.trim()}
              onClick={handleSend}
              className="assistant-send-btn"
            >
              {isLoading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}

