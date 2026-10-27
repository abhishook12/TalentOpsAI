import React, { useState, useRef, useMemo } from 'react';
import { 
  ClipboardPaste, FileSpreadsheet, Database, 
  Mail, CheckCircle2, AlertCircle, Trash2, X, Search, Filter
} from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import PasteRecipientsView from './PasteRecipientsView';
import UploadRecipientsView from './UploadRecipientsView';
import DatabaseRecipientsView from './DatabaseRecipientsView';

export default function DragDropRecipientBuilder({ recipients, onChange, onValidate }) {
  const [activeTab, setActiveTab] = useState('paste');
  
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all'); // all, valid, invalid
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  
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
    setShowClearConfirm(false);
  };

  const filteredRecipients = useMemo(() => {
    return recipients.filter(r => {
      const matchesSearch = r.email.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            (r.name && r.name.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesFilter = filterStatus === 'all' || 
                            (filterStatus === 'valid' && r.status === 'valid') ||
                            (filterStatus === 'invalid' && r.status !== 'valid');
      return matchesSearch && matchesFilter;
    });
  }, [recipients, searchQuery, filterStatus]);

  const hasRealEmail = (r) => r.email && r.email.trim() && !r.email.includes('@noemail') && !r.email.includes('@unknown');
  const validCount = recipients.filter(r => r.status === 'valid' && hasRealEmail(r)).length;
  const invalidCount = recipients.filter(r => r.status !== 'valid').length;
  const noEmailCount = recipients.filter(r => r.status === 'valid' && !hasRealEmail(r)).length;

  const rowVirtualizer = useVirtualizer({
    count: filteredRecipients.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64, // approximate height of each item
    overscan: 5
  });

  return (
    <div className="flex h-[600px] border border-[var(--card-border)] rounded-md overflow-hidden bg-[var(--main-bg)] shadow-sm">
      
      {/* Left Pane: Sources */}
      <div className="w-[48%] flex flex-col border-r border-[var(--card-border)] bg-[var(--card-bg)] min-w-0 overflow-hidden">
        
        {/* Tabs */}
        <div className="flex border-b border-[var(--card-border)] bg-[var(--panel-bg)] h-10 shrink-0">
          {[
            { id: 'paste', icon: ClipboardPaste, label: 'Paste', enabled: true },
            { id: 'upload', icon: FileSpreadsheet, label: 'CSV', enabled: true },
            { id: 'db', icon: Database, label: 'Database', enabled: true }
          ].map(tab => (
            <button
              key={tab.id}
              disabled={!tab.enabled}
              title={!tab.enabled ? 'Coming soon' : ''}
              onClick={() => tab.enabled && setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-1.5 text-xs font-medium transition-colors border-b-2 relative truncate min-w-0 ${
                activeTab === tab.id 
                  ? 'border-[var(--brand)] text-[var(--text-primary)] font-semibold bg-[var(--card-bg)]' 
                  : !tab.enabled
                    ? 'border-transparent text-[var(--text-muted)] opacity-50 cursor-not-allowed'
                    : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]'
              }`}
            >
              <tab.icon size={15} className="shrink-0" />
              <span className="truncate">{tab.label}</span>
              {!tab.enabled && (
                <span style={{ fontSize: '10px', lineHeight: 1 }} className="uppercase font-semibold bg-[var(--bg-elevated)] border border-[var(--card-border)] px-1 py-[2px] rounded text-[var(--text-muted)] ml-1 shrink-0">Soon</span>
              )}
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
      <div className="w-[52%] flex flex-col bg-[var(--card-bg)] min-w-0 overflow-hidden">
        
        {/* Header & Stats */}
        <div className="p-3.5 border-b border-[var(--card-border)] bg-[var(--panel-bg)]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Mail className="text-[var(--brand)]" size={18} />
              <h3 className="font-semibold text-sm text-[var(--text-primary)]">Campaign Recipients</h3>
            </div>
            
            <div className="flex items-center gap-3">
              {recipients.length > 0 && (
                showClearConfirm ? (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-red-500 font-medium">Are you sure?</span>
                    <button onClick={clearAll} className="text-xs text-white bg-red-600 hover:bg-red-700 px-2 py-0.5 rounded transition-colors font-medium">Yes</button>
                    <button onClick={() => setShowClearConfirm(false)} className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] px-2 py-0.5 transition-colors">No</button>
                  </div>
                ) : (
                  <button 
                    onClick={() => setShowClearConfirm(true)}
                    className="text-xs text-[var(--text-muted)] hover:text-red-400 transition-colors"
                  >
                    Clear All
                  </button>
                )
              )}
              <button 
                onClick={() => onValidate(recipients.map(r => r.email).join(','))}
                disabled={recipients.length === 0}
                className="text-xs font-semibold px-2.5 py-1 rounded bg-[rgba(228, 25, 55, 0.14)] text-[#e41937] border border-[rgba(228, 25, 55, 0.35)] hover:bg-[rgba(228, 25, 55, 0.22)] disabled:opacity-40 transition-colors"
              >
                Validate All
              </button>
            </div>
          </div>
          
          {/* Live Summary */}
          <div className="flex gap-4 text-xs mb-3">
            <div className="flex flex-col">
              <span className="text-[var(--text-muted)]">Total</span>
              <span className="font-semibold text-[var(--text-primary)]">{recipients.length}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[var(--text-muted)]">Will Send</span>
              <span className="font-semibold text-white">{validCount}</span>
            </div>
            {noEmailCount > 0 && (
              <div className="flex flex-col">
                <span className="text-[var(--text-muted)]">No Email</span>
                <span className="font-semibold text-orange-400" title="These contacts have no verified email and will be skipped">{noEmailCount} ⚠</span>
              </div>
            )}
            <div className="flex flex-col">
              <span className="text-[var(--text-muted)]">Invalid</span>
              <span className="font-semibold text-red-500">{invalidCount}</span>
            </div>
          </div>

          {/* Search and Filter */}
          {recipients.length > 0 && (
            <div className="flex items-center gap-2 mt-2">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                <input 
                  type="text"
                  placeholder="Search recipients..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[var(--bg-page)] border border-[var(--border)] rounded-md py-1.5 pl-8 pr-3 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--brand)]"
                />
              </div>
              <div className="relative">
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="bg-[var(--bg-page)] border border-[var(--border)] rounded-md py-1.5 pl-2 pr-6 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--brand)] appearance-none cursor-pointer"
                >
                  <option value="all">All</option>
                  <option value="valid">Valid</option>
                  <option value="invalid">Invalid</option>
                </select>
                <Filter size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none" />
              </div>
            </div>
          )}
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
                const recipient = filteredRecipients[virtualRow.index];
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
                    <div className="flex items-center justify-between p-3 bg-[var(--bg-page)] border border-[var(--border)] rounded-lg shadow-sm group hover:border-[var(--brand)] transition-colors h-full">
                      <div className="flex items-center gap-3 min-w-0">
                        {recipient.status === 'valid' && hasRealEmail(recipient) ? (
                          <CheckCircle2 size={16} className="text-white shrink-0" />
                        ) : recipient.status === 'valid' && !hasRealEmail(recipient) ? (
                          <AlertCircle size={16} className="text-orange-400 shrink-0" title="No verified email — will be skipped" />
                        ) : (
                          <AlertCircle size={16} className="text-[#e41937] shrink-0" />
                        )}
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                            {recipient.name || (recipient.email ? recipient.email.split('@')[0] : 'Unknown')}
                          </p>
                          {recipient.email && hasRealEmail(recipient) ? (
                            <p className="text-xs text-[var(--text-muted)] truncate">{recipient.email}</p>
                          ) : (
                            <p className="text-xs text-orange-400 truncate">⚠ No email — will be skipped</p>
                          )}
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
