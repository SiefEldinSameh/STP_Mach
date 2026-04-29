const STAGES = [
  { key: 'queued',           label: 'Queued',     short: '⏳' },
  { key: 'loading',          label: 'Preparing',  short: '⚙' },
  { key: 'table_detection',  label: 'Detection',  short: '🔍' },
  { key: 'table_structure',  label: 'Structure',  short: '⊞' },
  { key: 'ocr',              label: 'OCR',        short: 'T' },
  { key: 'finalizing',       label: 'Finalizing', short: '📦' },
];

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2 6 5 9 10 3" />
    </svg>
  );
}

function PipelineStepper({ progressStage }) {
  const activeIdx = STAGES.findIndex(s => s.key === progressStage);

  return (
    <div className="stepper" style={{ marginTop: '1.25rem', marginBottom: '0.5rem' }}>
      {STAGES.map((stage, i) => {
        const isDone   = activeIdx > i;
        const isActive = activeIdx === i;
        let cls = 'stepper-step';
        if (isDone)   cls += ' done';
        if (isActive) cls += ' active';

        return (
          <div key={stage.key} className={cls}>
            <div className="stepper-dot">
              {isDone ? <CheckIcon /> : stage.short}
            </div>
            <div className="stepper-label">{stage.label}</div>
          </div>
        );
      })}
    </div>
  );
}

export default function ProcessingStatus({ status, progressStage, error }) {
  if (status === 'idle') return null;

  return (
    <div className="glass-card animate-fadeIn mt-3" style={{ textAlign: 'center', padding: '2rem' }}>
      {status === 'uploading' && (
        <>
          <div className="spinner" style={{ margin: '0 auto 1rem' }} />
          <h3>Uploading</h3>
          <p className="mt-1" style={{ fontSize: '0.875rem' }}>Sending your file to the server…</p>
        </>
      )}

      {status === 'processing' && (
        <>
          <div className="spinner" style={{ margin: '0 auto 0.75rem' }} />
          <h3>Processing</h3>
          <p style={{ fontSize: '0.875rem', marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
            Running the table extraction pipeline
          </p>
          <PipelineStepper progressStage={progressStage} />
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
            Large PDFs and low-resolution files can take a little longer.
          </p>
        </>
      )}

      {status === 'error' && (
        <>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            background: 'rgba(239, 68, 68, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem',
          }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </div>
          <h3 style={{ color: 'var(--danger)' }}>Processing Failed</h3>
          <p className="mt-1" style={{ fontSize: '0.875rem' }}>{error || 'Something went wrong.'}</p>
        </>
      )}

      {status === 'completed' && (
        <>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            background: 'rgba(16, 185, 129, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem',
          }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <h3 style={{ color: 'var(--success)' }}>Complete</h3>
          <p className="mt-1" style={{ fontSize: '0.875rem' }}>
            Review the extracted tables below, edit cells if needed, then export.
          </p>
        </>
      )}
    </div>
  );
}
