function formatRelativeTime(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function StatusDot({ status }) {
  const color =
    status === 'completed' ? 'var(--success)' :
    status === 'error'     ? 'var(--danger)'  :
                             'var(--warning)';
  return (
    <span style={{
      display: 'inline-block',
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: color,
      flexShrink: 0,
    }} />
  );
}

function HistoryIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  );
}

export default function JobHistory({ history, activeJobId, onLoad, onClear, loading }) {
  if (history.length === 0) return null;

  return (
    <div className="glass-card animate-fadeIn" style={{ marginTop: '1.25rem' }}>
      <div className="flex items-center justify-between gap-2" style={{ marginBottom: '0.75rem' }}>
        <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <HistoryIcon />
          <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Job History
          </span>
          <span className="badge badge-info">{history.length}</span>
        </div>
        <button
          className="btn btn-secondary"
          style={{ fontSize: '0.72rem', padding: '0.25rem 0.65rem' }}
          onClick={onClear}
        >
          Clear all
        </button>
      </div>

      <div className="stack-xs">
        {history.map(job => {
          const isActive = job.job_id === activeJobId;
          return (
            <button
              key={job.job_id}
              className="history-row"
              data-active={isActive}
              onClick={() => onLoad(job.job_id)}
              disabled={loading}
              title={job.filename}
            >
              <div className="flex items-center gap-2" style={{ minWidth: 0, flex: 1 }}>
                <StatusDot status={job.status} />
                <div className="history-row-info">
                  <span className="history-filename">{job.filename || job.job_id}</span>
                  <span className="history-meta">
                    {formatRelativeTime(job.finished_at || job.started_at)}
                    {job.total_latency_ms ? ` · ${job.total_latency_ms}ms` : ''}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1" style={{ flexShrink: 0 }}>
                {isActive && (
                  <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Viewing</span>
                )}
                <span className={`badge ${
                  job.status === 'completed' ? 'badge-success' :
                  job.status === 'error'     ? 'badge-danger'  :
                                               'badge-warning'
                }`} style={{ fontSize: '0.65rem' }}>
                  {job.status}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
