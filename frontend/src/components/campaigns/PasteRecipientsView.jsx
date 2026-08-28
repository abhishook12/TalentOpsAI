import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Sparkles, Clock, History, Mail, User, Plus, Check, X, Building2, ChevronRight } from 'lucide-react';
import api from '../../services/api';

const HISTORY_STORAGE_KEY = 'talentops_recipient_history';

export default function PasteRecipientsView({ onAddRecipients }) {
  const [text, setText] = useState('');
  const [stats, setStats] = useState({ valid: 0, invalid: 0, duplicates: 0, parsed: [] });
  const [suggestions, setSuggestions] = useState([]);
  const [localHistory, setLocalHistory] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeQuery, setActiveQuery] = useState('');
  const [cursorPosition, setCursorPosition] = useState({ top: 0, left: 0 });
  const [recentRecipients, setRecentRecipients] = useState([]);
  
  const textareaRef = useRef(null);
  const suggestionsBoxRef = useRef(null);

  // 1. Load local history from localStorage and fetch top recent recipients from backend
  useEffect(() => {
    try {
      const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setLocalHistory(Array.isArray(parsed) ? parsed : []);
      }
    } catch (e) {
      console.warn('Failed to load recipient history', e);
    }

    // Fetch initial recent campaign recipients from backend
    api.get('/campaigns/recent-recipients', { params: { limit: 12 } })
      .then(res => {
        if (res.data?.items) {
          setRecentRecipients(res.data.items);
        }
      })
      .catch(() => {});
  }, []);

  // 2. Parse text input in real-time
  useEffect(() => {
    const lines = text.split(/[\n,;]+/).map(l => l.trim()).filter(l => l.length > 0);
    let validCount = 0;
    let invalidCount = 0;
    let dupCount = 0;
    const parsedRecipients = [];
    const seenEmails = new Set();

    const emailRegex = /([a-zA-Z0-9._+-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/i;

    lines.forEach(line => {
      const match = line.match(emailRegex);
      if (match) {
        const email = match[1].toLowerCase();
        if (seenEmails.has(email)) {
          dupCount++;
        } else {
          seenEmails.add(email);
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

  // 3. Extract the active word/line under the cursor for predictive suggestions
  const getCurrentFragment = useCallback(() => {
    if (!textareaRef.current) return '';
    const cursorPos = textareaRef.current.selectionStart || 0;
    const textBeforeCursor = text.substring(0, cursorPos);
    const lastLineBreak = Math.max(textBeforeCursor.lastIndexOf('\n'), textBeforeCursor.lastIndexOf(','), textBeforeCursor.lastIndexOf(';'));
    const fragment = (lastLineBreak === -1 ? textBeforeCursor : textBeforeCursor.substring(lastLineBreak + 1)).trim();
    return fragment;
  }, [text]);

  // 4. Query suggestions whenever active fragment changes
  useEffect(() => {
    const fragment = getCurrentFragment();
    setActiveQuery(fragment);

    if (!fragment || fragment.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const cleanQ = fragment.toLowerCase();

    // Fast local match first
    const localMatches = localHistory
      .filter(item => 
        (item.email && item.email.toLowerCase().includes(cleanQ)) ||
        (item.name && item.name.toLowerCase().includes(cleanQ)) ||
        (item.company && item.company.toLowerCase().includes(cleanQ))
      )
      .slice(0, 5);

    // Fetch from backend API
    const timer = setTimeout(() => {
      api.get('/campaigns/recent-recipients', { params: { q: cleanQ, limit: 8 } })
        .then(res => {
          const apiItems = res.data?.items || [];
          const combined = [...localMatches];
          const seen = new Set(localMatches.map(m => m.email.toLowerCase()));

          apiItems.forEach(item => {
            const em = item.email.toLowerCase();
            if (!seen.has(em)) {
              seen.add(em);
              combined.push(item);
            }
          });

          setSuggestions(combined.slice(0, 6));
          setShowSuggestions(combined.length > 0);
          setSelectedIndex(0);
        })
        .catch(() => {
          setSuggestions(localMatches);
          setShowSuggestions(localMatches.length > 0);
          setSelectedIndex(0);
        });
    }, 120);

    return () => clearTimeout(timer);
  }, [text, getCurrentFragment, localHistory]);

  // 5. Apply selected suggestion to textarea
  const applySuggestion = (suggestion) => {
    if (!textareaRef.current) return;
    const cursorPos = textareaRef.current.selectionStart || 0;
    const textBeforeCursor = text.substring(0, cursorPos);
    const textAfterCursor = text.substring(cursorPos);
    const lastLineBreak = Math.max(textBeforeCursor.lastIndexOf('\n'), textBeforeCursor.lastIndexOf(','), textBeforeCursor.lastIndexOf(';'));

    const beforeFragment = lastLineBreak === -1 ? '' : textBeforeCursor.substring(0, lastLineBreak + 1);
    const replacement = suggestion.name && suggestion.name !== suggestion.email.split('@')[0]
      ? `${suggestion.name} <${suggestion.email}>`
      : suggestion.email;

    const newText = (beforeFragment + replacement + '\n' + textAfterCursor.trimStart());
    setText(newText);
    setShowSuggestions(false);
    setSuggestions([]);

    // Focus back to textarea
    setTimeout(() => {
      if (textareaRef.current) {
        const nextPos = (beforeFragment + replacement + '\n').length;
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(nextPos, nextPos);
      }
    }, 10);
  };

  // 6. Quick add a contact from chip
  const handleQuickAddChip = (contact) => {
    const formatted = contact.name && contact.name !== contact.email.split('@')[0]
      ? `${contact.name} <${contact.email}>`
      : contact.email;
    
    setText(prev => {
      const trimmed = prev.trim();
      return trimmed ? `${trimmed}\n${formatted}` : formatted;
    });
  };

  // 7. Handle keyboard navigation inside suggestions dropdown
  const handleKeyDown = (e) => {
    if (showSuggestions && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % suggestions.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + suggestions.length) % suggestions.length);
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (suggestions[selectedIndex]) {
          applySuggestion(suggestions[selectedIndex]);
        }
      } else if (e.key === 'Escape') {
        setShowSuggestions(false);
      }
    }
  };

  // 8. Save recipients to persistent history and dispatch
  const handleAdd = () => {
    if (stats.parsed.length > 0) {
      // Update local storage history
      try {
        const existingHistory = [...localHistory];
        const historyMap = new Map(existingHistory.map(h => [h.email.toLowerCase(), h]));

        stats.parsed.forEach(p => {
          const em = p.email.toLowerCase();
          const current = historyMap.get(em) || { email: em, name: p.name, use_count: 0 };
          current.name = p.name || current.name;
          current.use_count = (current.use_count || 0) + 1;
          current.last_used = new Date().toISOString();
          historyMap.set(em, current);
        });

        const updatedHistory = Array.from(historyMap.values())
          .sort((a, b) => (b.use_count || 0) - (a.use_count || 0))
          .slice(0, 100);

        setLocalHistory(updatedHistory);
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updatedHistory));
      } catch (e) {
        console.warn('Failed to update recipient history', e);
      }

      onAddRecipients(stats.parsed);
      setText('');
      setShowSuggestions(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-surface)] p-4 relative">
      <div className="mb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Paste Directly</h3>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[var(--brand)]/15 text-[var(--brand)] border border-[var(--brand)]/30">
              <Sparkles size={11} /> Smart Predictor
            </span>
          </div>
          <span className="text-[11px] text-[var(--text-muted)] flex items-center gap-1">
            <kbd className="px-1 py-0.5 text-[10px] bg-[var(--bg-page)] border border-[var(--border)] rounded font-mono">Tab ↹</kbd> or <kbd className="px-1 py-0.5 text-[10px] bg-[var(--bg-page)] border border-[var(--border)] rounded font-mono">↵ Enter</kbd> to predict
          </span>
        </div>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">
          Type or paste email addresses. As you type, the engine automatically predicts past recipients.
        </p>
      </div>

      {/* Quick-Add Recent Recipient Chips */}
      {recentRecipients.length > 0 && (
        <div className="mb-2.5 flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          <span className="text-[11px] font-medium text-[var(--text-muted)] flex items-center gap-1 whitespace-nowrap">
            <History size={12} className="text-[var(--brand)]" /> Quick Add:
          </span>
          {recentRecipients.slice(0, 5).map((rec, idx) => (
            <button
              key={`rec_${rec.email}_${idx}`}
              type="button"
              onClick={() => handleQuickAddChip(rec)}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11.5px] bg-[var(--bg-page)] hover:bg-[var(--bg-hover)] border border-[var(--card-border)] hover:border-[var(--brand)] text-[var(--text-primary)] transition-all cursor-pointer whitespace-nowrap shadow-xs group"
              title={`Click to insert ${rec.name} <${rec.email}>`}
            >
              <Plus size={11} className="text-[var(--text-muted)] group-hover:text-[var(--brand)]" />
              <span className="font-medium">{rec.name || rec.email.split('@')[0]}</span>
              {rec.company && (
                <span className="text-[10px] text-[var(--text-muted)] border-l border-[var(--border)] pl-1">
                  {rec.company}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Main Textarea with Predictive Suggestions Floating Popover */}
      <div className="relative flex-1 flex flex-col min-h-0">
        <textarea
          ref={textareaRef}
          className="flex-1 w-full bg-[var(--bg-page)] border border-[var(--border)] rounded-lg p-3 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--brand)] resize-none font-mono text-[13px] leading-relaxed"
          placeholder="Start typing an email, name, or company...&#10;e.g. michelle.crowell@akkodis.com&#10;John Smith <john@company.com>"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        {/* Predictive Suggestions Dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div 
            ref={suggestionsBoxRef}
            className="absolute z-50 left-2 right-2 bottom-3 bg-[var(--card-bg, #1a1a24)] border border-[var(--brand)]/60 rounded-xl shadow-2xl overflow-hidden backdrop-blur-md animate-in fade-in slide-in-from-bottom-2 duration-150"
            style={{ maxHeight: '220px' }}
          >
            <div className="px-3 py-1.5 bg-[var(--brand)]/10 border-b border-[var(--brand)]/20 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--brand)]">
                <Sparkles size={13} className="animate-pulse" />
                Predicted Matches from History ({suggestions.length})
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">
                Use ↑ ↓ arrows & Tab / Enter to select
              </span>
            </div>

            <div className="max-h-[175px] overflow-y-auto divide-y divide-[var(--card-border)]/40">
              {suggestions.map((item, idx) => (
                <div
                  key={`sug_${item.email}_${idx}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    applySuggestion(item);
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`px-3 py-2 flex items-center justify-between cursor-pointer transition-colors ${
                    selectedIndex === idx 
                      ? 'bg-[var(--brand)]/20 text-[var(--text-primary)] border-l-3 border-[var(--brand)]' 
                      : 'hover:bg-[var(--bg-hover)] text-[var(--text-primary)]'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      selectedIndex === idx ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-page)] text-[var(--text-muted)]'
                    }`}>
                      {item.name ? item.name.charAt(0).toUpperCase() : <Mail size={12} />}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[12.5px] font-medium truncate text-[var(--text-primary)]">
                          {item.name || item.email.split('@')[0]}
                        </span>
                        {item.company && (
                          <span className="text-[10.5px] px-1.5 py-0.2 rounded bg-[var(--bg-page)] text-[var(--text-muted)] border border-[var(--border)]">
                            {item.company}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)] truncate font-mono">
                        {item.email}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    {item.use_count > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium">
                        Used {item.use_count}x
                      </span>
                    )}
                    {item.source === 'database' && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 font-medium">
                        Directory
                      </span>
                    )}
                    <ChevronRight size={14} className={`transition-transform ${selectedIndex === idx ? 'text-[var(--brand)] translate-x-0.5' : 'text-[var(--text-muted)]'}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer / Add Action */}
      {text && (
        <div className="mt-3 p-3 bg-[var(--bg-page)] rounded-lg border border-[var(--border)] flex items-center justify-between">
          <div className="flex gap-3 text-xs">
            <span className="text-green-500 font-medium flex items-center gap-1">
              <Check size={12} /> {stats.valid} Valid
            </span>
            {stats.duplicates > 0 && (
              <span className="text-yellow-500 font-medium">
                {stats.duplicates} Duplicates
              </span>
            )}
            {stats.invalid > 0 && (
              <span className="text-red-500 font-medium">
                {stats.invalid} Invalid
              </span>
            )}
          </div>
          <button 
            onClick={handleAdd}
            disabled={stats.valid === 0}
            className="px-4 py-1.5 bg-[var(--brand)] text-white text-xs font-semibold rounded-md shadow-sm hover:brightness-110 disabled:opacity-50 transition-all cursor-pointer flex items-center gap-1.5"
          >
            <Plus size={13} /> Add {stats.valid} Recipients
          </button>
        </div>
      )}
    </div>
  );
}

