import React, { useState, useRef } from 'react';
import Papa from 'papaparse';
import { Upload, FileSpreadsheet, ArrowRight, X } from 'lucide-react';

export default function UploadRecipientsView({ onAddRecipients }) {
  const [file, setFile] = useState(null);
  const [data, setData] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({ email: '', name: '', company: '', title: '' });
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) processFile(selectedFile);
  };

  const processFile = (selectedFile) => {
    if (selectedFile.type !== 'text/csv' && !selectedFile.name.endsWith('.csv')) {
      alert("Please upload a CSV file.");
      return;
    }
    setFile(selectedFile);
    parseFile(selectedFile);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) processFile(droppedFile);
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
      if (email && /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(email) && !seenEmails.has(email)) {
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
                className="w-full bg-[var(--bg-page)] border border-[var(--border)] rounded-lg p-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--brand)]"
              >
                <option value="">-- Ignore --</option>
                {headers.map(h => <option key={h} value={h}>{h}</option>)}
              </select>
            </div>
          ))}

          <div className="mt-6">
            <p className="text-xs font-medium text-[var(--text-muted)] mb-2">Preview (Up to 50 rows)</p>
            <div className="border border-[var(--border)] rounded-lg overflow-hidden text-xs max-h-48 overflow-y-auto">
              <table className="w-full text-left">
                <thead className="bg-[var(--bg-page)] border-b border-[var(--border)] sticky top-0 z-10">
                  <tr>
                    <th className="p-2 font-medium text-[var(--text-primary)]">Email</th>
                    <th className="p-2 font-medium text-[var(--text-primary)]">Name</th>
                    <th className="p-2 font-medium text-[var(--text-primary)]">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] bg-[var(--bg-surface)]">
                  {data.slice(0, 50).map((row, i) => {
                    const rawEmail = mapping.email ? row[mapping.email] : '';
                    const email = rawEmail?.trim().toLowerCase();
                    const isValid = mapping.email && email && /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(email);
                    
                    return (
                      <tr key={i} className={!isValid && mapping.email ? "bg-red-500/10" : ""}>
                        <td className={`p-2 ${!isValid && mapping.email ? "text-red-400 font-semibold" : "text-[var(--text-muted)]"}`}>{rawEmail || '-'}</td>
                        <td className="p-2 text-[var(--text-muted)]">{mapping.name ? row[mapping.name] : '-'}</td>
                        <td className="p-2">
                          {!mapping.email ? (
                            <span className="text-[var(--text-muted)]">Pending map</span>
                          ) : isValid ? (
                            <span className="text-green-500">Valid</span>
                          ) : (
                            <span className="text-red-500 font-medium">Invalid Email</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[var(--border)] flex justify-between items-center">
          <div className="text-xs text-[var(--text-muted)]">
            {mapping.email && (
              <>
                <span className="text-green-500 font-medium">{data.filter(r => /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(r[mapping.email]?.trim().toLowerCase())).length} Valid</span>
                {' • '}
                <span className="text-red-500 font-medium">{data.filter(r => !/^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(r[mapping.email]?.trim().toLowerCase())).length} Invalid</span>
              </>
            )}
          </div>
          <button 
            onClick={handleImport}
            disabled={!mapping.email}
            className="px-4 py-2 bg-[var(--brand)] text-[var(--text-inverse)] text-sm font-medium rounded-lg shadow flex items-center gap-2 hover:bg-[var(--brand)]/90 disabled:opacity-50 transition-colors"
          >
            Import Valid Rows <ArrowRight size={16} />
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
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`w-full h-48 border-2 border-dashed rounded-xl flex flex-col items-center justify-center cursor-pointer transition-colors group ${
          isDragging 
            ? 'border-[var(--brand)] bg-[var(--brand)]/10 scale-[1.02]' 
            : 'border-[var(--border)] hover:border-[var(--brand)] hover:bg-[var(--brand)]/5'
        }`}
      >
        <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-transform ${isDragging ? 'bg-[var(--brand)]/20 scale-110' : 'bg-[var(--bg-page)] border border-[var(--border)] group-hover:scale-110'}`}>
          <FileSpreadsheet size={24} className={isDragging ? 'text-[var(--brand)]' : 'text-[var(--text-muted)] group-hover:text-[var(--brand)]'} />
        </div>
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
          {isDragging ? 'Drop file here' : 'Upload CSV'}
        </h3>
        <p className="text-xs text-[var(--text-muted)] max-w-[200px] text-center">
          {isDragging 
            ? 'Release to upload' 
            : 'Click to browse or drag & drop your spreadsheet here. We\'ll help you map the columns.'}
        </p>
      </div>
    </div>
  );
}
