import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export default function CompanyModal({ company, onClose, onSave }) {
  const [formData, setFormData] = useState({
    company_name: '',
    website: '',
    email_pattern: '',
    industry: '',
    location: '',
    notes: '',
    is_active: true
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (company) {
      setFormData({
        company_name: company.company_name || '',
        website: company.website || '',
        email_pattern: company.email_pattern || '',
        industry: company.industry || '',
        location: company.location || '',
        notes: company.notes || '',
        is_active: company.is_active !== false // Default to true if undefined
      });
    }
  }, [company]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.company_name.trim()) {
      setError('Company name is required.');
      return;
    }
    
    setSaving(true);
    setError('');
    try {
      if (company && company.company_id) {
        // Update
        const res = await axios.put(`${API}/companies/${company.company_id}`, formData);
        onSave(res.data);
      } else {
        // Create
        const res = await axios.post(`${API}/companies/`, formData);
        onSave(res.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save company.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', zIndex: 100000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 20
    }}>
      <div className="card" style={{ width: '100%', maxWidth: 500, padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: '#185FA518', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <i className="ti ti-building-community" style={{ fontSize: 18, color: '#185FA5' }} />
            </div>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 600 }}>{company ? 'Edit Company' : 'Add Company'}</h2>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {company ? `Updating details for ${company.company_name}` : 'Create a new company record'}
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: 20, cursor: 'pointer' }}>
            <i className="ti ti-x" />
          </button>
        </div>

        {error && (
          <div style={{ padding: '10px 14px', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', borderRadius: 8, fontSize: 13 }}>
            <i className="ti ti-alert-circle" style={{ marginRight: 6 }} />{error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Company Name *</label>
              <input type="text" name="company_name" value={formData.company_name} onChange={handleChange} placeholder="e.g. Apex Staffing" required />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Website</label>
              <input type="text" name="website" value={formData.website} onChange={handleChange} placeholder="e.g. apex.com" />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Location / State</label>
              <input type="text" name="location" value={formData.location} onChange={handleChange} placeholder="e.g. Austin, TX" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Industry</label>
              <input type="text" name="industry" value={formData.industry} onChange={handleChange} placeholder="e.g. IT Staffing" />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Email Pattern (Optional)</label>
            <input type="text" name="email_pattern" value={formData.email_pattern} onChange={handleChange} placeholder="e.g. {f}{last}@apex.com" />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Notes</label>
            <textarea name="notes" value={formData.notes} onChange={handleChange} placeholder="Add any relevant information about this company..." style={{ resize: 'vertical', minHeight: 60 }} />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-primary)', cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox" name="is_active" checked={formData.is_active} onChange={handleChange} style={{ cursor: 'pointer' }} />
            Active Company
          </label>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
            <button type="button" onClick={onClose} style={{ padding: '10px 18px', background: 'var(--panel-bg)', color: 'var(--text-primary)', border: '1px solid var(--card-border)' }}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving} style={{ padding: '10px 18px', opacity: saving ? 0.7 : 1 }}>
              {saving ? 'Saving...' : 'Save Company'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
