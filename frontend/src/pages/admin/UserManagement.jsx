import { toast } from 'react-hot-toast'
import { useState, useEffect } from 'react';
import api, { getErrorMessage } from '../../services/api';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const limit = 50;
  
  // Selection & Details
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [selectedUserDetail, setSelectedUserDetail] = useState(null);
  const [userDetailLoading, setUserDetailLoading] = useState(false);
  const [userSessions, setUserSessions] = useState([]);
  const [userHistory, setUserHistory] = useState([]);
  
  // Modals / Overlays
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState({ email: '', first_name: '', last_name: '', role_name: 'user', company: '' });

  const loadAnalytics = async () => {
    try {
      const { data } = await api.get('/users/analytics');
      setAnalytics(data);
    } catch (err) {
      console.error("Failed to load analytics", err);
    }
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/users', { 
        params: { 
          search: search || undefined,
          role: roleFilter || undefined,
          status: statusFilter || undefined,
          skip: (page - 1) * limit,
          limit
        } 
      });
      setUsers(data.items || []);
      setTotalPages(data.pages || 1);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load users'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadUsers();
    }, 400);
    return () => clearTimeout(timer);
  }, [search, roleFilter, statusFilter, page]);

  const toggleSelection = (id) => {
    if (selectedUsers.includes(id)) {
      setSelectedUsers(selectedUsers.filter(uId => uId !== id));
    } else {
      setSelectedUsers([...selectedUsers, id]);
    }
  };

  const toggleAll = () => {
    if (selectedUsers.length === users.length && users.length > 0) {
      setSelectedUsers([]);
    } else {
      setSelectedUsers(users.map(u => u.id));
    }
  };

  const executeBulkAction = async (action, value) => {
    if (selectedUsers.length === 0) return;
    if (!window.confirm(`Are you sure you want to perform this action on ${selectedUsers.length} users?`)) return;
    
    try {
      await api.post('/users/bulk-action', { user_ids: selectedUsers, action, value });
      setSelectedUsers([]);
      loadUsers();
      loadAnalytics();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Bulk action failed'));
    }
  };

  const updateRole = async (user, role_name) => {
    try {
      await api.put(`/users/${user.id}/status`, { role_name });
      loadUsers();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update user role'));
    }
  };

  const deleteUser = async (id) => {
    if (!window.confirm("Are you sure you want to delete this user?")) return;
    try {
      await api.delete(`/users/${id}`);
      loadUsers();
      loadAnalytics();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to delete user'));
    }
  };

  const forceLogout = async (id) => {
    if (!window.confirm("Force logout all active sessions for this user?")) return;
    try {
      await api.post(`/users/${id}/force-logout`);
      toast.success("User has been logged out.");
      if (selectedUserDetail?.id === id) loadUserDetails(id);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to force logout'));
    }
  };

  const loadUserDetails = async (id) => {
    setUserDetailLoading(true);
    setSelectedUserDetail(null);
    try {
      const [userRes, sessionsRes, historyRes] = await Promise.all([
        api.get(`/users/${id}`),
        api.get(`/users/${id}/sessions`),
        api.get(`/users/${id}/login-history`)
      ]);
      setSelectedUserDetail(userRes.data);
      setUserSessions(sessionsRes.data);
      setUserHistory(historyRes.data);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load user details'));
    } finally {
      setUserDetailLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.post('/users/', newUser);
      setShowCreateModal(false);
      setNewUser({ email: '', first_name: '', last_name: '', role_name: 'user', company: '' });
      loadUsers();
      loadAnalytics();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to create user'));
    }
  };

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1400, margin: '0 auto', color: 'var(--text-primary)', fontFamily: '"Inter", sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, background: 'linear-gradient(90deg, #fff, #aaa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>User Management</h1>
          <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: 14 }}>Manage roles, permissions, and platform access.</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} style={{ padding: '10px 20px', borderRadius: 8, background: '#3b82f6', color: '#ffffff', border: 'none', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)' }}>
          + Add New User
        </button>
      </div>

      {/* Analytics Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20, marginBottom: 32 }}>
        {[
          { label: 'Total Users', value: analytics?.total || 0, color: '#3b82f6' },
          { label: 'Active Users', value: analytics?.active || 0, color: '#10b981' },
          { label: 'Inactive Users', value: analytics?.inactive || 0, color: '#f59e0b' },
          { label: 'New This Week', value: analytics?.new_last_7_days || 0, color: '#8b5cf6' }
        ].map((stat, i) => (
          <div key={i} style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: 20, position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, width: 4, height: '100%', background: stat.color }} />
            <div style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>{stat.label}</div>
            <div style={{ fontSize: 32, fontWeight: 800, marginTop: 8, color: 'var(--text-primary)' }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, email, or company..."
          style={{
            padding: '10px 16px', borderRadius: 8, border: '1px solid var(--card-border)',
            background: 'var(--bg-surface)', color: 'var(--text-primary)', flex: '1 1 300px', outline: 'none'
          }}
        />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          style={{ padding: '10px 16px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }}
        >
          <option value="">All Roles</option>
          <option value="superadmin">Superadmin</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: '10px 16px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }}
        >
          <option value="">All Statuses</option>
          <option value="Active">Active</option>
          <option value="Inactive">Inactive</option>
          <option value="Deleted">Deleted</option>
        </select>

        {selectedUsers.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(59, 130, 246, 0.1)', padding: '0 16px', borderRadius: 8, border: '1px solid rgba(59, 130, 246, 0.3)' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#60a5fa' }}>{selectedUsers.length} selected</span>
            <button onClick={() => executeBulkAction('status', 'Active')} style={{ background: 'transparent', border: 'none', color: '#10b981', cursor: 'pointer', fontWeight: 600 }}>Activate</button>
            <button onClick={() => executeBulkAction('status', 'Inactive')} style={{ background: 'transparent', border: 'none', color: '#f59e0b', cursor: 'pointer', fontWeight: 600 }}>Deactivate</button>
            <button onClick={() => executeBulkAction('delete')} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontWeight: 600 }}>Delete</button>
          </div>
        )}
      </div>

      {error && <div style={{ color: '#ef4444', padding: 12, background: 'rgba(239, 68, 68, 0.1)', borderRadius: 8, marginBottom: 20 }}>{error}</div>}

      <div style={{ display: 'flex', gap: 24 }}>
        {/* Main Table */}
        <div style={{ flex: 1, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, overflow: 'hidden', boxShadow: '0 8px 32px rgba(0,0,0,0.1)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 14 }}>
            <thead style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--card-border)' }}>
              <tr>
                <th style={{ padding: '16px', width: 40 }}><input type="checkbox" checked={users.length > 0 && selectedUsers.length === users.length} onChange={toggleAll} /></th>
                <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-muted)' }}>User</th>
                <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-muted)' }}>Company</th>
                <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-muted)' }}>Role</th>
                <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-muted)' }}>Status</th>
                <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-muted)' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && users.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: '24px 20px' }}><SkeletonRow rows={10} gap={16} height={20} /></td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>No users found.</td></tr>
              ) : (
                users.map(user => (
                  <tr key={user.id} style={{ borderBottom: '1px solid var(--card-border)', transition: 'background 0.2s', cursor: 'pointer' }} onClick={() => loadUserDetails(user.id)} className="hover-row">
                    <td style={{ padding: '16px' }} onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={selectedUsers.includes(user.id)} onChange={() => toggleSelection(user.id)} />
                    </td>
                    <td style={{ padding: '16px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{user.first_name} {user.last_name}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{user.email}</div>
                    </td>
                    <td style={{ padding: '16px', color: 'var(--text-secondary)' }}>{user.company || '-'}</td>
                    <td style={{ padding: '16px' }} onClick={(e) => e.stopPropagation()}>
                      <select
                        value={user.role_name}
                        onChange={(e) => updateRole(user, e.target.value)}
                        style={{ padding: '6px 12px', borderRadius: 6, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', fontSize: 13 }}
                      >
                        <option value="superadmin">Superadmin</option>
                        <option value="admin">Admin</option>
                        <option value="user">User</option>
                        <option value="readonly">Read-Only</option>
                      </select>
                    </td>
                    <td style={{ padding: '16px' }}>
                      <span style={{ 
                        padding: '4px 8px', borderRadius: 12, fontSize: 12, fontWeight: 600,
                        background: user.status === 'Active' ? 'rgba(16, 185, 129, 0.1)' : user.status === 'Inactive' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        color: user.status === 'Active' ? '#10b981' : user.status === 'Inactive' ? '#f59e0b' : '#ef4444'
                      }}>
                        {user.status || 'Unknown'}
                      </span>
                    </td>
                    <td style={{ padding: '16px' }} onClick={(e) => e.stopPropagation()}>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={() => forceLogout(user.id)} style={{ padding: '6px 10px', background: 'var(--accent-bg)', border: 'none', borderRadius: 4, color: 'var(--text-primary)', cursor: 'pointer', fontSize: 12 }}>Logout</button>
                        <button onClick={() => deleteUser(user.id)} style={{ padding: '6px 10px', background: 'rgba(239, 68, 68, 0.1)', border: 'none', borderRadius: 4, color: '#ef4444', cursor: 'pointer', fontSize: 12 }}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderTop: '1px solid var(--card-border)' }}>
              <button disabled={page === 1} onClick={() => setPage(page - 1)} style={{ padding: '8px 16px', background: 'var(--bg-surface)', border: 'none', borderRadius: 6, color: 'var(--text-primary)', cursor: page === 1 ? 'not-allowed' : 'pointer' }}>Previous</button>
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Page {page} of {totalPages}</span>
              <button disabled={page === totalPages} onClick={() => setPage(page + 1)} style={{ padding: '8px 16px', background: 'var(--bg-surface)', border: 'none', borderRadius: 6, color: 'var(--text-primary)', cursor: page === totalPages ? 'not-allowed' : 'pointer' }}>Next</button>
            </div>
          )}
        </div>

        {/* Side Panel (Slide out) */}
        {selectedUserDetail && (
          <div style={{ width: 400, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
            <div style={{ padding: 20, borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>User Details</h2>
              <button onClick={() => setSelectedUserDetail(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 20 }}>&times;</button>
            </div>
            
            <div style={{ padding: 20, overflowY: 'auto', flex: 1 }}>
              <div style={{ textAlign: 'center', marginBottom: 24 }}>
                <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', margin: '0 auto 12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32, fontWeight: 800, color: 'var(--text-primary)' }}>
                  {selectedUserDetail.first_name[0]}{selectedUserDetail.last_name[0]}
                </div>
                <h3 style={{ margin: '0 0 4px', fontSize: 20 }}>{selectedUserDetail.first_name} {selectedUserDetail.last_name}</h3>
                <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>{selectedUserDetail.email}</div>
              </div>

              <div style={{ marginBottom: 24 }}>
                <h4 style={{ margin: '0 0 12px', fontSize: 12, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: 0.5 }}>Information</h4>
                <div style={{ background: 'var(--bg-surface)', borderRadius: 8, padding: 12, fontSize: 13 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-muted)' }}>Company:</span>
                    <span>{selectedUserDetail.company || '-'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-muted)' }}>Country:</span>
                    <span>{selectedUserDetail.country || '-'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Joined:</span>
                    <span>{new Date(selectedUserDetail.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: 24 }}>
                <h4 style={{ margin: '0 0 12px', fontSize: 12, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: 0.5 }}>Active Sessions ({userSessions.filter(s => s.is_active).length})</h4>
                {userSessions.length > 0 ? userSessions.filter(s => s.is_active).map(session => (
                  <div key={session.id} style={{ background: 'var(--bg-surface)', borderRadius: 8, padding: 12, fontSize: 12, marginBottom: 8, borderLeft: '3px solid #10b981' }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{session.device || 'Unknown Device'} - {session.browser}</div>
                    <div style={{ color: 'var(--text-muted)' }}>IP: {session.ip_address}</div>
                  </div>
                )) : <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No active sessions</div>}
              </div>

              <div>
                <h4 style={{ margin: '0 0 12px', fontSize: 12, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: 0.5 }}>Recent Logins</h4>
                {userHistory.length > 0 ? userHistory.slice(0, 5).map(hist => (
                  <div key={hist.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--card-border)', fontSize: 12 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: hist.status === 'success' ? '#10b981' : '#ef4444' }} />
                    <div style={{ flex: 1 }}>
                      <div>{hist.ip_address} ({hist.os})</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{new Date(hist.timestamp).toLocaleString()}</div>
                    </div>
                  </div>
                )) : <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No login history</div>}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Modal Overlay */}
      {showCreateModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: 'var(--panel-bg)', padding: 32, borderRadius: 16, width: 400, boxShadow: '0 20px 40px rgba(0,0,0,0.4)', border: '1px solid var(--card-border)' }}>
            <h2 style={{ margin: '0 0 24px', fontSize: 22 }}>Create New User</h2>
            <form onSubmit={handleCreateUser}>
              <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>First Name</label>
                  <input required value={newUser.first_name} onChange={e => setNewUser({...newUser, first_name: e.target.value})} style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Last Name</label>
                  <input required value={newUser.last_name} onChange={e => setNewUser({...newUser, last_name: e.target.value})} style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
                </div>
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Email</label>
                <input required type="email" value={newUser.email} onChange={e => setNewUser({...newUser, email: e.target.value})} style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Company (Optional)</label>
                <input value={newUser.company} onChange={e => setNewUser({...newUser, company: e.target.value})} style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Role</label>
                <select value={newUser.role_name} onChange={e => setNewUser({...newUser, role_name: e.target.value})} style={{ width: '100%', padding: '10px 12px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', boxSizing: 'border-box' }}>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                  <option value="superadmin">Superadmin</option>
                  <option value="readonly">Read-Only</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setShowCreateModal(false)} style={{ padding: '10px 16px', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontWeight: 600 }}>Cancel</button>
                <button type="submit" style={{ padding: '10px 24px', background: '#3b82f6', border: 'none', borderRadius: 8, color: 'var(--text-primary)', cursor: 'pointer', fontWeight: 600 }}>Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      <style>{`
        .hover-row:hover { background: rgba(255,255,255,0.02); }
      `}</style>
    </div>
  );
}

