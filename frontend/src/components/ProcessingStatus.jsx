import { useEffect, useState } from 'react';
import { SUBSCRIBE_URL } from '../api/client';

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
  const [promoDismissed, setPromoDismissed] = useState(false);

  useEffect(() => {
    if (status === 'uploading') {
      setPromoDismissed(false);
    }
  }, [status]);

  if (status === 'idle') return null;

  const showPromoBanner = (status === 'uploading' || status === 'processing') && !promoDismissed;

  return (
    <div className="glass-card animate-fadeIn mt-3" style={{ textAlign: 'center', padding: '2rem' }}>
      {showPromoBanner && (
        <div
          className="flex items-start justify-between gap-2"
          style={{
            marginBottom: '1rem',
            padding: '0.85rem 1rem',
            borderRadius: '12px',
            border: '1px solid var(--border-glass)',
            background: 'linear-gradient(135deg, rgba(125, 211, 252, 0.08) 0%, rgba(167, 139, 250, 0.06) 100%)',
            textAlign: 'left',
            boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)',
          }}
        >
          <div className="flex items-start gap-2" style={{ minWidth: 0 }}>
            <span aria-hidden style={{ flexShrink: 0, fontSize: '1.15rem', lineHeight: 1 }}>
              ✨
            </span>
            <div>
              <div
                style={{
                  fontWeight: 700,
                  fontSize: '0.88rem',
                  marginBottom: '0.4rem',
                  letterSpacing: '-0.01em',
                  background: 'var(--accent-gradient)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}
              >
                Unlock faster runs — up to 10×
              </div>
              <p style={{ margin: 0, lineHeight: 1.5, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Subscribe with us for marketing updates and tips to speed up your next extraction.
                {SUBSCRIBE_URL ? (
                  <>
                    {' '}
                    <a href={SUBSCRIBE_URL} target="_blank" rel="noreferrer noopener" className="btn btn-primary" style={{ fontSize: '0.78rem', padding: '0.2rem 0.65rem', marginLeft: '0.35rem', display: 'inline-block', verticalAlign: 'middle' }}>
                      Subscribe
                    </a>
                  </>
                ) : null}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setPromoDismissed(true)}
            style={{ fontSize: '0.72rem', padding: '0.25rem 0.55rem', flexShrink: 0, opacity: 0.85 }}
            aria-label="Dismiss offer"
          >
            Dismiss
          </button>
        </div>
      )}

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
