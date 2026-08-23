import { useState } from 'react';
import type { AssistantPreset } from '../types';
import { TaggedText } from './primitives';

const ASSISTANT_PRESETS: AssistantPreset[] = [
  {
    id: 'risk',
    question: 'Which clients are at risk and why?',
    answer:
      'Logistics Assistant backend will be connected in Step 8. This placeholder will query the grounded planning engine directly.',
  },
  {
    id: 'gaps',
    question: 'Which farm/segment gaps matter most today?',
    answer:
      'Logistics Assistant backend will be connected in Step 8. This placeholder will query the grounded planning engine directly.',
  },
  {
    id: 'local',
    question: 'Why are tonnes going local and what is their estimated value?',
    answer:
      'Logistics Assistant backend will be connected in Step 8. This placeholder will query the grounded planning engine directly.',
  },
];

interface AssistantPanelProps {
  statusLabel?: string;
  onAsk?: (query: string) => string;
}

/**
 * AI Logistics Assistant UI panel.
 * Connects to the backend AI assistant API endpoint in Step 8.
 */
export function AssistantPanel({
  statusLabel = 'Placeholder Mode (Step 8)',
  onAsk,
}: AssistantPanelProps) {
  const [currentAnswer, setCurrentAnswer] = useState<string>(
    'Select a question above or type an operational query. (AI Assistant backend integration in Step 8)'
  );
  const [draft, setDraft] = useState('');

  const handlePresetClick = (preset: AssistantPreset) => {
    if (onAsk) {
      setCurrentAnswer(onAsk(preset.question));
    } else {
      setCurrentAnswer(preset.answer);
    }
  };

  const handleSend = () => {
    const query = draft.trim();
    if (!query) return;

    if (onAsk) {
      setCurrentAnswer(onAsk(query));
    } else {
      setCurrentAnswer(
        `Received query: "${query}". AI Assistant backend integration will be connected in Step 8.`
      );
    }
    setDraft('');
  };

  return (
    <aside className="assistant-sidebar">
      <div className="assistant-panel-card">
        <div className="assistant-panel-header">
          <span className="label-caps">Logistics Assistant</span>
          <div className="assistant-status-tag">
            <div className="status-dot" style={{ backgroundColor: 'var(--warning)' }} />
            <span style={{ color: 'var(--warning)' }}>{statusLabel}</span>
          </div>
        </div>

        <div className="assistant-panel-body">
          <div className="preset-queries-group">
            <span className="label-caps text-subtle">Preset Questions</span>
            {ASSISTANT_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => handlePresetClick(preset)}
                className="preset-query-btn"
              >
                {preset.question}
              </button>
            ))}
          </div>

          <div className="assistant-response-bubble">
            <TaggedText text={currentAnswer} accent />
          </div>
        </div>

        <div className="assistant-panel-footer">
          <div className="assistant-input-wrapper">
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about allocation, supply..."
              aria-label="Ask assistant"
              className="assistant-input"
            />
            <button
              type="button"
              onClick={handleSend}
              className="assistant-send-btn"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
