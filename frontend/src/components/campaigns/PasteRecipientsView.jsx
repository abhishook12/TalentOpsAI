import React, { useState, useEffect } from 'react';

export default function PasteRecipientsView({ onAddRecipients }) {
  const [text, setText] = useState('');
  const [stats, setStats] = useState({ valid: 0, invalid: 0, duplicates: 0, parsed: [] });

  useEffect(() => {
    // Parse on change
    const lines = text.split(/[\n,;]+/).map(l => l.trim()).filter(l => l.length > 0);
    let validCount = 0;
    let invalidCount = 0;
    let dupCount = 0;
    const parsedRecipients = [];
    const seenEmails = new Set();

    const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/i;

    lines.forEach(line => {
      const match = line.match(emailRegex);
      if (match) {
        const email = match[1].toLowerCase();
        if (seenEmails.has(email)) {
          dupCount++;
        } else {
          seenEmails.add(email);
          // Try to extract name (e.g., "John Doe <john@doe.com>")
          let name = '';
          const nameMatch = line.replace(emailRegex, '').replace(/[<>]/g, '').trim();
          if (nameMatch) name = nameMatch;
          
          parsedRecipients.push({
            id: `p_${Date.now()}_${validCount}`,
            email,
            name: name || email.split('@')[0],
            source: 'paste',
            status: 'valid'
          });
          validCount++;
        }
      } else {
        invalidCount++;
      }
    });

    setStats({ valid: validCount, invalid: invalidCount, duplicates: dupCount, parsed: parsedRecipients });
  }, [text]);

  const handleAdd = () => {
    if (stats.parsed.length > 0) {
      onAddRecipients(stats.parsed);
      setText('');
    }
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-surface)] p-4">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Paste Directly</h3>
        <p className="text-xs text-[var(--text-muted)]">
          Paste email addresses from Outlook, Excel, or any text source. One per line or comma separated.
        </p>
      </div>

      <textarea
        className="flex-1 w-full bg-[var(--bg-page)] border border-[var(--border)] rounded-lg p-3 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] resize-none"
        placeholder="john@example.com&#10;John Smith <john@example.com>"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />

      {text && (
        <div className="mt-4 p-3 bg-[var(--bg-page)] rounded-lg border border-[var(--border)] flex items-center justify-between">
          <div className="flex gap-4 text-xs">
            <span className="text-green-500 font-medium">{stats.valid} Valid</span>
            <span className="text-yellow-500 font-medium">{stats.duplicates} Duplicates</span>
            <span className="text-red-500 font-medium">{stats.invalid} Invalid</span>
          </div>
          <button 
            onClick={handleAdd}
            disabled={stats.valid === 0}
            className="px-4 py-1.5 bg-[var(--accent)] text-white text-xs font-medium rounded shadow hover:bg-[var(--accent)]/90 disabled:opacity-50 transition-colors"
          >
            Add {stats.valid} Recipients
          </button>
        </div>
      )}
    </div>
  );
}
