import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react';

const GlobalUploadStatus = () => {
  const [activeJob, setActiveJob] = useState(null);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/upload/jobs`);
        const jobs = response.data;
        if (jobs && jobs.length > 0) {
          // Find first active job
          const running = jobs.find(j => j.status === 'processing' || j.status === 'queued');
          setActiveJob(running || null);
        } else {
          setActiveJob(null);
        }
      } catch (err) {
        console.error("Failed to fetch global upload status", err);
      }
    };

    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  if (!activeJob) return null;

  const pct = activeJob.total_rows > 0 ? Math.round((activeJob.processed_rows / activeJob.total_rows) * 100) : 0;

  return (
    <div className="fixed bottom-4 right-4 bg-gray-800 border border-gray-700 rounded-lg p-4 shadow-lg flex items-center space-x-4 z-50">
      <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />
      <div>
        <p className="text-sm font-semibold text-white">Importing {activeJob.filename}</p>
        <div className="w-48 bg-gray-700 rounded-full h-2 mt-2">
          <div className="bg-blue-500 h-2 rounded-full transition-all duration-300" style={{ width: `${pct}%` }}></div>
        </div>
        <p className="text-xs text-gray-400 mt-1">{pct}% • {activeJob.processed_rows} / {activeJob.total_rows} rows</p>
      </div>
    </div>
  );
};

export default GlobalUploadStatus;
