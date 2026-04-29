import { useCallback, useState } from 'react';

function UploadIcon() {
  return (
    <svg
      className="upload-icon"
      width="52"
      height="52"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 16.5A4.5 4.5 0 0 1 7.5 8h.5a6 6 0 0 1 11.57 1.5A4 4 0 0 1 21 13.5v.5A3.5 3.5 0 0 1 17.5 17.5H8" />
      <polyline points="12 13 12 21" />
      <polyline points="9 17 12 13 15 17" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function formatSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileUpload({ onUpload, disabled }) {
  const [dragActive, setDragActive] = useState(false);
  const [fileInfo, setFileInfo] = useState(null);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      setFileInfo({ name: file.name, size: file.size });
      onUpload(file);
    }
  }, [onUpload]);

  const handleChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileInfo({ name: file.name, size: file.size });
      onUpload(file);
    }
  }, [onUpload]);

  return (
    <div
      className={`glass-card animate-fadeIn ${dragActive ? 'drag-active' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={() => !disabled && document.getElementById('file-input').click()}
      style={{
        textAlign: 'center',
        padding: '2.75rem 2rem',
        border: dragActive
          ? '2px dashed var(--accent-primary)'
          : '2px dashed var(--border-glass)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        transition: 'var(--transition)',
        background: dragActive
          ? 'rgba(99, 102, 241, 0.06)'
          : undefined,
      }}
    >
      <input
        id="file-input"
        type="file"
        accept=".jpg,.jpeg,.png,.tif,.tiff,.pdf"
        onChange={handleChange}
        disabled={disabled}
        style={{ display: 'none' }}
      />

      <div style={{ marginBottom: '1rem' }}>
        <UploadIcon />
      </div>

      {fileInfo ? (
        <div style={{ marginBottom: '0.75rem' }}>
          <div className="file-chip" style={{ margin: '0 auto' }}>
            <FileIcon />
            <span>{fileInfo.name}</span>
            {fileInfo.size > 0 && (
              <span style={{ opacity: 0.7 }}>• {formatSize(fileInfo.size)}</span>
            )}
          </div>
        </div>
      ) : (
        <>
          <h3 style={{ marginBottom: '0.4rem', fontSize: '1.05rem' }}>
            {dragActive ? 'Drop to upload' : 'Drop your file here'}
          </h3>
          <p style={{ fontSize: '0.85rem', marginBottom: '1.25rem' }}>
            or click to browse
          </p>
        </>
      )}

      {!fileInfo && (
        <div className="flex items-center justify-center gap-1" style={{ flexWrap: 'wrap' }}>
          {['PDF', 'JPG', 'PNG', 'TIFF'].map(fmt => (
            <span key={fmt} className="badge badge-info">{fmt}</span>
          ))}
        </div>
      )}

      {fileInfo && !disabled && (
        <button
          className="btn btn-secondary mt-2"
          style={{ fontSize: '0.8rem', padding: '0.4rem 1rem' }}
          onClick={e => { e.stopPropagation(); setFileInfo(null); }}
        >
          Choose different file
        </button>
      )}
    </div>
  );
}
