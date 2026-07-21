import React, { useState, useEffect } from 'react';
import { X, Wand2, Check, ArrowRight } from 'lucide-react';

export default function CampaignReuseWorkflow({ importedEmail, onClose, onComplete }) {
  const [subject, setSubject] = useState(importedEmail?.subject || '');
  const [htmlBody, setHtmlBody] = useState(importedEmail?.html_body || '');
  const [variables, setVariables] = useState([]);
  const [smartCleanupSuggestions, setSmartCleanupSuggestions] = useState([]);

  useEffect(() => {
    if (htmlBody) {
      detectVariables(htmlBody);
      generateSmartCleanup(htmlBody);
    }
  }, [htmlBody]);

  const detectVariables = (body) => {
    // Regex to match {{VariableName}}
    const regex = /{{([^}]+)}}/g;
    const found = [];
    let match;
    while ((match = regex.exec(body)) !== null) {
      if (!found.includes(match[1])) found.push(match[1]);
    }
    setVariables(found);
  };

  const generateSmartCleanup = (body) => {
    // Basic smart cleanup mock for UI purposes based on standard greetings
    const suggestions = [];
    if (body.includes("Hi ") && !body.includes("Hi {{")) {
      const match = body.match(/Hi\s+([A-Za-z]+)[,:]/);
      if (match && match[1]) {
        suggestions.push({
          id: 1,
          type: 'FirstName',
          original: `Hi ${match[1]}`,
          replacement: 'Hi {{FirstName}}'
        });
      }
    }
    
    // Check for common company signatures like "at Amazon"
    if (body.match(/at\s+[A-Z][a-z]+/)) {
      const match = body.match(/at\s+([A-Z][a-z]+)/);
      if (match && match[1] && !["the", "our", "your"].includes(match[1].toLowerCase())) {
         suggestions.push({
          id: 2,
          type: 'Company',
          original: `at ${match[1]}`,
          replacement: 'at {{Company}}'
        });
      }
    }
    
    setSmartCleanupSuggestions(suggestions);
  };

  const applyCleanup = (suggestion) => {
    setHtmlBody(prev => prev.replace(suggestion.original, suggestion.replacement));
    setSmartCleanupSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
  };

  const handleFinish = () => {
    onComplete({ subject, body: htmlBody });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="bg-[var(--bg-page)] border border-[var(--border)] rounded-xl shadow-2xl w-[900px] max-h-[85vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-surface)]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[var(--accent)]/20 text-[var(--accent)] rounded-lg">
              <Wand2 size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[var(--text-primary)]">Reuse Campaign Template</h2>
              <p className="text-sm text-[var(--text-muted)]">Review variables and clean up hardcoded values.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded-lg">
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          
          {/* Smart Cleanup */}
          {smartCleanupSuggestions.length > 0 && (
            <div className="bg-[var(--accent)]/10 border border-[var(--accent)]/30 rounded-xl p-5">
              <div className="flex items-center gap-2 text-[var(--accent)] font-medium mb-3">
                <Wand2 size={18} /> Smart Cleanup Suggestions
              </div>
              <p className="text-sm text-[var(--text-primary)] mb-4">We found some hardcoded values in your old email. Want to replace them with merge variables?</p>
              
              <div className="space-y-2">
                {smartCleanupSuggestions.map(s => (
                  <div key={s.id} className="flex items-center justify-between bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-3">
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-red-400 line-through bg-red-400/10 px-2 py-1 rounded">{s.original}</span>
                      <ArrowRight size={14} className="text-[var(--text-muted)]" />
                      <span className="text-green-400 bg-green-400/10 px-2 py-1 rounded">{s.replacement}</span>
                    </div>
                    <button 
                      onClick={() => applyCleanup(s)}
                      className="px-3 py-1.5 bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white text-xs font-medium rounded-lg"
                    >
                      Apply
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-3 gap-6">
            <div className="col-span-1 space-y-6">
              {/* Variables Found */}
              <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-5">
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 uppercase tracking-wider flex items-center gap-2">
                  <Check size={16} className="text-green-400"/> Variables Detected
                </h3>
                {variables.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)] italic">No {"{{Variables}}"} found in the email.</p>
                ) : (
                  <ul className="space-y-2">
                    {variables.map(v => (
                      <li key={v} className="flex items-center gap-2 text-sm text-[var(--text-primary)]">
                        <Check size={14} className="text-green-500" /> {v}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              
              <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-5">
                 <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2 uppercase tracking-wider">Next Steps</h3>
                 <p className="text-sm text-[var(--text-muted)] leading-relaxed mb-4">
                   Once imported, you will select your new recipients using the builder, preview the campaign, and schedule the send.
                 </p>
                 <button 
                   onClick={handleFinish}
                   className="w-full py-2.5 bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white font-medium rounded-lg shadow-md transition-colors"
                 >
                   Continue to Campaign
                 </button>
              </div>
            </div>
            
            <div className="col-span-2">
              <div className="bg-white rounded-xl border border-[var(--border)] overflow-hidden h-[400px] flex flex-col">
                <div className="p-4 border-b border-[var(--border)] bg-gray-50">
                  <input 
                    type="text" 
                    value={subject} 
                    onChange={e => setSubject(e.target.value)}
                    className="w-full text-lg font-semibold text-gray-900 bg-transparent focus:outline-none focus:border-[var(--accent)] border-b border-transparent pb-1"
                  />
                </div>
                <div className="flex-1 overflow-auto p-6">
                  {/* Provide a lightweight visual preview of the body with modifications applied */}
                  <iframe 
                      title="Email Preview"
                      srcDoc={htmlBody}
                      className="w-full h-full border-none"
                      sandbox="allow-same-origin allow-popups"
                    />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
