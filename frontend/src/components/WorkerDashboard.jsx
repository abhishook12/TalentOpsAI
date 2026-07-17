import React, { useEffect, useState, useRef } from "react";
import api from "../services/api";
import { motion, AnimatePresence } from "framer-motion";
import EnrichmentLiveFeed from "./EnrichmentLiveFeed";

const fetchStatus = async () => {
  const { data } = await api.get("/admin/workers/status");
  return data;
};

const fetchLogs = async (name) => {
  const { data } = await api.get(`/admin/workers/logs/${name}`);
  return data;
};

export default function WorkerDashboard() {
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedWorker, setExpandedWorker] = useState(null);
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  const load = async () => {
    try {
      const data = await fetchStatus();
      setWorkers(data);
    } catch (e) {
      console.error("Failed to load workers", e);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async (name) => {
    try {
      const data = await fetchLogs(name);
      setLogs(data);
    } catch (e) {
      console.error("Failed to load logs", e);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (expandedWorker) {
      loadLogs(expandedWorker);
      const interval = setInterval(() => loadLogs(expandedWorker), 2000);
      return () => clearInterval(interval);
    }
  }, [expandedWorker]);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const toggle = async (name, action) => {
    try {
      await api.post(`/admin/workers/${action}?name=${name}`, null);
      load();
    } catch (e) {
      console.error("Failed to toggle worker", e);
    }
  };

  return (
    <div style={{ padding: '24px', background: 'linear-gradient(135deg, #111827, #1f2937, #374151)', borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)', minHeight: '400px' }}>
      <h2 style={{ fontSize: '24px', fontWeight: 500, color: 'var(--text-inverse)', marginBottom: '16px' }}>Worker Dashboard</h2>
      {loading ? (
        <div style={{ color: '#9ca3af' }}>Loading...</div>
      ) : (
        <table style={{ width: '100%', textAlign: 'left', background: 'var(--bg-surface)', backdropFilter: 'blur(4px)', borderRadius: '8px', overflow: 'hidden', borderCollapse: 'collapse' }}>
          <thead style={{ background: 'var(--accent-bg)' }}>
            <tr>
              <th style={{ padding: '12px 16px', color: '#e5e7eb', borderBottom: '1px solid var(--card-border)' }}>Name</th>
              <th style={{ padding: '12px 16px', color: '#e5e7eb', borderBottom: '1px solid var(--card-border)' }}>PID</th>
              <th style={{ padding: '12px 16px', color: '#e5e7eb', borderBottom: '1px solid var(--card-border)' }}>Status</th>
              <th style={{ padding: '12px 16px', color: '#e5e7eb', borderBottom: '1px solid var(--card-border)' }}>Uptime (s)</th>
              <th style={{ padding: '12px 16px', color: '#e5e7eb', borderBottom: '1px solid var(--card-border)' }}>Control</th>
            </tr>
          </thead>
          <tbody>
            {workers.map(w => (
              <React.Fragment key={w.name}>
                <tr
                  style={{
                    borderBottom: '1px solid var(--card-border)',
                    backgroundColor: w.status === 'running' ? 'rgba(16, 185, 129, 0.1)' : 'transparent',
                    transition: 'background-color 0.2s'
                  }}
                >
                  <td style={{ padding: '12px 16px', color: '#f3f4f6' }}>{w.name}</td>
                  <td style={{ padding: '12px 16px', color: '#f3f4f6' }}>{w.pid ?? "—"}</td>
                  <td style={{ padding: '12px 16px', color: '#f3f4f6', textTransform: 'capitalize' }}>{w.status}</td>
                  <td style={{ padding: '12px 16px', color: '#f3f4f6' }}>{w.uptime_seconds?.toFixed(2) ?? "—"}</td>
                  <td style={{ padding: '12px 16px', display: 'flex', gap: '8px' }}>
                    {w.status === "running" ? (
                      <button
                        onClick={() => toggle(w.name, "stop")}
                        style={{ padding: '6px 12px', background: '#dc2626', color: 'var(--text-inverse)', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' }}
                      >
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => toggle(w.name, "start")}
                        style={{ padding: '6px 12px', background: '#059669', color: 'var(--text-inverse)', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' }}
                      >
                        Start
                      </button>
                    )}
                    <button
                      onClick={() => setExpandedWorker(expandedWorker === w.name ? null : w.name)}
                      style={{ padding: '6px 12px', background: 'var(--accent-bg)', color: 'var(--text-inverse)', border: '1px solid var(--card-border)', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' }}
                    >
                      {expandedWorker === w.name ? "Hide Logs" : "View Logs"}
                    </button>
                  </td>
                </tr>
                <AnimatePresence>
                  {expandedWorker === w.name && (
                    <motion.tr
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                    >
                      <td colSpan="5" style={{ padding: 0 }}>
                        <div style={{
                          background: '#000', padding: '16px', fontFamily: 'monospace', fontSize: '13px',
                          color: '#34d399', height: '300px', overflowY: 'auto', margin: '0 16px 16px 16px',
                          borderRadius: '6px', border: '1px solid #374151'
                        }}>
                          {logs.length === 0 ? (
                            <span style={{ color: '#6b7280' }}>No logs output yet.</span>
                          ) : (
                            logs.map((log, i) => <div key={i} style={{ marginBottom: '4px', wordBreak: 'break-all' }}>{log}</div>)
                          )}
                          <div ref={logsEndRef} />
                        </div>
                      </td>
                    </motion.tr>
                  )}
                </AnimatePresence>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
      
      <div style={{ marginTop: '32px' }}>
        <EnrichmentLiveFeed />
      </div>
    </div>
  );
}
