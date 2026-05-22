import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { formatDistanceToNow } from 'date-fns';

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export default function JobsHistory() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await axios.get(`${API}/upload/jobs`);
        setJobs(res.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
    const int = setInterval(fetchJobs, 5000);
    return () => clearInterval(int);
  }, []);

  if (loading) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>Loading history...</div>;

  return (
    <div className="card" style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: '#185FA518', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className="ti ti-history" style={{ fontSize: 18, color: '#185FA5' }} />
        </div>
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Import History</h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Live status of recent background ETL imports</p>
        </div>
      </div>

      {jobs.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>No recent import jobs found.</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: 12 }}>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Filename</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Inserted</th>
                <th>Failed</th>
                <th>Started</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => {
                const pct = j.total_rows ? Math.round((j.processed_rows / j.total_rows) * 100) : 0;
                
                const handleDownloadErrors = async () => {
                  try {
                    const res = await axios.get(`${API}/upload/jobs/${j.job_id}`);
                    const errs = res.data.errors;
                    if (!errs || !errs.length) {
                      alert('No detailed errors available for this job.');
                      return;
                    }
                    // Create CSV of errors
                    const csvContent = 'data:text/csv;charset=utf-8,Row,Reason\n' 
                      + errs.map(e => `${e.row},"${(e.reason || '').replace(/"/g, '""')}"`).join('\n');
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement('a');
                    link.setAttribute('href', encodedUri);
                    link.setAttribute('download', `errors_${j.job_id}.csv`);
                    document.body.appendChild(link);
                    link.click();
                  } catch (err) {
                    console.error('Error downloading report', err);
                  }
                };

                const handleRetry = async () => {
                  try {
                    await axios.post(`${API}/upload/jobs/${j.job_id}/retry`);
                    alert('Job retry has been queued successfully.');
                  } catch (err) {
                    alert('Could not retry this job. The original file may have been deleted.');
                  }
                };

                return (
                  <tr key={j.job_id}>
                    <td style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                      {j.job_id.substring(0, 8)}...
                    </td>
                    <td style={{ fontWeight: 500, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={j.filename}>{j.filename}</td>
                    <td>
                      <span className={`badge ${j.status === 'completed' ? 'badge-green' : j.status === 'failed' ? 'badge-red' : j.status === 'processing' ? 'badge-blue' : 'badge-gray'}`}>
                        {j.status}
                      </span>
                    </td>
                    <td style={{ minWidth: 100 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ flex: 1, height: 4, background: 'var(--card-border)', borderRadius: 2 }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', borderRadius: 2, transition: 'width 0.3s' }}></div>
                        </div>
                        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{pct}%</span>
                      </div>
                    </td>
                    <td style={{ color: '#3fb950', fontWeight: 600 }}>{j.inserted_rows}</td>
                    <td style={{ color: j.error_count > 0 ? '#f85149' : 'var(--text-muted)', fontWeight: j.error_count > 0 ? 600 : 400 }}>
                      {j.error_count}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                      {j.started_at ? formatDistanceToNow(new Date(j.started_at + 'Z'), { addSuffix: true }) : '-'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {(j.error_count > 0 || j.status === 'failed') && (
                          <button onClick={handleDownloadErrors} title="Download Error Report" style={{ background: 'rgba(196,57,74,0.1)', color: '#C4394A', border: 'none', padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}>
                            <i className="ti ti-download" />
                          </button>
                        )}
                        {j.status === 'failed' && (
                          <button onClick={handleRetry} title="Retry Job" style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: 'none', padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}>
                            <i className="ti ti-reload" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
