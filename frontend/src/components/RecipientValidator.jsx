import React, { useState, useEffect, useMemo } from 'react';
import { Upload, CheckCircle2, XCircle, Users, Loader2, Search, Filter, Database, FileText, Type, Trash2 } from 'lucide-react';
import api from '../services/api';

export default function RecipientValidator({ onValidated, initialRecipients = [] }) {
  const [activeTab, setActiveTab] = useState('directory'); // directory, manual
  
  // Directory Tab State
  const [recruiters, setRecruiters] = useState([]);
  const [loadingRecruiters, setLoadingRecruiters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Manual Tab State
  const [inputText, setInputText] = useState('');
  
  // Unified Validated Results
  const [isValidating, setIsValidating] = useState(false);
  const [validatedList, setValidatedList] = useState(initialRecipients); // Array of validated objects

  useEffect(() => {
    fetchRecruiters();
  }, []);
  
  // Notify parent whenever validated list changes
  useEffect(() => {
    if (onValidated) {
      onValidated({
        total: validatedList.length,
        valid_count: validatedList.filter(r => r.status === 'valid').length,
        duplicate_count: validatedList.filter(r => r.status === 'duplicate').length,
        invalid_count: validatedList.filter(r => r.status === 'invalid').length,
        disposable_count: validatedList.filter(r => r.status === 'disposable').length,
        recipients: validatedList
      });
    }
  }, [validatedList, onValidated]);

  const fetchRecruiters = async () => {
    try {
      setLoadingRecruiters(true);
      const res = await api.get('/recruiters');
      // If it returns a standard structure with items
      const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
      setRecruiters(items);
    } catch (e) {
      console.error("Failed to load recruiters", e);
    } finally {
      setLoadingRecruiters(false);
    }
  };

  const handleValidateManual = async (textToValidate = inputText) => {
    if (typeof textToValidate !== 'string') {
      textToValidate = inputText;
    }
    if (!textToValidate.trim()) return;

    setIsValidating(true);
    try {
      const emailList = textToValidate.split('\n').map(e => e.trim()).filter(e => e);
      
      const chunkSize = 500;
      let allNewRecipients = [];
      
      for (let i = 0; i < emailList.length; i += chunkSize) {
        const chunk = emailList.slice(i, i + chunkSize);
        const response = await api.post('/campaigns/validate-recipients', { emails: chunk });
        if (response.data && response.data.recipients) {
          allNewRecipients = allNewRecipients.concat(response.data.recipients);
        }
      }
      
      // Merge with existing avoiding duplicates
      setValidatedList(prev => {
        const existingEmails = new Set(prev.map(r => r.email.toLowerCase()));
        const toAdd = allNewRecipients.filter(r => !existingEmails.has(r.email.toLowerCase()));
        return [...prev, ...toAdd];
      });
      
      setInputText('');
    } catch (error) {
      console.error("Validation failed", error);
      const msg = error.response?.data?.detail || error.message || "Failed to validate recipients";
      import('react-hot-toast').then(({ toast }) => toast.error(msg));
    } finally {
      setIsValidating(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const XLSX = await import('xlsx');
        const bstr = evt.target.result;
        const wb = XLSX.read(bstr, { type: 'binary' });
        const wsname = wb.SheetNames[0];
        const ws = wb.Sheets[wsname];
        const data = XLSX.utils.sheet_to_json(ws, { header: 1 });
        
        let emailColIdx = -1;
        for (let row of data.slice(0, 5)) {
          for (let i = 0; i < row.length; i++) {
            if (typeof row[i] === 'string' && row[i].includes('@')) {
              emailColIdx = i;
              break;
            }
          }
          if (emailColIdx !== -1) break;
        }

        let emails = [];
        if (emailColIdx !== -1) {
          emails = data.map(row => row[emailColIdx]).filter(Boolean);
        } else {
          const flat = data.flat();
          emails = flat.filter(v => typeof v === 'string' && v.includes('@'));
        }

        const text = emails.join('\n');
        setInputText(text);
        // Auto validate after file load
        setTimeout(() => handleValidateManual(text), 100);
      } catch (err) {
        console.error("Error parsing file", err);
      }
    };
    reader.readAsBinaryString(file);
    e.target.value = ''; // reset input
  };
  
  const addFromDirectory = (rec) => {
    if (validatedList.some(r => r.email.toLowerCase() === rec.email.toLowerCase())) {
      return; // Already added
    }
    
    setValidatedList(prev => [...prev, {
      email: rec.email,
      name: rec.recruiter_name,
      recruiter_id: rec.recruiter_id,
      company_name: rec.company?.company_name,
      status: 'valid'
    }]);
  };
  
  const addAllFilteredFromDirectory = () => {
    const filtered = recruiters.filter(r => 
      (r.recruiter_name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
       r.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
       r.company?.company_name?.toLowerCase().includes(searchQuery.toLowerCase())) &&
      r.email
    );
    
    const existingEmails = new Set(validatedList.map(r => r.email.toLowerCase()));
    
    const toAdd = filtered
      .filter(r => !existingEmails.has(r.email.toLowerCase()))
      .map(rec => ({
        email: rec.email,
        name: rec.recruiter_name,
        recruiter_id: rec.recruiter_id,
        company_name: rec.company?.company_name,
        status: 'valid'
      }));
      
    setValidatedList(prev => [...prev, ...toAdd]);
  };

  const removeRecipient = (email) => {
    setValidatedList(prev => prev.filter(r => r.email !== email));
  };
  
  const clearAll = () => {
    if (window.confirm("Remove all recipients?")) {
      setValidatedList([]);
    }
  };

  const filteredRecruiters = useMemo(() => recruiters.filter(r => 
    r.recruiter_name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    r.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.company?.company_name?.toLowerCase().includes(searchQuery.toLowerCase())
  ), [recruiters, searchQuery]);

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* SOURCE SELECTION TABS */}
      <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden flex flex-col h-[300px]">
        <div className="flex border-b border-[var(--card-border)] bg-[var(--card-bg)]">
          <button 
            className={`flex-1 py-3 px-4 text-sm font-medium flex justify-center items-center gap-2 transition-colors
              ${activeTab === 'directory' ? 'text-[var(--accent)] border-b-2 border-[var(--accent)] bg-[var(--bg-surface)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'}`}
            onClick={() => setActiveTab('directory')}
          >
            <Database className="w-4 h-4" /> Directory
          </button>
          <button 
            className={`flex-1 py-3 px-4 text-sm font-medium flex justify-center items-center gap-2 transition-colors
              ${activeTab === 'manual' ? 'text-[var(--accent)] border-b-2 border-[var(--accent)] bg-[var(--bg-surface)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'}`}
            onClick={() => setActiveTab('manual')}
          >
            <Type className="w-4 h-4" /> Manual & CSV
          </button>
        </div>
        
        <div className="flex-1 overflow-hidden flex flex-col">
          {activeTab === 'directory' ? (
            <div className="flex flex-col h-full p-4 gap-3">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    type="text"
                    placeholder="Search by name, email, or company..."
                    className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-[var(--accent)]"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <button 
                  onClick={addAllFilteredFromDirectory}
                  className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--card-bg)] whitespace-nowrap"
                >
                  Add All Filtered
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--bg-surface)]">
                {loadingRecruiters ? (
                  <div className="p-8 flex justify-center items-center text-[var(--text-muted)]">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading directory...
                  </div>
                ) : filteredRecruiters.length === 0 ? (
                  <div className="p-8 text-center text-sm text-[var(--text-muted)]">No recruiters found</div>
                ) : (
                  <div className="divide-y divide-[var(--border)]">
                    {filteredRecruiters.map(rec => {
                      const isAdded = validatedList.some(r => r.email.toLowerCase() === rec.email?.toLowerCase());
                      return (
                        <div key={rec.recruiter_id} className="p-2.5 flex items-center justify-between hover:bg-[var(--card-bg)] group">
                          <div>
                            <div className="text-sm font-medium text-[var(--text-primary)]">{rec.recruiter_name}</div>
                            <div className="text-xs text-[var(--text-muted)] flex items-center gap-2">
                              <span>{rec.email}</span>
                              {rec.company && <span>• {rec.company.company_name}</span>}
                            </div>
                          </div>
                          <button
                            onClick={() => !isAdded && addFromDirectory(rec)}
                            disabled={isAdded || !rec.email}
                            className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                              isAdded 
                                ? 'bg-[var(--bg-surface)] border-[var(--border)] text-[var(--text-muted)]' 
                                : 'bg-[var(--accent)]/10 border-[var(--accent)]/30 text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white'
                            }`}
                          >
                            {isAdded ? 'Added' : 'Add'}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col h-full p-4 gap-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-[var(--text-secondary)]">Paste emails or upload list</span>
                <div className="flex gap-2">
                  <label className="btn-secondary text-xs px-3 py-1.5 cursor-pointer flex items-center gap-1.5 bg-[var(--bg-surface)] border border-[var(--border)] rounded-md hover:bg-[var(--card-bg)] transition-colors">
                    <Upload className="w-3.5 h-3.5" /> CSV/Excel
                    <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleFileUpload} />
                  </label>
                  <button 
                    onClick={handleValidateManual} 
                    disabled={isValidating || !inputText.trim()}
                    className="bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white text-xs px-3 py-1.5 rounded-md flex items-center gap-1.5 disabled:opacity-50 transition-colors"
                  >
                    {isValidating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                    Validate & Add
                  </button>
                </div>
              </div>
              
              <textarea
                className="flex-1 w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-3 text-sm font-mono resize-none outline-none focus:border-[var(--accent)]"
                placeholder="Paste email addresses here (one per line)..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />
            </div>
          )}
        </div>
      </div>

      {/* VALIDATED RECIPIENTS TABLE */}
      <div className="flex-1 bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden flex flex-col min-h-[300px]">
        <div className="p-3 border-b border-[var(--card-border)] bg-[var(--card-bg)] flex justify-between items-center">
          <span className="font-medium text-sm flex items-center gap-2 text-[var(--text-primary)]">
            <Users className="w-4 h-4 text-[var(--accent)]" /> Selected Recipients ({validatedList.length})
          </span>
          {validatedList.length > 0 && (
            <button 
              onClick={clearAll}
              className="text-xs text-[var(--danger)] hover:bg-[var(--danger)]/10 px-2 py-1 rounded transition-colors"
            >
              Clear All
            </button>
          )}
        </div>

        <div className="flex-1 overflow-auto">
          {validatedList.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-[var(--text-muted)] space-y-3 p-8 text-center">
              <Users className="w-12 h-12 opacity-20" />
              <div>
                <p className="text-sm font-medium">No recipients added</p>
                <p className="text-xs mt-1 max-w-[250px]">Select recruiters from the directory or upload a list of emails to get started.</p>
              </div>
            </div>
          ) : (
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-[var(--bg-surface)] text-[var(--text-muted)] sticky top-0 border-b border-[var(--border)] shadow-sm">
                <tr>
                  <th className="py-2 px-4 font-medium text-xs">Email</th>
                  <th className="py-2 px-4 font-medium text-xs">Name</th>
                  <th className="py-2 px-4 font-medium text-xs">Company</th>
                  <th className="py-2 px-4 font-medium text-xs">Status</th>
                  <th className="py-2 px-4 font-medium text-xs w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {validatedList.map((rec, i) => (
                  <tr key={i} className="hover:bg-[var(--bg-surface)] group">
                    <td className="py-2 px-4 font-mono text-xs text-[var(--text-primary)] truncate max-w-[200px]" title={rec.email}>{rec.email}</td>
                    <td className="py-2 px-4 text-xs text-[var(--text-secondary)]">{rec.name || '-'}</td>
                    <td className="py-2 px-4 text-xs text-[var(--text-secondary)]">
                      {rec.company_name ? (
                        <span className="bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/20">{rec.company_name}</span>
                      ) : '-'}
                    </td>
                    <td className="py-2 px-4">
                      {rec.status === 'valid' ? (
                        <span className="text-xs text-green-400 flex items-center gap-1"><CheckCircle2 className="w-3 h-3"/> Valid</span>
                      ) : rec.status === 'duplicate' ? (
                        <span className="text-xs text-[var(--text-muted)]">Duplicate</span>
                      ) : (
                        <span className="text-xs text-red-400 flex items-center gap-1" title={rec.reason}><XCircle className="w-3 h-3"/> Invalid</span>
                      )}
                    </td>
                    <td className="py-2 px-4 text-right">
                      <button 
                        onClick={() => removeRecipient(rec.email)}
                        className="text-[var(--text-muted)] hover:text-[var(--danger)] opacity-0 group-hover:opacity-100 transition-all p-1 rounded hover:bg-[var(--danger)]/10"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
