import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, Building, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';

export default function DatabaseRecipientsView({ onAddRecipients }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
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
    queryKey: ['recruiters_db', debouncedSearch, page],
    keepPreviousData: true,
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '50', page: page.toString() });
      if (debouncedSearch) params.append('search', debouncedSearch);
      const res = await api.get(`/recruiters?${params.toString()}`);
      return res.data || { items: [], total: 0, pages: 1 };
    }
  });

  const recruiters = data?.items || [];
  const totalPages = data?.pages || 1;

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
        company: r.company?.name || '',
        role: r.specialization || '',
        location: r.location || '',
        source: 'db',
        status: 'valid'
      }))
      .filter(r => r.email && r.email.includes('@')); // ensure valid email

    if (selectedRecruiters.length > 0) {
      onAddRecipients(selectedRecruiters);
      setSelectedIds(new Set());
    }
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-surface)]">
      {/* Search Bar */}
      <div className="p-3 border-b border-[var(--border)]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" size={16} />
          <input 
            type="text"
            placeholder="Search recruiters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[var(--bg-page)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
          />
        </div>
      </div>

      {/* Select All & Add Actions */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-page)]/50">
        <label className="flex items-center gap-2 text-xs font-medium text-[var(--text-primary)] cursor-pointer">
          <input 
            type="checkbox" 
            checked={recruiters.length > 0 && selectedIds.size === recruiters.length}
            onChange={handleSelectAll}
            className="rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)]"
          />
          Select All
        </label>
        
        <button
          onClick={handleAdd}
          disabled={selectedIds.size === 0}
          className="text-xs font-medium px-3 py-1 bg-[var(--accent)] text-white rounded hover:bg-[var(--accent)]/90 disabled:opacity-50 transition-colors"
        >
          Add {selectedIds.size} Selected
        </button>
      </div>

      {/* Recruiter List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar" ref={scrollRef}>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-[var(--text-muted)]">
            <div className="w-6 h-6 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin"></div>
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
                  selectedIds.has(r.recruiter_id) ? 'bg-[var(--accent)]/5' : 'hover:bg-[var(--bg-page)]'
                }`}
              >
                <input 
                  type="checkbox"
                  checked={selectedIds.has(r.recruiter_id)}
                  onChange={() => {}} // handled by parent div click
                  className="mt-1 rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-[var(--text-primary)] truncate">{r.recruiter_name}</p>
                    {r.specialization && (
                      <span className="text-[10px] bg-[var(--bg-page)] border border-[var(--border)] text-[var(--text-muted)] px-2 py-0.5 rounded-full truncate max-w-[80px]">
                        {r.specialization}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[var(--text-muted)] truncate mt-0.5">{r.email}</p>
                  
                  <div className="flex items-center gap-3 mt-1.5 text-[11px] text-[var(--text-muted)]">
                    {r.company?.name && (
                      <span className="flex items-center gap-1 truncate">
                        <Building size={10} /> {r.company.name}
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
