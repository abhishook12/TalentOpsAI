import React from 'react';

const VARIABLES = [
  { label: 'First Name', tag: '{{FirstName}}' },
  { label: 'Last Name', tag: '{{LastName}}' },
  { label: 'Full Name', tag: '{{Name}}' },
  { label: 'Company', tag: '{{Company}}' },
  { label: 'Title', tag: '{{Title}}' },
  { label: 'Location', tag: '{{Location}}' },
];

export default function PersonalizationToolbar({ onInsert }) {
  return (
    <div className="flex flex-wrap items-center gap-2 p-2 bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-lg mb-3">
      <span className="text-xs text-[var(--text-muted)] uppercase tracking-wider font-semibold mr-2">Variables:</span>
      {VARIABLES.map(v => (
        <button
          key={v.tag}
          type="button"
          onClick={() => onInsert(v.tag)}
          className="text-xs px-2 py-1 bg-[var(--accent)]/10 text-[var(--accent)] hover:bg-[var(--accent)]/20 rounded font-mono transition-colors"
        >
          {v.label}
        </button>
      ))}
    </div>
  );
}
