import { useState, useEffect, useCallback } from 'react';
import { Bell, Check, Info, AlertTriangle, AlertCircle, Radio, Send, Plus, X } from 'lucide-react';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function NotificationCenter() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin' || user?.email === 'abhishekjadon824@gmail.com';

  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [showComposer, setShowComposer] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [composerForm, setComposerForm] = useState({
    title: '',
    message: '',
    type: 'info'
  });

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await api.get('/notifications', { skipCache: true });
      if (Array.isArray(res.data)) {
        setNotifications(res.data);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      fetchNotifications();
    }, 90000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  useEffect(() => {
    const handleToggle = () => setIsOpen(o => !o);
    window.addEventListener('toggle-notification-center', handleToggle);
    return () => window.removeEventListener('toggle-notification-center', handleToggle);
  }, []);

  const markAllRead = async () => {
    try {
      await api.post('/notifications/read');
      setNotifications(notifications.map(n => ({ ...n, read: true })));
    } catch (e) {
      console.error(e);
    }
  };

  const markItemRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/read`);
      setNotifications(notifications.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendBroadcast = async (e) => {
    e.preventDefault();
    if (!composerForm.title.trim() || !composerForm.message.trim()) {
      toast.error('Title and message are required');
      return;
    }
    setIsSending(true);
    try {
      const res = await api.post('/notifications', {
        title: composerForm.title.trim(),
        message: composerForm.message.trim(),
        type: composerForm.type,
        user_id: null
      });
      if (res.data?.notification) {
        setNotifications(prev => [res.data.notification, ...prev.filter(x => x.id !== res.data.notification.id)]);
      }
      toast.success('📢 Fleet broadcast dispatched successfully!');
      setComposerForm({ title: '', message: '', type: 'info' });
      setShowComposer(false);
      await fetchNotifications();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to dispatch broadcast');
    } finally {
      setIsSending(false);
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <>
      <button 
        className="cc-icon-button" 
        title="Notifications" 
        aria-label="Notifications" 
        style={{ position: 'relative' }} 
        onClick={() => setIsOpen(true)}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span style={{ 
            position: 'absolute', top: 7, right: 9, 
            width: 8, height: 8, borderRadius: 999, 
            background: 'var(--danger)',
            boxShadow: '0 0 8px var(--danger)'
          }} />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div 
              onClick={() => setIsOpen(false)}
              style={{ position: 'fixed', inset: 0, zIndex: 9001 }} 
            />
            <motion.div 
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              style={{
                position: 'absolute',
                top: 50, right: 10,
                width: 400,
                maxHeight: '85vh',
                background: 'var(--bg-surface)',
                border: '1px solid var(--card-border)',
                borderRadius: 8,
                zIndex: 9002,
                boxShadow: 'var(--shadow-lg)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
              }}
            >
              <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Notifications</h3>
                  {unreadCount > 0 && (
                    <span style={{ fontSize: 11, padding: '1px 6px', borderRadius: 10, background: 'rgba(239, 68, 68, 0.15)', color: 'var(--danger)', fontWeight: 700 }}>
                      {unreadCount} new
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {isAdmin && (
                    <button 
                      onClick={() => setShowComposer(!showComposer)} 
                      style={{ 
                        background: showComposer ? '#1E293B' : 'rgba(56, 189, 248, 0.12)', 
                        border: '1px solid rgba(56, 189, 248, 0.3)', 
                        color: '#38BDF8', 
                        fontSize: 12, 
                        cursor: 'pointer', 
                        fontWeight: 600,
                        padding: '3px 8px',
                        borderRadius: 5,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4
                      }}
                      title="Dispatch fleet broadcast"
                    >
                      {showComposer ? <X size={12} /> : <Plus size={12} />}
                      <span>{showComposer ? 'Cancel' : 'Broadcast'}</span>
                    </button>
                  )}
                  {unreadCount > 0 && (
                    <button onClick={markAllRead} style={{ background: 'none', border: 'none', color: 'var(--brand)', fontSize: 12, cursor: 'pointer', fontWeight: 600 }}>
                      Mark all read
                    </button>
                  )}
                </div>
              </div>

              {/* Admin Broadcast Composer */}
              {isAdmin && showComposer && (
                <form onSubmit={handleSendBroadcast} style={{ padding: '12px 16px', background: '#0F172A', borderBottom: '1px solid var(--card-border)', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Radio size={13} />
                    <span>Dispatch Global Fleet Broadcast</span>
                  </div>
                  <input
                    type="text"
                    placeholder="Broadcast title..."
                    value={composerForm.title}
                    onChange={(e) => setComposerForm({ ...composerForm, title: e.target.value })}
                    style={{
                      background: '#1E293B',
                      border: '1px solid var(--card-border)',
                      borderRadius: 4,
                      padding: '6px 10px',
                      color: 'var(--text-primary)',
                      fontSize: 12
                    }}
                  />
                  <textarea
                    rows={2}
                    placeholder="Broadcast announcement message..."
                    value={composerForm.message}
                    onChange={(e) => setComposerForm({ ...composerForm, message: e.target.value })}
                    style={{
                      background: '#1E293B',
                      border: '1px solid var(--card-border)',
                      borderRadius: 4,
                      padding: '6px 10px',
                      color: 'var(--text-primary)',
                      fontSize: 12,
                      resize: 'none'
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                    <select
                      value={composerForm.type}
                      onChange={(e) => setComposerForm({ ...composerForm, type: e.target.value })}
                      style={{
                        background: '#1E293B',
                        border: '1px solid var(--card-border)',
                        borderRadius: 4,
                        padding: '4px 8px',
                        color: 'var(--text-secondary)',
                        fontSize: 11
                      }}
                    >
                      <option value="info">Info</option>
                      <option value="update">Update</option>
                      <option value="success">Success</option>
                      <option value="warning">Warning</option>
                    </select>
                    <button
                      type="submit"
                      disabled={isSending}
                      style={{
                        background: '#0284C7',
                        border: 'none',
                        color: '#fff',
                        borderRadius: 4,
                        padding: '5px 12px',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 5
                      }}
                    >
                      <Send size={12} />
                      <span>{isSending ? 'Sending...' : 'Send Broadcast'}</span>
                    </button>
                  </div>
                </form>
              )}

              <div style={{ overflowY: 'auto', flex: 1, padding: 8 }}>
                {notifications.length === 0 ? (
                  <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                    No notifications yet.
                  </div>
                ) : (
                  notifications.map(n => {
                    let Icon = Info;
                    let color = 'var(--brand)';
                    if (n.type === 'success') { Icon = Check; color = 'var(--success)'; }
                    if (n.type === 'warning') { Icon = AlertTriangle; color = 'var(--warning)'; }
                    if (n.type === 'error') { Icon = AlertCircle; color = 'var(--danger)'; }
                    if (n.type === 'update') { Icon = Radio; color = '#10B981'; }

                    return (
                      <div 
                        key={n.id} 
                        onClick={() => !n.read && markItemRead(n.id)}
                        style={{ 
                          display: 'flex', gap: 12, padding: '12px 14px', 
                          background: n.read ? 'transparent' : 'rgba(56, 189, 248, 0.05)',
                          border: n.read ? '1px solid transparent' : '1px solid rgba(56, 189, 248, 0.12)',
                          borderRadius: 6, margin: '4px 0',
                          cursor: n.read ? 'default' : 'pointer'
                        }}
                        title={n.read ? '' : 'Click to mark as read'}
                      >
                        <div style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 6, background: `${color}15`, color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <Icon size={16} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                            <div style={{ fontSize: 13, fontWeight: n.read ? 600 : 700, color: 'var(--text-primary)', marginBottom: 3 }}>
                              {n.title}
                            </div>
                            {!n.read && (
                              <span style={{ width: 6, height: 6, borderRadius: 999, background: color, display: 'inline-block' }} />
                            )}
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{n.message}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                            {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                          </div>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
