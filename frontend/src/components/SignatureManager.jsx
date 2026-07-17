import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Check, X, Star } from 'lucide-react';
import api from '../services/api';
import RichTextComposer from './RichTextComposer';

export default function SignatureManager({ onSelectSignature, selectedSignatureId }) {
  const [signatures, setSignatures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingSig, setEditingSig] = useState(null);
  
  // Form state
  const [name, setName] = useState('');
  const [htmlContent, setHtmlContent] = useState('<p>Best regards,<br/>Your Name</p>');
  const [isDefault, setIsDefault] = useState(false);

  const fetchSignatures = async () => {
    try {
      setLoading(true);
      const res = await api.get('/campaigns/signatures/list');
      setSignatures(res.data);
      
      // Auto-select default signature if none selected
      if (!selectedSignatureId && res.data.length > 0) {
        const defaultSig = res.data.find(s => s.is_default) || res.data[0];
        if (onSelectSignature) onSelectSignature(defaultSig.signature_id);
      }
    } catch (e) {
      console.error("Failed to load signatures:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignatures();
  }, []);

  const handleSave = async () => {
    try {
      if (!name.trim()) return;
      
      const payload = {
        name,
        html_content: htmlContent,
        is_default: isDefault
      };
      
      if (editingSig) {
        await api.put(`/campaigns/signatures/${editingSig.signature_id}`, payload);
      } else {
        await api.post('/campaigns/signatures/create', payload);
      }
      
      setEditingSig(null);
      setName('');
      setHtmlContent('<p>Best regards,<br/>Your Name</p>');
      setIsDefault(false);
      fetchSignatures();
    } catch (e) {
      console.error("Failed to save signature:", e);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this signature?")) return;
    
    try {
      await api.delete(`/campaigns/signatures/${id}`);
      if (selectedSignatureId === id && onSelectSignature) {
        onSelectSignature(null);
      }
      fetchSignatures();
    } catch (e) {
      console.error("Failed to delete signature:", e);
    }
  };

  const startEdit = (sig) => {
    setEditingSig(sig);
    setName(sig.name);
    setHtmlContent(sig.html_content);
    setIsDefault(sig.is_default);
  };

  const cancelEdit = () => {
    setEditingSig(null);
    setName('');
    setHtmlContent('<p>Best regards,<br/>Your Name</p>');
    setIsDefault(false);
  };

  if (editingSig !== null || signatures.length === 0) {
    return (
      <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '12px', padding: '16px' }}>
        <h3 style={{ margin: '0 0 16px', color: 'var(--text-primary)', fontSize: '16px', fontWeight: 600 }}>
          {editingSig ? 'Edit Signature' : 'Create Signature'}
        </h3>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>Signature Name</label>
            <input 
              type="text" 
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Formal, Casual, Default"
              style={{
                width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border)',
                background: 'var(--bg-surface)', color: 'var(--text-primary)', fontSize: '14px'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>Content</label>
            <div style={{ height: '250px' }}>
              <RichTextComposer 
                content={htmlContent}
                onChange={setHtmlContent}
                placeholder="Write your signature..."
              />
            </div>
          </div>
          
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '14px', color: 'var(--text-primary)' }}>
            <input 
              type="checkbox" 
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              style={{ width: '16px', height: '16px', accentColor: 'var(--accent)' }}
            />
            Set as default signature
          </label>
          
          <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
            <button 
              onClick={handleSave}
              disabled={!name.trim() || !htmlContent.trim()}
              style={{
                background: 'var(--accent)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px',
                fontWeight: 500, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
              }}
            >
              <Check size={16} /> Save Signature
            </button>
            
            {signatures.length > 0 && (
              <button 
                onClick={cancelEdit}
                style={{
                  background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border)', 
                  padding: '8px 16px', borderRadius: '6px', fontWeight: 500, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '6px'
                }}
              >
                <X size={16} /> Cancel
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '12px', padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '16px', fontWeight: 600 }}>Your Signatures</h3>
        <button 
          onClick={() => setEditingSig(false)} // false means creating new
          style={{
            background: 'var(--accent)', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px',
            fontSize: '13px', fontWeight: 500, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
          }}
        >
          <Plus size={14} /> New
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>Loading signatures...</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {signatures.map(sig => (
            <div 
              key={sig.signature_id}
              onClick={() => onSelectSignature && onSelectSignature(sig.signature_id)}
              style={{
                border: `1px solid ${selectedSignatureId === sig.signature_id ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: '8px',
                padding: '12px',
                cursor: onSelectSignature ? 'pointer' : 'default',
                background: selectedSignatureId === sig.signature_id ? 'rgba(14, 165, 233, 0.05)' : 'var(--bg-surface)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: '14px' }}>{sig.name}</span>
                  {sig.is_default && (
                    <span style={{ 
                      background: 'rgba(234, 179, 8, 0.1)', color: 'var(--accent)', padding: '2px 6px', 
                      borderRadius: '4px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 500
                    }}>
                      <Star size={10} /> Default
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button 
                    onClick={(e) => { e.stopPropagation(); startEdit(sig); }}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px' }}
                    title="Edit"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDelete(sig.signature_id); }}
                    style={{ background: 'transparent', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: '4px' }}
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              <div 
                style={{ fontSize: '12px', color: 'var(--text-secondary)', opacity: 0.8, maxHeight: '60px', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}
                dangerouslySetInnerHTML={{ __html: sig.html_content }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
