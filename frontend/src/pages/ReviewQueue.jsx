import { useState, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'
import {
  Badge,
  EmptyState,
  GhostButton,
  PrimaryButton,
  SectionHeader,
  ShellCard
} from '../components/CommandCenter'

export default function ReviewQueue() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})
  
  // Fetch recruiters flagged for review
  const { data, isLoading, error } = useQuery({
    queryKey: ['review-queue'],
    queryFn: async () => {
      const res = await api.get('/recruiters', {
        params: { needs_review: true, limit: 100 }
      })
      return res.data
    },
    refetchOnWindowFocus: false
  })

  // Mutations
  const updateRecruiter = useMutation({
    mutationFn: async ({ id, updates }) => {
      await api.put(`/recruiters/${id}`, updates)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-kpis'] })
    }
  })

  const recruiters = data?.items || []

  const handleApprove = useCallback((id, currentData) => {
    // Approve resets needs_review to false
    updateRecruiter.mutate({
      id,
      updates: { ...currentData, needs_review: false, completeness_score: Math.max(currentData.completeness_score || 0, 80) }
    })
  }, [updateRecruiter])

  const handleDeactivate = useCallback((id, currentData) => {
    // Deactivate hides them completely
    updateRecruiter.mutate({
      id,
      updates: { ...currentData, is_active: false, needs_review: false }
    })
  }, [updateRecruiter])

  const startEdit = useCallback((r) => {
    setEditingId(r.recruiter_id)
    setEditForm({
      recruiter_name: r.recruiter_name || '',
      email: r.email || '',
      phone: r.phone || ''
    })
  }, [])

  const saveEdit = useCallback((r) => {
    updateRecruiter.mutate({
      id: r.recruiter_id,
      updates: { ...r, ...editForm, needs_review: false }
    })
    setEditingId(null)
  }, [editForm, updateRecruiter])

  const cancelEdit = useCallback(() => {
    setEditingId(null)
  }, [])

  if (isLoading) {
    return (
      <div className="page-enter" style={{ display: 'grid', placeItems: 'center', minHeight: '60vh' }}>
        <i className="ti ti-loader animate-spin" style={{ fontSize: 24, color: 'var(--accent)' }} />
      </div>
    )
  }

  if (error) {
    return (
      <ShellCard style={{ padding: 18, borderColor: 'var(--danger)', background: 'rgba(239, 68, 68, 0.05)' }}>
        <div style={{ color: 'var(--danger)', fontWeight: 700 }}>Failed to load review queue.</div>
      </ShellCard>
    )
  }

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <SectionHeader
        eyebrow="Data Hygiene"
        title="Review Queue"
        subtitle="Rapidly audit, fix, and approve records flagged by the system."
        action={
          <Badge tone={recruiters.length > 0 ? "warning" : "success"}>
            {recruiters.length} Pending
          </Badge>
        }
      />

      {recruiters.length === 0 ? (
        <ShellCard>
          <EmptyState
            icon="ti-circle-check"
            title="Queue is empty!"
            description="All flagged records have been processed and approved."
          />
        </ShellCard>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {recruiters.map((r) => {
            const isEditing = editingId === r.recruiter_id
            
            return (
              <ShellCard 
                key={r.recruiter_id} 
                style={{ 
                  padding: 18, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: 12,
                  transition: 'all 0.2s ease',
                  borderLeft: '4px solid var(--warning)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 16, fontWeight: 900, color: 'var(--text-primary)' }}>
                        {isEditing ? (
                          <input 
                            value={editForm.recruiter_name} 
                            onChange={(e) => setEditForm({...editForm, recruiter_name: e.target.value})} 
                            placeholder="Name" 
                            autoFocus
                            style={{ padding: '6px 10px', fontSize: 14 }}
                          />
                        ) : (
                          r.recruiter_name || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Missing Name</span>
                        )}
                      </span>
                      <Badge tone="danger">Flagged</Badge>
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      {r.company_name || 'No Company'} • {r.state || 'Unknown State'}
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: 8 }}>
                    {isEditing ? (
                      <>
                        <GhostButton onClick={cancelEdit}>Cancel</GhostButton>
                        <PrimaryButton onClick={() => saveEdit(r)}>Save & Approve</PrimaryButton>
                      </>
                    ) : (
                      <>
                        <GhostButton onClick={() => handleDeactivate(r.recruiter_id, r)} style={{ color: 'var(--danger)' }}>
                          <i className="ti ti-trash" /> Archive
                        </GhostButton>
                        <GhostButton onClick={() => startEdit(r)}>
                          <i className="ti ti-edit" /> Edit
                        </GhostButton>
                        <PrimaryButton onClick={() => handleApprove(r.recruiter_id, r)}>
                          <i className="ti ti-check" /> Approve
                        </PrimaryButton>
                      </>
                    )}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 8, padding: 12, background: 'var(--bg-primary)', borderRadius: 8 }}>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Email</div>
                    {isEditing ? (
                      <input 
                        value={editForm.email} 
                        onChange={(e) => setEditForm({...editForm, email: e.target.value})} 
                        placeholder="Email" 
                        style={{ width: '100%', padding: '6px 10px', fontSize: 13 }}
                      />
                    ) : (
                      <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{r.email}</div>
                    )}
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Phone</div>
                    {isEditing ? (
                      <input 
                        value={editForm.phone} 
                        onChange={(e) => setEditForm({...editForm, phone: e.target.value})} 
                        placeholder="Phone" 
                        style={{ width: '100%', padding: '6px 10px', fontSize: 13 }}
                      />
                    ) : (
                      <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{r.phone || '—'}</div>
                    )}
                  </div>
                </div>
              </ShellCard>
            )
          })}
        </div>
      )}
    </div>
  )
}
