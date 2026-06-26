import React, { useEffect, useState } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";

export default function EnrichmentLiveFeed() {
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchFeed = async () => {
    try {
      const { data } = await axios.get("http://127.0.0.1:8000/analytics/enrichment-feed", { withCredentials: true });
      setFeed(data.feed || []);
    } catch (error) {
      console.error("Failed to fetch enrichment feed", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeed();
    const interval = setInterval(fetchFeed, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '24px', background: 'linear-gradient(135deg, #111827, #1f2937, #374151)', borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)', minHeight: '400px', maxHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ fontSize: '24px', fontWeight: 500, color: '#fff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#10b981', boxShadow: '0 0 10px #10b981', animation: 'pulse 2s infinite' }} />
        Live Enrichment Feed
      </h2>
      
      <style>{`
        @keyframes pulse {
          0% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
          100% { opacity: 1; transform: scale(1); }
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05); 
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2); 
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.3); 
        }
      `}</style>

      {loading && feed.length === 0 ? (
        <div style={{ color: '#9ca3af' }}>Connecting to data streams...</div>
      ) : feed.length === 0 ? (
        <div style={{ color: '#9ca3af' }}>No recent activity. Workers might be idle.</div>
      ) : (
        <div className="custom-scrollbar" style={{ flex: 1, overflowY: 'auto', paddingRight: '8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <AnimatePresence>
            {feed.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  backdropFilter: 'blur(4px)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px'
                }}
              >
                <div style={{ 
                  padding: '8px', 
                  borderRadius: '8px', 
                  backgroundColor: item.type === 'discovery' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                  color: item.type === 'discovery' ? '#34d399' : '#60a5fa',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {item.type === 'discovery' ? (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                  ) : (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                  )}
                </div>
                
                <div style={{ flex: 1 }}>
                  <div style={{ color: '#f3f4f6', fontWeight: 500, fontSize: '15px' }}>{item.message}</div>
                  <div style={{ color: '#9ca3af', fontSize: '13px', marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <div style={{ color: '#e5e7eb' }}><strong>Company:</strong> {item.company}</div>
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                      {item.title && <span>💼 {item.title}</span>}
                      {item.location && <span>📍 {item.location}</span>}
                      {item.phone && <span>📞 {item.phone}</span>}
                      {item.email && !item.email.includes("missing.local") && <span>✉️ {item.email}</span>}
                    </div>
                  </div>
                </div>
                
                <div style={{ color: '#6b7280', fontSize: '12px', whiteSpace: 'nowrap', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                  <span>{item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'Just now'}</span>
                  {item.timestamp && <span style={{ fontSize: '10px' }}>{new Date(item.timestamp).toLocaleDateString()}</span>}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
