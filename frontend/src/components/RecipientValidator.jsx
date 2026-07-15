import React, { useState } from 'react';
import { Upload, CheckCircle2, XCircle, AlertTriangle, Users, Loader2 } from 'lucide-react';
import api from '../services/api';
import * as XLSX from 'xlsx';

export default function RecipientValidator({ onValidated }) {
  const [inputText, setInputText] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [result, setResult] = useState(null);

  const handleValidate = async (emails = null) => {
    const textToValidate = emails || inputText;
    if (!textToValidate.trim()) return;

    setIsValidating(true);
    try {
      const emailList = textToValidate.split('\n').map(e => e.trim()).filter(e => e);
      const response = await api.post('/campaigns/validate-recipients', { emails: emailList });
      setResult(response.data);
      if (onValidated) {
        onValidated(response.data);
      }
    } catch (error) {
      console.error("Validation failed", error);
    } finally {
      setIsValidating(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const bstr = evt.target.result;
        const wb = XLSX.read(bstr, { type: 'binary' });
        const wsname = wb.SheetNames[0];
        const ws = wb.Sheets[wsname];
        const data = XLSX.utils.sheet_to_json(ws, { header: 1 });
        
        // Find email column (simple heuristic: look for '@' in first few rows)
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
          // Flatten and find any email
          const flat = data.flat();
          emails = flat.filter(v => typeof v === 'string' && v.includes('@'));
        }

        const text = emails.join('\n');
        setInputText(text);
        handleValidate(text);
      } catch (err) {
        console.error("Error parsing file", err);
      }
    };
    reader.readAsBinaryString(file);
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex-1 flex flex-col bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden">
        <div className="p-3 border-b border-[var(--card-border)] bg-[var(--card-bg)] flex justify-between items-center">
          <span className="font-medium text-sm flex items-center gap-2">
            <Users className="w-4 h-4 text-[var(--accent)]" /> Target Recipients
          </span>
          <div className="flex gap-2">
            <label className="btn-secondary text-xs px-2 py-1 cursor-pointer flex items-center gap-1">
              <Upload className="w-3 h-3" /> CSV/Excel
              <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleFileUpload} />
            </label>
            <button 
              onClick={() => handleValidate()} 
              disabled={isValidating || !inputText.trim()}
              className="btn-primary text-xs px-3 py-1 flex items-center gap-1"
            >
              {isValidating ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
              Validate
            </button>
          </div>
        </div>
        
        <textarea
          className="flex-1 w-full bg-transparent p-4 text-sm font-mono resize-none outline-none focus:ring-1 focus:ring-[var(--accent)]/50"
          placeholder="Paste email addresses here (one per line)..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />
      </div>

      {result && (
        <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl p-4">
          <div className="text-sm font-medium mb-3">Validation Results</div>
          
          <div className="grid grid-cols-4 gap-2 mb-4">
            <div className="bg-[var(--card-bg)] rounded-lg p-2 text-center border border-[var(--card-border)]">
              <div className="text-xl font-semibold">{result.total}</div>
              <div className="text-xs text-[var(--text-muted)]">Total</div>
            </div>
            <div className="bg-green-500/10 rounded-lg p-2 text-center border border-green-500/20">
              <div className="text-xl font-semibold text-green-400">{result.valid_count}</div>
              <div className="text-xs text-green-400/80 flex justify-center items-center gap-1"><CheckCircle2 className="w-3 h-3"/> Valid</div>
            </div>
            <div className="bg-[var(--card-bg)] rounded-lg p-2 text-center border border-[var(--card-border)]">
              <div className="text-xl font-semibold text-[var(--text-muted)]">{result.duplicate_count}</div>
              <div className="text-xs text-[var(--text-muted)]">Dupes</div>
            </div>
            <div className="bg-red-500/10 rounded-lg p-2 text-center border border-red-500/20">
              <div className="text-xl font-semibold text-red-400">{result.invalid_count + result.disposable_count}</div>
              <div className="text-xs text-red-400/80 flex justify-center items-center gap-1"><XCircle className="w-3 h-3"/> Invalid</div>
            </div>
          </div>

          <div className="max-h-48 overflow-y-auto space-y-1">
            {result.recipients.map((rec, i) => (
              <div key={i} className="text-xs flex items-center justify-between p-1.5 hover:bg-[var(--card-bg)] rounded">
                <span className="font-mono truncate max-w-[150px]" title={rec.email}>{rec.email}</span>
                {rec.status === 'valid' ? (
                  rec.company_name ? (
                    <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded truncate max-w-[100px]">
                      {rec.company_name}
                    </span>
                  ) : (
                    <span className="text-[10px] text-green-400 flex items-center"><CheckCircle2 className="w-3 h-3 mr-1"/> Valid</span>
                  )
                ) : rec.status === 'duplicate' ? (
                  <span className="text-[10px] text-[var(--text-muted)]">Duplicate</span>
                ) : (
                  <span className="text-[10px] text-red-400 flex items-center" title={rec.reason}><XCircle className="w-3 h-3 mr-1"/> {rec.status}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
