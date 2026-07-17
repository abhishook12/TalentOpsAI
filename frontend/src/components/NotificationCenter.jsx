import React, { useState, useEffect } from 'react';
import { Bell, Check, Info, AlertTriangle, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

export default function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);

  const fetchNotifications = async () => {
    try {
      const res = await api.get('/notifications');
      setNotifications(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, []);

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
              transition={{ duration: 0.15, ease: 'easeOut' }}
              style={{
                position: 'absolute',
                top: 50, right: 10,
                width: 380,
                maxHeight: '80vh',
                background: 'var(--bg-surface)',
                border: '1px solid var(--card-border)',
                borderRadius: 16,
                zIndex: 9002,
                boxShadow: 'var(--shadow-lg)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Notifications</h3>
                {unreadCount > 0 && (
                  <button onClick={markAllRead} style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: 13, cursor: 'pointer', fontWeight: 600 }}>
                    Mark all read
                  </button>
                )}
              </div>
              <div style={{ overflowY: 'auto', flex: 1, padding: 8 }}>
                {notifications.length === 0 ? (
                  <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                    No notifications yet.
                  </div>
                ) : (
                  notifications.map(n => {
                    let Icon = Info;
                    let color = 'var(--accent)';
                    if (n.type === 'success') { Icon = Check; color = 'var(--success)'; }
                    if (n.type === 'warning') { Icon = AlertTriangle; color = 'var(--warning)'; }
                    if (n.type === 'error') { Icon = AlertCircle; color = 'var(--danger)'; }

                    return (
                      <div key={n.id} style={{ 
                        display: 'flex', gap: 12, padding: '12px 16px', 
                        background: n.read ? 'transparent' : 'rgba(14, 165, 233, 0.04)',
                        borderRadius: 12, margin: '4px 0'
                      }}>
                        <div style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 16, background: `${color}15`, color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <Icon size={16} />
                        </div>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: n.read ? 600 : 700, color: 'var(--text-primary)', marginBottom: 4 }}>{n.title}</div>
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{n.message}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                            {new Date(n.created_at).toLocaleString()}
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
