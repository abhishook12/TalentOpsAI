import React, { useState, useRef } from 'react';
import { 
  ClipboardPaste, FileSpreadsheet, Database, 
  Mail, CheckCircle2, AlertCircle, Trash2, X
} from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import PasteRecipientsView from './PasteRecipientsView';
import UploadRecipientsView from './UploadRecipientsView';
import DatabaseRecipientsView from './DatabaseRecipientsView';

export default function DragDropRecipientBuilder({ recipients, onChange, onValidate }) {
  const [activeTab, setActiveTab] = useState('paste');
  const parentRef = useRef(null);
  
  const handleAddRecipients = (newRecipients) => {
    // Filter duplicates against existing recipients
    const existingEmails = new Set(recipients.map(r => r.email));
    const uniqueNew = newRecipients.filter(r => !existingEmails.has(r.email));
    
    if (uniqueNew.length > 0) {
      onChange([...recipients, ...uniqueNew]);
    }
  };

  const removeRecipient = (email) => {
    onChange(recipients.filter(r => r.email !== email));
  };

  const clearAll = () => {
    onChange([]);
  };

  const validCount = recipients.filter(r => r.status === 'valid').length;
  const invalidCount = recipients.filter(r => r.status !== 'valid').length;

  const rowVirtualizer = useVirtualizer({
    count: recipients.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64, // approximate height of each item
    overscan: 5
  });

  return (
    <div className="flex h-[600px] border border-[var(--border)] rounded-xl overflow-hidden bg-[var(--bg-page)] shadow-sm">
      
      {/* Left Pane: Sources */}
      <div className="w-[45%] flex flex-col border-r border-[var(--border)] bg-[var(--bg-surface)]">
        
        {/* Tabs */}
        <div className="flex border-b border-[var(--border)] bg-[var(--bg-page)]">
          {[
            { id: 'paste', icon: ClipboardPaste, label: 'Paste Directly' },
            { id: 'upload', icon: FileSpreadsheet, label: 'CSV / Excel' },
            { id: 'db', icon: Database, label: 'Database' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-3 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab.id 
                  ? 'border-[var(--accent)] text-[var(--accent)] bg-[var(--bg-surface)]' 
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)]'
              }`}
            >
              <tab.icon size={16} /> <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'paste' && <PasteRecipientsView onAddRecipients={handleAddRecipients} />}
          {activeTab === 'upload' && <UploadRecipientsView onAddRecipients={handleAddRecipients} />}
          {activeTab === 'db' && <DatabaseRecipientsView onAddRecipients={handleAddRecipients} />}
        </div>
      </div>

      {/* Right Pane: Selected Recipients */}
      <div className="w-[55%] flex flex-col bg-[var(--bg-surface)]">
        
        {/* Header & Stats */}
        <div className="p-4 border-b border-[var(--border)] bg-[var(--bg-page)]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Mail className="text-[var(--accent)]" size={20} />
              <h3 className="font-semibold text-[var(--text-primary)]">Campaign Recipients</h3>
            </div>
            
            <div className="flex items-center gap-3">
              {recipients.length > 0 && (
                <button 
                  onClick={clearAll}
                  className="text-xs text-[var(--text-muted)] hover:text-red-500 transition-colors"
                >
                  Clear All
                </button>
              )}
              <button 
                onClick={() => onValidate(recipients.map(r => r.email).join(','))}
                disabled={recipients.length === 0}
                className="text-sm font-medium text-[var(--accent)] hover:text-[var(--accent)]/80 disabled:opacity-50 transition-colors"
              >
                Validate All
              </button>
            </div>
          </div>
          
          {/* Live Summary */}
          <div className="flex gap-4 text-xs">
            <div className="flex flex-col">
              <span className="text-[var(--text-muted)]">Total</span>
              <span className="font-semibold text-[var(--text-primary)]">{recipients.length}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[var(--text-muted)]">Valid</span>
              <span className="font-semibold text-green-500">{validCount}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[var(--text-muted)]">Invalid</span>
              <span className="font-semibold text-red-500">{invalidCount}</span>
            </div>
          </div>
        </div>

        {/* Recipient List */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar" ref={parentRef}>
          {recipients.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-[var(--bg-page)] rounded-full flex items-center justify-center mb-4 border-2 border-dashed border-[var(--border)]">
                <Mail size={24} className="text-[var(--text-muted)]" />
              </div>
              <h3 className="text-sm font-medium text-[var(--text-primary)] mb-1">No Recipients Selected</h3>
              <p className="text-xs text-[var(--text-muted)] max-w-[250px]">
                Use the tabs on the left to paste emails, upload a CSV, or select from the database.
              </p>
            </div>
          ) : (
            <div 
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative'
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const recipient = recipients[virtualRow.index];
                return (
                  <div 
                    key={virtualRow.key} 
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`
                    }}
                    className="pb-2" // add gap via padding
                  >
                    <div className="flex items-center justify-between p-3 bg-[var(--bg-page)] border border-[var(--border)] rounded-lg shadow-sm group hover:border-[var(--accent)] transition-colors h-full">
                      <div className="flex items-center gap-3 min-w-0">
                        {recipient.status === 'valid' ? (
                          <CheckCircle2 size={16} className="text-green-500 shrink-0" />
                        ) : (
                          <AlertCircle size={16} className="text-yellow-500 shrink-0" />
                        )}
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                            {recipient.name || recipient.email.split('@')[0]}
                          </p>
                          <p className="text-xs text-[var(--text-muted)] truncate">{recipient.email}</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => removeRecipient(recipient.email)}
                        className="p-1.5 text-[var(--text-muted)] hover:text-red-500 hover:bg-red-500/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
