import { useEffect, useState, memo } from "react";
import api from "../services/api";
import { motion, AnimatePresence } from "framer-motion";

export default function EnrichmentLiveFeed() {
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchFeed = async () => {
      try {
        const { data } = await api.get("/analytics/enrichment-feed");
        if (isMounted) setFeed(data.feed || []);
      } catch (error) {
        if (isMounted) console.error("Failed to fetch enrichment feed", error);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchFeed();
    const interval = setInterval(fetchFeed, 5000); // Live poll every 5 seconds
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div style={{ padding: '24px', background: 'var(--bg-surface)', borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)', minHeight: '400px', maxHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ fontSize: '24px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--brand)', boxShadow: '0 0 10px var(--brand)',  }} />
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
        <div style={{ color: 'var(--text-muted)' }}>Connecting to data streams...</div>
      ) : feed.length === 0 ? (
        <div style={{ color: 'var(--text-muted)' }}>No recent activity. Workers might be idle.</div>
      ) : (
        <div className="custom-scrollbar" style={{ flex: 1, overflowY: 'auto', paddingRight: '8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <AnimatePresence>
            {feed.map((item) => (
              <FeedItem key={item.id} item={item} />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

const FeedItem = memo(({ item }) => (
  <motion.div
    initial={{ opacity: 0, y: -20, scale: 0.95 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    exit={{ opacity: 0, scale: 0.95 }}
    transition={{ duration: 0.3 }}
    style={{
      background: 'var(--bg-surface)',
      backdropFilter: 'blur(4px)',
      border: '1px solid var(--card-border)',
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
      backgroundColor: 'var(--brand-bg)',
      color: 'var(--brand)',
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
      <div style={{ color: 'var(--text-primary)', fontWeight: 500, fontSize: '15px' }}>{item.message}</div>
      <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <div style={{ color: 'var(--text-secondary)' }}><strong>Company:</strong> {item.company}</div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {item.title && <span>Title: {item.title}</span>}
          {item.location && <span>Location: {item.location}</span>}
          {item.phone && <span>Phone: {item.phone}</span>}
          {item.email && !item.email.includes("missing.local") && <span>Email: {item.email}</span>}
        </div>
      </div>
    </div>
    
    <div style={{ color: '#6b7280', fontSize: '12px', whiteSpace: 'nowrap', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
      <span>{item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'Just now'}</span>
      {item.timestamp && <span style={{ fontSize: '10px' }}>{new Date(item.timestamp).toLocaleDateString()}</span>}
    </div>
  </motion.div>
));
