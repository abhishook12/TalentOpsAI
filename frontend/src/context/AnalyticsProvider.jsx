import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { API } from '../services/api';

const AnalyticsContext = createContext({});

export const useAnalytics = () => useContext(AnalyticsContext);

export function AnalyticsProvider({ children }) {
  const [anonymousId, setAnonymousId] = useState('');
  const [sessionId, setSessionId] = useState('');
  const idleTimeoutRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);
  const lastActivityRef = useRef(Date.now());
  const isIdleRef = useRef(false);
  const clickCountRef = useRef(0);
  const sessionStartedRef = useRef(false);
  const prevPathRef = useRef(null);

  // Initialize identity
  useEffect(() => {
    try {
      let aid = localStorage.getItem('talentops_aid');
      if (!aid) {
        aid = crypto.randomUUID ? crypto.randomUUID() : `aid_${Math.random().toString(36).slice(2)}${Date.now()}`;
        localStorage.setItem('talentops_aid', aid);
      }
      setAnonymousId(aid);

      let sid = sessionStorage.getItem('talentops_sid');
      if (!sid) {
        sid = crypto.randomUUID ? crypto.randomUUID() : `sid_${Math.random().toString(36).slice(2)}${Date.now()}`;
        sessionStorage.setItem('talentops_sid', sid);
      }
      setSessionId(sid);
    } catch (e) {
      console.warn('Analytics init error:', e);
    }
  }, []);

  // API Call Wrapper — fully guarded, never throws
  const sendAnalytics = async (endpoint, payload) => {
    if (!anonymousId || !sessionId) return;
    try {
      const authSession = JSON.parse(localStorage.getItem('auth_session') || '{}');
      await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        keepalive: true,
        body: JSON.stringify({
          anonymous_id: anonymousId,
          session_id: sessionId,
          user_email: authSession?.email || null,
          ...payload
        })
      });
    } catch (e) {
      // Silently fail — analytics should never break the app
    }
  };

  // Get current path safely without useRouter
  const getCurrentPath = () => {
    try {
      return window.location.pathname;
    } catch {
      return '/';
    }
  };

  // 1. Session Start
  useEffect(() => {
    if (!anonymousId || !sessionId || sessionStartedRef.current) return;
    sessionStartedRef.current = true;
    prevPathRef.current = getCurrentPath();
    sendAnalytics('/analytics/session/start', {
      screen_size: `${window.innerWidth}x${window.innerHeight}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      referrer: document.referrer,
      user_agent: navigator.userAgent,
      current_page: getCurrentPath()
    });
  }, [anonymousId, sessionId]);

  // 2. Page Views — use popstate + MutationObserver to detect navigation without useRouter
  useEffect(() => {
    if (!sessionStartedRef.current) return;

    const checkPathChange = () => {
      const currentPath = getCurrentPath();
      if (prevPathRef.current !== null && prevPathRef.current !== currentPath) {
        sendAnalytics('/analytics/session/event', {
          event_type: 'page_view',
          current_page: currentPath,
          previous_page: prevPathRef.current
        });
      }
      prevPathRef.current = currentPath;
    };

    // Listen for browser navigation
    window.addEventListener('popstate', checkPathChange);
    
    // Poll for SPA navigation changes every 2 seconds
    const pathPoll = setInterval(checkPathChange, 2000);

    return () => {
      window.removeEventListener('popstate', checkPathChange);
      clearInterval(pathPoll);
    };
  }, [anonymousId, sessionId]);

  // 3. Activity Tracking & Heartbeat
  const resetIdle = () => {
    lastActivityRef.current = Date.now();
    if (isIdleRef.current) {
      isIdleRef.current = false;
      sendAnalytics('/analytics/session/event', { event_type: 'active' });
    }
  };

  useEffect(() => {
    if (!anonymousId || !sessionId) return;

    const handleActivity = () => resetIdle();
    const handleClick = () => {
      clickCountRef.current += 1;
      resetIdle();
    };

    window.addEventListener('mousemove', handleActivity, { passive: true });
    window.addEventListener('keydown', handleActivity, { passive: true });
    window.addEventListener('scroll', handleActivity, { passive: true });
    window.addEventListener('click', handleClick, { passive: true });

    // Check idle every 10s (Idle = 60s of no activity)
    idleTimeoutRef.current = setInterval(() => {
      if (!isIdleRef.current && Date.now() - lastActivityRef.current > 60000) {
        isIdleRef.current = true;
        sendAnalytics('/analytics/session/event', { event_type: 'idle' });
      }
    }, 10000);

    // Heartbeat every 30s
    heartbeatIntervalRef.current = setInterval(() => {
      sendAnalytics('/analytics/session/heartbeat', {
        status: isIdleRef.current ? 'Idle' : 'Active',
        clicks_since_last: clickCountRef.current,
        current_page: getCurrentPath()
      });
      clickCountRef.current = 0;
    }, 30000);

    // Before Unload
    const handleUnload = () => {
      sendAnalytics('/analytics/session/end', { current_page: getCurrentPath() });
    };
    window.addEventListener('beforeunload', handleUnload);

    return () => {
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('scroll', handleActivity);
      window.removeEventListener('click', handleClick);
      window.removeEventListener('beforeunload', handleUnload);
      clearInterval(idleTimeoutRef.current);
      clearInterval(heartbeatIntervalRef.current);
    };
  }, [anonymousId, sessionId]);

  return (
    <AnalyticsContext.Provider value={{ sessionId, anonymousId }}>
      {children}
    </AnalyticsContext.Provider>
  );
}
