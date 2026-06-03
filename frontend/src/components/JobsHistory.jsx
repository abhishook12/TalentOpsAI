import React, { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import api from '../services/api'

export default function JobsHistory() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await api.get('/upload/jobs');
        setJobs(Array.isArray(res.data) ? res.data : []);
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

  if (loading) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>Loading import history…</div>;

  const toneFor = (status) => {
    if (status === 'completed') return 'badge-green'
    if (status === 'failed') return 'badge-red'
    if (status === 'processing') return 'badge-blue'
    if (status === 'queued') return 'badge-amber'
    return 'badge-gray'
  }

  return (
    <div className="card" style={{ padding: 20 }}>
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
          {jobs.map(j => {
            const errorRows = j.error_rows ?? j.error_count ?? 0;
            const skippedRows = j.skipped_rows ?? 0;
            const insertedRows = j.inserted_rows ?? 0;
            const pct = j.total_rows ? Math.round(((insertedRows + skippedRows + errorRows) / j.total_rows) * 100) : 0;
            const successRate = j.total_rows ? Math.round((insertedRows / j.total_rows) * 1000) / 10 : null

            const handleDownloadErrors = async () => {
              try {
                alert('Rejected row export is not available on the current backend yet.');
              } catch (err) {
                console.error('Error downloading report', err);
              }
            };

            const handleRetry = async () => {
              try {
                alert('Retry is not supported yet for the new Smart Import Engine.');
              } catch (err) {
                alert('Could not retry this job.');
              }
            };

            return (
              <div key={j.job_id} className="card" style={{ padding: 16, background: 'var(--panel-bg)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                    <div style={{ width: 34, height: 34, borderRadius: 10, background: 'var(--accent-bg)', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
                      <i className="ti ti-file-spreadsheet" style={{ color: 'var(--accent)' }} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={j.filename}>
                        {j.filename}
                      </div>
                      <div style={{ marginTop: 3, fontSize: 11, color: 'var(--text-muted)' }}>
                        {j.started_at ? `Imported ${formatDistanceToNow(new Date(j.started_at + 'Z'), { addSuffix: true })}` : '—'}
                      </div>
                    </div>
                  </div>
                  <span className={`badge ${toneFor(j.status)}`} style={{ textTransform: 'uppercase' }}>{j.status}</span>
                </div>

                <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Rows</div>
                    <div style={{ marginTop: 6, fontSize: 16, fontWeight: 900, color: 'var(--text-primary)' }}>{(j.total_rows || 0).toLocaleString()}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Success rate</div>
                    <div style={{ marginTop: 6, fontSize: 16, fontWeight: 900, color: 'var(--text-primary)' }}>{successRate === null ? '—' : `${successRate}%`}</div>
                  </div>
                </div>

                <div style={{ marginTop: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Progress</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{pct}%</div>
                  </div>
                  <div style={{ height: 6, background: 'var(--card-border)', borderRadius: 999, overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, var(--accent), #185FA5)', borderRadius: 999, transition: 'width 0.3s' }} />
                  </div>
                </div>

                <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-muted)' }} title={j.job_id}>
                    {j.job_id.substring(0, 8)}…
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    {(errorRows > 0 || j.status === 'failed' || j.status === 'completed') && (
                      <button
                        onClick={handleDownloadErrors}
                        title="Download Error Report"
                        style={{ border: '1px solid rgba(248,81,73,0.25)', background: 'rgba(248,81,73,0.08)', color: '#f85149', padding: '7px 10px', borderRadius: 10, cursor: 'pointer' }}
                      >
                        <i className="ti ti-download" />
                      </button>
                    )}
                    {j.status === 'failed' && (
                      <button
                        onClick={handleRetry}
                        title="Retry Job"
                        style={{ border: '1px solid rgba(59,130,246,0.25)', background: 'rgba(59,130,246,0.10)', color: '#3b82f6', padding: '7px 10px', borderRadius: 10, cursor: 'pointer' }}
                      >
                        <i className="ti ti-reload" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
