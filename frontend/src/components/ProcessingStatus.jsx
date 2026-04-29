const STAGE_COPY = {
  queued: {
    label: 'Queued',
    detail: 'Your file is waiting for the background worker.',
  },
  loading: {
    label: 'Preparing',
    detail: 'Setting up the pipeline and document workspace.',
  },
  table_detection: {
    label: 'Detecting Tables',
    detail: 'Scanning the document to find candidate tables.',
  },
  table_structure: {
    label: 'Recognizing Structure',
    detail: 'Recovering rows, columns, and span geometry.',
  },
  ocr: {
    label: 'Running OCR',
    detail: 'Reading cell text from the extracted table regions.',
  },
  finalizing: {
    label: 'Finalizing',
    detail: 'Saving crops and packaging the result payload.',
  },
};

export default function ProcessingStatus({ status, progressStage, error }) {
  if (status === 'idle') return null;

  const stageInfo = STAGE_COPY[progressStage] || {
    label: 'Processing',
    detail: 'The pipeline is working through your document.',
  };

  return (
    <div className="glass-card animate-fadeIn mt-3" style={{ textAlign: 'center', padding: '2rem' }}>
      {status === 'uploading' && (
        <>
          <div className="spinner" style={{ margin: '0 auto 1rem' }} />
          <h3>Uploading...</h3>
          <p className="mt-1">Sending your file to the server.</p>
        </>
      )}

      {status === 'processing' && (
        <>
          <div className="spinner" style={{ margin: '0 auto 1rem' }} />
          <div className="stack-sm">
            <span className="badge badge-info">{stageInfo.label}</span>
            <h3>Processing...</h3>
          </div>
          <p className="mt-1">{stageInfo.detail}</p>
          <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: 'var(--text-muted)' }}>
            Large PDFs and low-resolution files can take a little longer.
          </p>
        </>
      )}

      {status === 'error' && (
        <>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>✖</div>
          <h3 style={{ color: 'var(--danger)' }}>Error</h3>
          <p className="mt-1">{error || 'Something went wrong.'}</p>
        </>
      )}

      {status === 'completed' && (
        <>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>✓</div>
          <h3 style={{ color: 'var(--success)' }}>Processing Complete</h3>
          <p className="mt-1">Review the extracted tables, edit cells if needed, then download.</p>
        </>
      )}
    </div>
  );
}
