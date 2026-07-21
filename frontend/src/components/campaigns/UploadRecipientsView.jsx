import React, { useState, useRef } from 'react';
import Papa from 'papaparse';
import { Upload, FileSpreadsheet, ArrowRight, X } from 'lucide-react';

export default function UploadRecipientsView({ onAddRecipients }) {
  const [file, setFile] = useState(null);
  const [data, setData] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({ email: '', name: '', company: '', title: '' });
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      parseFile(selectedFile);
    }
  };

  const parseFile = (file) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (results.data && results.data.length > 0) {
          const detectedHeaders = Object.keys(results.data[0]);
          setHeaders(detectedHeaders);
          setData(results.data);
          
          // Auto-detect mapping
          const newMapping = { email: '', name: '', company: '', title: '' };
          detectedHeaders.forEach(h => {
            const lower = h.toLowerCase();
            if (!newMapping.email && (lower.includes('email') || lower.includes('e-mail'))) newMapping.email = h;
            if (!newMapping.name && (lower.includes('name') || lower.includes('first') || lower.includes('contact'))) newMapping.name = h;
            if (!newMapping.company && lower.includes('company')) newMapping.company = h;
            if (!newMapping.title && (lower.includes('title') || lower.includes('role'))) newMapping.title = h;
          });
          setMapping(newMapping);
        }
      }
    });
  };

  const handleImport = () => {
    if (!mapping.email) return;

    const parsedRecipients = [];
    const seenEmails = new Set();
    let validCount = 0;

    data.forEach(row => {
      const email = row[mapping.email]?.trim().toLowerCase();
      if (email && email.includes('@') && !seenEmails.has(email)) {
        seenEmails.add(email);
        parsedRecipients.push({
          id: `u_${Date.now()}_${validCount}`,
          email,
          name: mapping.name ? row[mapping.name] : email.split('@')[0],
          company: mapping.company ? row[mapping.company] : '',
          role: mapping.title ? row[mapping.title] : '',
          source: 'upload',
          status: 'valid'
        });
        validCount++;
      }
    });

    onAddRecipients(parsedRecipients);
    reset();
  };

  const reset = () => {
    setFile(null);
    setData([]);
    setHeaders([]);
    setMapping({ email: '', name: '', company: '', title: '' });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  if (file && headers.length > 0) {
    return (
      <div className="flex flex-col h-full bg-[var(--bg-surface)] p-4">
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--border)]">
          <div>
            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Map Columns</h3>
            <p className="text-xs text-[var(--text-muted)]">Select which columns correspond to recipient data.</p>
          </div>
          <button onClick={reset} className="p-1 text-[var(--text-muted)] hover:text-red-500 hover:bg-red-500/10 rounded">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-4 flex-1 overflow-y-auto custom-scrollbar pr-2">
          {['email', 'name', 'company', 'title'].map((field) => (
            <div key={field} className="flex flex-col gap-1">
              <label className="text-xs font-medium text-[var(--text-primary)] capitalize">
                {field} {field === 'email' && <span className="text-red-500">*</span>}
              </label>
              <select
                value={mapping[field]}
                onChange={(e) => setMapping({ ...mapping, [field]: e.target.value })}
                className="w-full bg-[var(--bg-page)] border border-[var(--border)] rounded-lg p-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="">-- Ignore --</option>
                {headers.map(h => <option key={h} value={h}>{h}</option>)}
              </select>
            </div>
          ))}

          <div className="mt-6">
            <p className="text-xs font-medium text-[var(--text-muted)] mb-2">Preview (First 3 rows)</p>
            <div className="border border-[var(--border)] rounded-lg overflow-hidden text-xs">
              <table className="w-full text-left">
                <thead className="bg-[var(--bg-page)] border-b border-[var(--border)]">
                  <tr>
                    <th className="p-2 font-medium text-[var(--text-primary)]">Email</th>
                    <th className="p-2 font-medium text-[var(--text-primary)]">Name</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] bg-[var(--bg-surface)]">
                  {data.slice(0, 3).map((row, i) => (
                    <tr key={i}>
                      <td className="p-2 text-[var(--text-muted)]">{mapping.email ? row[mapping.email] : '-'}</td>
                      <td className="p-2 text-[var(--text-muted)]">{mapping.name ? row[mapping.name] : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[var(--border)] flex justify-end">
          <button 
            onClick={handleImport}
            disabled={!mapping.email}
            className="px-4 py-2 bg-[var(--accent)] text-white text-sm font-medium rounded-lg shadow flex items-center gap-2 hover:bg-[var(--accent)]/90 disabled:opacity-50 transition-colors"
          >
            Import {data.length} Rows <ArrowRight size={16} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[var(--bg-surface)] p-4 items-center justify-center">
      <input 
        type="file" 
        accept=".csv" 
        className="hidden" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
      />
      
      <div 
        onClick={() => fileInputRef.current?.click()}
        className="w-full h-48 border-2 border-dashed border-[var(--border)] rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-[var(--accent)] hover:bg-[var(--accent)]/5 transition-colors group"
      >
        <div className="w-12 h-12 rounded-full bg-[var(--bg-page)] border border-[var(--border)] flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
          <FileSpreadsheet size={24} className="text-[var(--text-muted)] group-hover:text-[var(--accent)]" />
        </div>
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Upload CSV</h3>
        <p className="text-xs text-[var(--text-muted)] max-w-[200px] text-center">
          Click to browse or drag & drop your spreadsheet here. We'll help you map the columns.
        </p>
      </div>
    </div>
  );
}
