import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, Building, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';

export default function DatabaseRecipientsView({ onAddRecipients }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [preset, setPreset] = useState('all');
  const [page, setPage] = useState(1);
  const scrollRef = useRef(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1); // reset to page 1 on new search
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['recruiters_db', debouncedSearch, preset, page],
    keepPreviousData: true,
    staleTime: 60_000,
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '50', page: page.toString() });
      if (debouncedSearch) params.append('search', debouncedSearch);
      
      if (preset === 'execs') {
        params.append('seniority_level', 'Executive');
      } else if (preset === 'tech_sf') {
        params.append('metro_hub', 'SF_BAY_AREA');
        params.append('specialization_sector', 'Technical');
      } else if (preset === 'enterprise') {
        params.append('company_scale', 'Enterprise');
      } else if (preset === 'pacific') {
        params.append('timezone_code', 'PT');
      }
      
      const res = await api.get(`/recruiters?${params.toString()}`);
      return res.data || { items: [], total: 0, pages: 1 };
    }
  });

  const recruiters = data?.results || data?.items || [];
  const totalPages = data?.total_pages || data?.pages || 1;

  const handleToggleSelect = (recruiter) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(recruiter.recruiter_id)) {
      newSet.delete(recruiter.recruiter_id);
    } else {
      newSet.add(recruiter.recruiter_id);
    }
    setSelectedIds(newSet);
  };

  const handleSelectAll = () => {
    if (selectedIds.size === recruiters.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(recruiters.map(r => r.recruiter_id)));
    }
  };

  const handleAdd = () => {
    if (selectedIds.size === 0) return;
    const selectedRecruiters = recruiters
      .filter(r => selectedIds.has(r.recruiter_id))
      .map(r => ({
        id: `db_${r.recruiter_id}`,
        email: r.email?.toLowerCase(),
        name: r.recruiter_name,
        company: r.company?.name || r.company_name || '',
        role: r.specialization || '',
        location: r.location || '',
        logo_url: r.logo_url || null,
        seniority_level: r.seniority_level || 'Specialist',
        timezone: r.timezone || 'America/New_York',
        timezone_code: r.timezone_code || 'ET',
        is_deliverable: r.is_deliverable !== false,
        trust_score: r.trust_score || 95,
        source: 'db',
        status: r.is_deliverable === false ? 'invalid_mx' : 'valid'
      }))
      .filter(r => r.email && r.email.includes('@')); // ensure valid email

    if (selectedRecruiters.length > 0) {
      onAddRecipients(selectedRecruiters);
      setSelectedIds(new Set());
    }
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-surface)]">
      {/* Search Bar & Smart Presets */}
      <div className="p-3 border-b border-[var(--border)] flex flex-col gap-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" size={16} />
          <input 
            type="text"
            placeholder="Search recruiters by name, email, title, company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[var(--bg-page)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--brand)] transition-colors"
          />
        </div>

        {/* 1-Click Smart Audience Presets */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <span className="text-[11px] text-[var(--text-muted)] font-medium mr-1 flex items-center gap-1">
            ⚡ Presets:
          </span>
          <button
            onClick={() => { setPreset('all'); setPage(1); }}
            className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap text-[11px] font-medium ${
              preset === 'all' ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-page)] text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border)]'
            }`}
          >
            All Database
          </button>
          <button
            onClick={() => { setPreset('execs'); setPage(1); }}
            className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap text-[11px] font-medium ${
              preset === 'execs' ? 'bg-purple-600 text-white' : 'bg-[var(--bg-page)] text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border)]'
            }`}
          >
            👑 Leadership & Heads
          </button>
          <button
            onClick={() => { setPreset('tech_sf'); setPage(1); }}
            className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap text-[11px] font-medium ${
              preset === 'tech_sf' ? 'bg-indigo-600 text-white' : 'bg-[var(--bg-page)] text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border)]'
            }`}
          >
            💻 SF Bay Tech Recruiters
          </button>
          <button
            onClick={() => { setPreset('enterprise'); setPage(1); }}
            className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap text-[11px] font-medium ${
              preset === 'enterprise' ? 'bg-emerald-600 text-white' : 'bg-[var(--bg-page)] text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border)]'
            }`}
          >
            🏢 Enterprise Scale (500+)
          </button>
          <button
            onClick={() => { setPreset('pacific'); setPage(1); }}
            className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap text-[11px] font-medium ${
              preset === 'pacific' ? 'bg-blue-600 text-white' : 'bg-[var(--bg-page)] text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border)]'
            }`}
          >
            🌊 Pacific Time (PT)
          </button>
        </div>
      </div>

      {/* Select All & Add Actions */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-page)]/50">
        <label className="flex items-center gap-2 text-xs font-medium text-[var(--text-primary)] cursor-pointer">
          <input 
            type="checkbox" 
            checked={recruiters.length > 0 && selectedIds.size === recruiters.length}
            onChange={handleSelectAll}
            className="rounded border-[var(--border)] text-[var(--brand)] focus:ring-[var(--brand)]"
          />
          <span>Select all ({recruiters.length})</span>
        </label>
        
        <button
          onClick={handleAdd}
          disabled={selectedIds.size === 0}
          className="px-3 py-1.5 bg-[var(--brand)] hover:bg-[var(--brand-hover)] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded-md transition-colors"
        >
          Add {selectedIds.size} Selected
        </button>
      </div>

      {/* Recruiter List */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 text-[var(--text-muted)] gap-2">
            <div className="w-6 h-6 border-2 border-[var(--brand)] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs">Loading database...</p>
          </div>
        ) : recruiters.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-[var(--text-muted)]">
            <Users size={32} className="mb-2 opacity-50" />
            <p className="text-sm">No recruiters found</p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            {recruiters.map(r => (
              <div 
                key={r.recruiter_id}
                onClick={() => handleToggleSelect(r)}
                className={`p-3 flex items-start gap-3 cursor-pointer transition-colors ${
                  selectedIds.has(r.recruiter_id) ? 'bg-[var(--brand)]/5' : 'hover:bg-[var(--bg-page)]'
                }`}
              >
                <input 
                  type="checkbox" 
                  checked={selectedIds.has(r.recruiter_id)}
                  onChange={() => {}} // handled by parent div click
                  className="mt-1 rounded border-[var(--border)] text-[var(--brand)] focus:ring-[var(--brand)]"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 truncate">
                      <p className="text-sm font-semibold text-[var(--text-primary)] truncate">{r.recruiter_name}</p>
                      {r.seniority_level && r.seniority_level !== 'Specialist' && (
                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                          r.seniority_level === 'Executive' ? 'bg-purple-500/10 border-purple-500/30 text-purple-400' :
                          r.seniority_level === 'Lead' ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400' :
                          r.seniority_level === 'Senior' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                          'bg-amber-500/10 border-amber-500/30 text-amber-400'
                        }`}>
                          {r.seniority_level}
                        </span>
                      )}
                    </div>
                    {r.specialization && (
                      <span className="text-[10px] bg-[var(--bg-page)] border border-[var(--border)] text-[var(--text-muted)] px-2 py-0.5 rounded-full truncate max-w-[120px]">
                        {r.specialization}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs text-[var(--text-muted)] truncate">{r.email}</p>
                    {r.is_deliverable !== false && (
                      <span className="text-[9px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold px-1.5 py-0.2 rounded">
                        MX Verified
                      </span>
                    )}
                    {r.timezone_code && (
                      <span className="text-[9px] bg-blue-500/10 border border-blue-500/20 text-blue-400 font-medium px-1 py-0.2 rounded">
                        {r.timezone_code}
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-3 mt-1.5 text-[11px] text-[var(--text-muted)]">
                    {(r.company_name || r.company?.name) && (
                      <span className="flex items-center gap-1 truncate">
                        <Building size={10} /> {r.company_name || r.company?.name}
                      </span>
                    )}
                    {r.location && (
                      <span className="flex items-center gap-1 truncate">
                        <MapPin size={10} /> {r.location}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-3 bg-[var(--bg-page)]/50">
                <button 
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 text-xs font-medium text-[var(--text-primary)] bg-[var(--bg-surface)] border border-[var(--border)] rounded hover:bg-[var(--bg-page)] disabled:opacity-50 transition-colors"
                >
                  Previous
                </button>
                <span className="text-xs text-[var(--text-muted)]">Page {page} of {totalPages}</span>
                <button 
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 text-xs font-medium text-[var(--text-primary)] bg-[var(--bg-surface)] border border-[var(--border)] rounded hover:bg-[var(--bg-page)] disabled:opacity-50 transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
