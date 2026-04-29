import { startTransition, useEffect, useEffectEvent, useState } from 'react';
import { getHealth } from '../api/client';

const STAGE_ORDER = ['table_detection', 'table_structure', 'ocr', 'total'];

function formatStageLabel(stage) {
  return stage
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export default function HealthDashboard({ onLoadJob }) {
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

  const stageEntries = Object.entries(health.stage_average_ms || {}).sort(
    (a, b) => {
      const ia = STAGE_ORDER.indexOf(a[0]);
      const ib = STAGE_ORDER.indexOf(b[0]);
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    }
  );
  const maxStageValue = Math.max(1, ...stageEntries.map(([, value]) => value || 0));

  const matrix = health.stage_health_matrix || {};
  const orderedStages = [
    ...STAGE_ORDER.filter(s => matrix[s] != null),
    ...Object.keys(matrix).filter(s => !STAGE_ORDER.includes(s)),
  ];
  const maxAvg = Math.max(1, ...orderedStages.map(s => matrix[s]?.avg_ms || 0));

  return (
    <div className="animate-fadeIn stack-md">
      <div>
        <h2 style={{ marginBottom: '0.5rem' }}>System Health</h2>
        <p>
          Live backend status, stage timing charts and matrix, recent jobs, and{' '}
          <strong>View Results</strong> to open the full extraction on the Extract tab.
        </p>
      </div>

      <div className="health-grid">
        <div className="glass-card metric-card">
          <p className="metric-label">Status</p>
          {health.models_loaded ? (
            <span className="badge badge-success">Models Ready</span>
          ) : health.model_load_error ? (
            <div className="stack-xs">
              <span className="badge badge-danger">Load Failed</span>
              <span style={{ fontSize: '0.68rem', color: 'var(--danger)', wordBreak: 'break-word' }}>
                {health.model_load_error}
              </span>
            </div>
          ) : (
            <span className="badge badge-warning">Loading Models</span>
          )}
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

        <div className="stack-sm" style={{ marginBottom: '1.5rem' }}>
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

        <div
          style={{
            borderTop: '1px solid var(--border-glass)',
            paddingTop: '1.25rem',
            marginTop: '0.25rem',
          }}
        >
          <div className="flex items-center justify-between gap-2" style={{ marginBottom: '0.65rem', flexWrap: 'wrap' }}>
            <h4 style={{ margin: 0, fontSize: '1rem' }}>Stage timing matrix</h4>
            <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>Samples · min · max · P95</span>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.85rem' }}>
            Same stages as above; columns summarize the rolling buffer of per-job stage latencies (ms).
          </p>

          {orderedStages.length === 0 ? (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>No matrix data yet.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table health-matrix-table">
                <thead>
                  <tr>
                    <th>Stage</th>
                    <th>Samples</th>
                    <th>Avg</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>P95</th>
                  </tr>
                </thead>
                <tbody>
                  {orderedStages.map(stage => {
                    const row = matrix[stage];
                    const heat = maxAvg > 0 ? Math.min(1, (row?.avg_ms ?? 0) / maxAvg) : 0;
                    return (
                      <tr key={stage}>
                        <td>
                          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{formatStageLabel(stage)}</span>
                        </td>
                        <td>{row?.sample_count ?? 0}</td>
                        <td
                          style={{
                            background: `rgba(99, 102, 241, ${0.06 + heat * 0.14})`,
                          }}
                        >
                          {row?.sample_count ? row.avg_ms : '—'}
                        </td>
                        <td>{row?.sample_count ? row.min_ms : '—'}</td>
                        <td>{row?.sample_count ? row.max_ms : '—'}</td>
                        <td>{row?.sample_count ? row.p95_ms : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
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
                  {onLoadJob && <th>Results</th>}
                </tr>
              </thead>
              <tbody>
                {health.recent_jobs.map(job => (
                  <tr key={job.job_id}>
                    <td>
                      <div className="stack-xs">
                        <strong style={{ fontSize: '0.85rem' }}>{job.filename || job.job_id}</strong>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{job.job_id}</span>
                        {job.error && (
                          <span style={{ color: 'var(--danger)', fontSize: '0.72rem' }}>{job.error}</span>
                        )}
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
                    {onLoadJob && (
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: '0.72rem', padding: '0.25rem 0.65rem', whiteSpace: 'nowrap' }}
                          disabled={job.status !== 'completed'}
                          title={job.status !== 'completed' ? 'Only completed jobs can be viewed' : 'Open in Extract'}
                          onClick={() => onLoadJob(job)}
                        >
                          View Results
                        </button>
                      </td>
                    )}
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
