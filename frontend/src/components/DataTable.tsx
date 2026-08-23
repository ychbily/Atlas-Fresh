import React from 'react';

export type TableAlign = 'left' | 'right' | 'center';

export function TableShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="table-shell">
      <table className="data-table">{children}</table>
    </div>
  );
}

export function Thead({ children }: { children: React.ReactNode }) {
  return <thead><tr>{children}</tr></thead>;
}

export function Tbody({ children }: { children: React.ReactNode }) {
  return <tbody>{children}</tbody>;
}

export function Row({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <tr className={className}>{children}</tr>;
}

export function TotalRow({ children }: { children: React.ReactNode }) {
  return <tfoot><tr>{children}</tr></tfoot>;
}

export function Th({
  children,
  align = 'left',
  className = '',
}: {
  children?: React.ReactNode;
  align?: TableAlign;
  className?: string;
}) {
  const alignClass = `text-${align}`;
  return <th className={`${alignClass} ${className}`}>{children}</th>;
}

export function Td({
  children,
  align = 'left',
  mono = false,
  muted = false,
  className = '',
  style,
}: {
  children?: React.ReactNode;
  align?: TableAlign;
  mono?: boolean;
  muted?: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  const alignClass = `text-${align}`;
  const monoClass = mono ? 'font-mono' : '';
  const mutedClass = muted ? 'text-muted' : '';
  return (
    <td style={style} className={`${alignClass} ${monoClass} ${mutedClass} ${className}`}>
      {children}
    </td>
  );
}
