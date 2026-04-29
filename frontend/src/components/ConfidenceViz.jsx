function formatPercent(confidence) {
  if (confidence == null) return 'N/A';
  return `${Math.round(confidence * 100)}%`;
}

export default function ConfidenceViz({ label, confidence, details = [] }) {
  const pct = confidence == null ? null : Math.round(confidence * 100);
  let cls = 'confidence-high';
  if (pct !== null && pct < 50) cls = 'confidence-low';
  else if (pct !== null && pct < 75) cls = 'confidence-mid';

  return (
    <div className="confidence-card">
      <div className="flex items-center justify-between gap-2">
        <span className="metric-label">{label}</span>
        <strong style={{ fontSize: '0.9rem' }}>{formatPercent(confidence)}</strong>
      </div>

      <div className="confidence-bar" style={{ marginTop: '0.45rem' }}>
        {pct !== null && (
          <div className={`confidence-bar-fill ${cls}`} style={{ width: `${pct}%` }} />
        )}
      </div>

      {details.length > 0 && (
        <div className="confidence-breakdown">
          {details.map(detail => (
            <span key={detail.label} className="badge badge-info">
              {detail.label}: {formatPercent(detail.value)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
