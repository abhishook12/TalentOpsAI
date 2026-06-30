import React, { useEffect, useState } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";

export default function ActivityLog() {
  const [activity, setActivity] = useState([]);
  const [dailyStats, setDailyStats] = useState({added: 0, improved: 0, removed: 0});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const fetchActivity = async () => {
    try {
      const { data } = await axios.get("http://127.0.0.1:8000/analytics/global-activity?limit=200", {
        withCredentials: true,
      });
      setActivity(data.activity || []);
      if(data.daily_stats) setDailyStats(data.daily_stats);
    } catch (error) {
      console.error("Failed to fetch activity", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivity();
    const interval = setInterval(fetchActivity, 5000);
    return () => clearInterval(interval);
  }, []);

  const filteredActivity = activity.filter((item) => {
    if (filter === "all") return true;
    return item.category === filter;
  });

  const stats = {
    added: activity.filter((a) => a.category === "added").length,
    improved: activity.filter((a) => a.category === "improved").length,
    needs_improvement: activity.filter((a) => a.category === "needs_improvement").length,
    removed: activity.filter((a) => a.category === "removed").length,
  };

  const formatTime = (isoString) => {
    if (!isoString) return "";
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const categoryOptions = [
    { key: "all", label: "All Activity" },
    { key: "added", label: "New Additions" },
    { key: "improved", label: "Improved" },
    { key: "needs_improvement", label: "Needs Improvement" },
  ];

  const getBadgeLabel = (category) => {
    switch (category) {
      case "added":
        return "ADDED";
      case "improved":
        return "IMPROVED";
      case "needs_improvement":
        return "UPDATED";
      case "removed":
        return "REMOVED";
      default:
        return "UPDATED";
    }
  };

  const getBadgeClasses = (category) =>
    category === "added" ? "bg-white text-black" : "bg-surface-container-high text-white";

  return (
    <div className="min-h-screen bg-background text-on-surface selection:bg-primary selection:text-on-primary">
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #000000;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #333535;
          border-radius: 2px;
        }
        .activity-pulse {
          position: relative;
        }
        .activity-pulse::after {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 2px;
          background: #ffffff;
          box-shadow: 0 0 8px rgba(255,255,255,0.3);
        }
        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .no-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>

      <header className="fixed top-0 left-0 right-0 z-50 flex w-full items-center justify-between border-b border-outline-variant bg-surface px-4 py-4">
        <div className="flex items-center gap-3">
          <i className="ti ti-cpu text-primary text-2xl" />
          <h1 className="text-xl font-bold tracking-tighter text-on-surface">TalentOps AI</h1>
        </div>
        <button className="flex h-10 w-10 items-center justify-center rounded-full transition-transform duration-150 hover:bg-surface-container active:scale-95">
          <i className="ti ti-search text-primary text-lg" />
        </button>
      </header>

      <main className="mx-auto min-h-screen max-w-2xl px-4 pb-24 pt-24">
        <div className="mb-8">
          <p className="mb-1 text-xs font-mono uppercase tracking-[0.2em] text-on-surface-variant">
            Global Activity Log
          </p>
          <div className="flex items-baseline justify-between">
            <h2 className="text-3xl font-bold text-on-surface">Activity Log</h2>
            <div className="flex items-center gap-3">
              <button onClick={fetchActivity} className="flex h-8 w-8 items-center justify-center rounded-full border border-outline-variant bg-surface-container-low transition-colors hover:bg-surface-container-high active:scale-95">
                <i className="ti ti-refresh text-[16px] text-on-surface-variant" />
              </button>
              <div className="flex items-center gap-1.5 rounded-full border border-outline-variant bg-surface-container-low px-2 py-1">
                <span className="h-2 w-2 animate-pulse rounded-full bg-[#00eefc]"></span>
                <span className="text-[10px] font-mono tracking-widest text-[#00eefc]">LIVE FEED</span>
              </div>
            </div>
          </div>
          <p className="mt-1 text-sm text-on-surface-variant">Real-time database changes</p>
        </div>

        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-bold text-on-surface">TODAY'S PROGRESS</h3>
            <div className="h-px flex-1 bg-outline-variant"></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-outline-variant bg-surface-container p-4">
              <div className="mb-2 flex items-start justify-between">
                <span className="text-[10px] font-mono uppercase text-on-surface-variant">NEW ADDITIONS</span>
                <i className="ti ti-user-plus text-[16px] text-primary" />
              </div>
              <div className="text-2xl font-bold text-primary">{dailyStats.added}</div>
            </div>
            <div className="rounded-lg border border-outline-variant bg-surface-container p-4">
              <div className="mb-2 flex items-start justify-between">
                <span className="text-[10px] font-mono uppercase text-on-surface-variant">IMPROVED</span>
                <i className="ti ti-trending-up text-[16px] text-primary" />
              </div>
              <div className="text-2xl font-bold text-primary">{dailyStats.improved}</div>
            </div>
            <div className="rounded-lg border border-outline-variant bg-surface-container-low p-4 opacity-60">
              <div className="mb-2 flex items-start justify-between">
                <span className="text-[10px] font-mono uppercase text-on-surface-variant">REMOVED</span>
                <i className="ti ti-flag text-[16px] text-on-surface-variant" />
              </div>
              <div className="text-2xl font-bold text-on-surface-variant">{dailyStats.removed}</div>
            </div>
            <div className="rounded-lg border border-outline-variant bg-surface-container-low p-4 opacity-60">
              <div className="mb-2 flex items-start justify-between">
                <span className="text-[10px] font-mono uppercase text-on-surface-variant">RECENT ACTIVITY</span>
                <i className="ti ti-history text-[16px] text-on-surface-variant" />
              </div>
              <div className="text-2xl font-bold text-on-surface-variant">{activity.length}</div>
            </div>
          </div>
        </div>

        <div className="mb-6 flex gap-2 overflow-x-auto pb-4 no-scrollbar">
          {categoryOptions.map((cat) => {
            const isActive = filter === cat.key;
            return (
              <button
                key={cat.key}
                onClick={() => setFilter(cat.key)}
                className={`whitespace-nowrap rounded-full px-4 py-1.5 font-mono text-xs transition-colors ${
                  isActive
                    ? "bg-primary font-bold text-on-primary"
                    : "border border-outline-variant bg-surface-container text-on-surface hover:bg-surface-container-highest"
                }`}
              >
                {cat.label}
              </button>
            );
          })}
        </div>

        <div className="space-y-3">
          <AnimatePresence>
            {filteredActivity.map((item, index) => {
              const label = getBadgeLabel(item.category);
              const badgeClasses = getBadgeClasses(item.category);

              return (
                <motion.div
                  key={item.id || `${item.name}-${index}`}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="activity-pulse flex flex-col gap-2 rounded-lg border border-outline-variant bg-surface-container p-4 transition-all hover:bg-surface-container-high active:scale-[0.98]"
                >
                  <div className="flex items-start justify-between">
                    <span className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${badgeClasses}`}>
                      {label}
                    </span>
                    <span className="text-[10px] font-mono text-on-surface-variant">
                      {formatTime(item.timestamp)}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-on-surface">{item.name || "Unnamed entry"}</h3>
                    <p className="mt-0.5 text-[11px] uppercase tracking-wide text-primary">
                      {item.title || "No Designation"}
                    </p>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-y-2 gap-x-4 text-[11px] font-mono">
                    <div className="flex items-center gap-1.5 overflow-hidden">
                      <i className="ti ti-building text-[14px] text-on-surface-variant" />
                      <span className="truncate uppercase text-on-surface">{item.company || "Unknown Company"}</span>
                    </div>
                    <div className="flex items-center gap-1.5 overflow-hidden">
                      <i className="ti ti-map-pin text-[14px] text-on-surface-variant" />
                      <span className="truncate uppercase text-on-surface">{item.location || "Unknown Location"}</span>
                    </div>
                    <div className="flex items-center gap-1.5 overflow-hidden">
                      <i className="ti ti-mail text-[14px] text-primary" />
                      <span className="truncate text-on-surface">{item.email || "No Email"}</span>
                    </div>
                    <div className="flex items-center gap-1.5 overflow-hidden opacity-60">
                      <i className="ti ti-phone text-[14px] text-on-surface-variant" />
                      <span className="truncate text-on-surface-variant">{item.phone || "No Phone"}</span>
                    </div>
                  </div>
                </motion.div>
              );
            })}

            {filteredActivity.length === 0 && (
              <div className="rounded-lg border border-dashed border-outline-variant p-8 text-center font-mono text-sm text-on-surface-variant">
                {loading ? "Loading live data streams..." : "No activity found for this filter."}
              </div>
            )}
          </AnimatePresence>
        </div>

        <div className="mb-8 mt-16 flex flex-col items-center gap-4 text-center">
          <div className="flex items-center gap-2">
            <i className="ti ti-settings text-sm text-on-surface-variant" />
            <p className="text-[10px] font-mono uppercase tracking-widest text-on-surface-variant">
              REC-INTEL v4.0
            </p>
          </div>
          <p className="text-[10px] font-mono text-on-surface-variant/40">
            BUILT BY ABHISHEK • SERVER NODE US-EAST-01A
          </p>
        </div>
      </main>

    </div>
  );
}
