import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Search, Monitor, Settings, Users, Briefcase, BarChart, Database, Activity, MapPin } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef(null);
  
  const actions = [
    { id: 'dashboard', title: 'Go to Dashboard', icon: BarChart, route: '/' },
    { id: 'recruiters', title: 'Search Recruiters', icon: Users, route: '/recruiters' },
    { id: 'companies', title: 'Search Companies', icon: Briefcase, route: '/directory' },
    { id: 'campaigns', title: 'View Campaigns', icon: Activity, route: '/campaigns' },
    { id: 'analytics', title: 'View Analytics', icon: BarChart, route: '/analytics' },
    { id: 'directory', title: 'View Directory', icon: Database, route: '/directory' },
    { id: 'settings', title: 'Open Settings', icon: Settings, route: '/settings' },
    { id: 'profile', title: 'My Profile', icon: Users, route: '/profile' },
    { id: 'admin_dashboard', title: 'Admin Terminal', icon: Monitor, route: '/admin' },
    { id: 'admin_users', title: 'User Management', icon: Users, route: '/admin/users' },
    { id: 'admin_visitors', title: 'Visitor Analytics', icon: Activity, route: '/admin/visitor-analytics' },
    { id: 'ai_search', title: 'AI Search', icon: Search, route: '/ai-search' },
  ];

  const filteredActions = actions.filter(action => 
    action.title.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleExecute = (action) => {
    setIsOpen(false);
    navigate(action.route);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filteredActions.length);
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredActions.length) % filteredActions.length);
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredActions[selectedIndex]) {
        handleExecute(filteredActions[selectedIndex]);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(8px)',
          zIndex: 9999,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          paddingTop: '12vh'
        }}
        onClick={() => setIsOpen(false)}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          transition={{ duration: 0.15, ease: 'easeOut' }}
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--card-border)',
            borderRadius: 16,
            width: '100%',
            maxWidth: 600,
            overflow: 'hidden',
            boxShadow: '0 24px 48px rgba(0,0,0,0.4)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div style={{ display: 'flex', alignItems: 'center', padding: '16px 24px', borderBottom: '1px solid var(--card-border)' }}>
            <Search size={20} style={{ color: 'var(--text-muted)', marginRight: 12 }} />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search actions, recruiters, or navigate... (Ctrl+K)"
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--text-primary)',
                fontSize: 18,
                width: '100%',
                fontWeight: 500
              }}
            />
          </div>
          <div style={{ padding: 12, maxHeight: 400, overflowY: 'auto' }}>
            {filteredActions.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                No actions found for "{query}"
              </div>
            ) : (
              filteredActions.map((action, idx) => {
                const Icon = action.icon;
                const isSelected = idx === selectedIndex;
                return (
                  <div
                    key={action.id}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    onClick={() => handleExecute(action)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '12px 16px',
                      borderRadius: 12,
                      cursor: 'pointer',
                      background: isSelected ? 'var(--card-border)' : 'transparent',
                      color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                      transition: 'background 0.1s'
                    }}
                  >
                    <Icon size={18} style={{ color: isSelected ? 'var(--accent)' : 'inherit' }} />
                    <span style={{ fontSize: 15, fontWeight: isSelected ? 600 : 500 }}>{action.title}</span>
                  </div>
                );
              })
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
