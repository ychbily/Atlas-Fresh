import React from 'react';

export type PillTone = 'neutral' | 'positive' | 'warning' | 'negative';

interface PillProps {
  children: React.ReactNode;
  tone?: PillTone;
  className?: string;
}

/**
 * Clean status and categorical badge component.
 */
export function Pill({ children, tone = 'neutral', className = '' }: PillProps) {
  const toneClass = {
    neutral: 'pill-neutral',
    positive: 'pill-positive',
    warning: 'pill-warning',
    negative: 'pill-negative',
  }[tone];

  return <span className={`pill ${toneClass} ${className}`}>{children}</span>;
}

/**
 * Metric variance badge displaying positive values with a '+' and green tone,
 * negative values with a '-' and red tone, or zero in neutral tone.
 */
export function VariancePill({ value }: { value: number }) {
  const tone: PillTone = value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';
  const prefix = value > 0 ? '+' : '';
  return (
    <Pill tone={tone}>
      {prefix}
      {value.toFixed(1)}
    </Pill>
  );
}

/**
 * Parses and highlights entity references enclosed in square brackets (e.g. [C02], [F01], [Segment A]).
 */
export function TaggedText({ text, accent = false }: { text: string; accent?: boolean }) {
  const parts = text.split(/(\[[^\]]+\])/g);
  return (
    <>
      {parts.map((part, idx) => {
        if (part.startsWith('[') && part.endsWith(']')) {
          return (
            <span key={idx} className={accent ? 'tag-accent' : 'tag-chip'}>
              {part}
            </span>
          );
        }
        return <span key={idx}>{part}</span>;
      })}
    </>
  );
}

/**
 * Format a number into tonnes notation (e.g. 560.0t).
 */
export function fmtT(tonnes: number): string {
  return `${tonnes.toFixed(1)}t`;
}

/**
 * Format a currency amount in EUR (e.g. €549,500).
 */
export function fmtEur(amount: number): string {
  return `€${Math.round(amount).toLocaleString('en-US')}`;
}

/**
 * Format a percentage (e.g. 89.3%).
 */
export function fmtPct(pct: number): string {
  return `${pct.toFixed(1)}%`;
}
