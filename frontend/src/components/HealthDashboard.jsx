import { startTransition, useEffect, useEffectEvent, useState } from 'react';
import { getHealth } from '../api/client';

function formatStageLabel(stage) {
  return stage
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export default function HealthDashboard() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  const loadHealth = useEffectEvent(async () => {
    try {
      const data = await getHealth();
      startTransition(() => {
        setHealth(data);
        setError(null);
      });
    } catch (fetchError) {
      startTransition(() => {
        setError(fetchError.message);
      });
    }
  });

  useEffect(() => {
    const run = () => {
      void loadHealth();
    };

    run();
    const interval = setInterval(run, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="glass-card animate-fadeIn" style={{ borderLeft: '3px solid var(--danger)' }}>
        <h3>Backend Offline</h3>
        <p className="mt-1" style={{ fontSize: '0.85rem' }}>{error}</p>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="glass-card animate-fadeIn text-center" style={{ padding: '2rem' }}>
        <div className="spinner" style={{ margin: '0 auto 1rem' }} />
        <p>Loading health data...</p>
      </div>
    );
  }

  const stageEntries = Object.entries(health.stage_average_ms || {});
  const maxStageValue = Math.max(1, ...stageEntries.map(([, value]) => value || 0));

  return (
    <div className="animate-fadeIn stack-md">
      <div>
        <h2 style={{ marginBottom: '0.5rem' }}>System Health</h2>
        <p>Live backend status, rolling stage latency, and the latest processed jobs.</p>
      </div>

      <div className="health-grid">
        <div className="glass-card metric-card">
          <p className="metric-label">Status</p>
          <span className={`badge ${health.models_loaded ? 'badge-success' : 'badge-warning'}`}>
            {health.models_loaded ? 'Models Loaded' : 'Loading Models'}
          </span>
        </div>

        <div className="glass-card metric-card">
          <p className="metric-label">Device</p>
          <h3>{health.device}</h3>
        </div>

        <div className="glass-card metric-card">
          <p className="metric-label">Total Requests</p>
          <h3>{health.total_requests}</h3>
        </div>

        <div className="glass-card metric-card">
          <p className="metric-label">Success Rate</p>
          <h3>{health.success_rate}%</h3>
          <p style={{ fontSize: '0.75rem' }}>
            {health.successful_requests} success • {health.failed_requests} failed
          </p>
        </div>

        <div className="glass-card metric-card">
          <p className="metric-label">Average Latency</p>
          <h3>{health.average_latency_ms} ms</h3>
        </div>
      </div>

      <div className="glass-card">
        <div className="flex items-center justify-between gap-2" style={{ marginBottom: '1rem', flexWrap: 'wrap' }}>
          <h3>Average Stage Timings</h3>
          <span className="badge badge-info">Rolling in-memory metrics</span>
        </div>

        <div className="stack-sm">
          {stageEntries.map(([stage, value]) => (
            <div key={stage} className="stage-row">
              <div className="stage-row-header">
                <span>{formatStageLabel(stage)}</span>
                <strong>{value} ms</strong>
              </div>
              <div className="confidence-bar">
                <div
                  className="confidence-bar-fill confidence-high"
                  style={{ width: `${Math.max(8, (value / maxStageValue) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card">
        <div className="flex items-center justify-between gap-2" style={{ marginBottom: '1rem', flexWrap: 'wrap' }}>
          <h3>Recent Jobs</h3>
          <span className="badge badge-info">{health.recent_jobs.length} tracked</span>
        </div>

        {health.recent_jobs.length === 0 ? (
          <div className="empty-state">
            <p>No completed jobs have been recorded yet.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table recent-jobs-table">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>Started</th>
                  <th>Finished</th>
                </tr>
              </thead>
              <tbody>
                {health.recent_jobs.map(job => (
                  <tr key={job.job_id}>
                    <td>
                      <div className="stack-xs">
                        <strong style={{ fontSize: '0.85rem' }}>{job.filename || job.job_id}</strong>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{job.job_id}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${job.status === 'completed' ? 'badge-success' : 'badge-danger'}`}>
                        {job.status}
                      </span>
                    </td>
                    <td>{job.total_latency_ms} ms</td>
                    <td>{job.started_at ? new Date(job.started_at).toLocaleString() : '—'}</td>
                    <td>{job.finished_at ? new Date(job.finished_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
