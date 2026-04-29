import { useCallback, useState } from 'react';

export default function FileUpload({ onUpload, disabled }) {
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState('');

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
      setFileName(file.name);
      onUpload(file);
    }
  }, [onUpload]);

  const handleChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
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
      style={{
        textAlign: 'center',
        padding: '3rem 2rem',
        border: dragActive ? '2px dashed var(--accent-primary)' : '2px dashed var(--border-glass)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        transition: 'var(--transition)',
      }}
      onClick={() => !disabled && document.getElementById('file-input').click()}
    >
      <input
        id="file-input"
        type="file"
        accept=".jpg,.jpeg,.png,.tif,.tiff,.pdf"
        onChange={handleChange}
        disabled={disabled}
        style={{ display: 'none' }}
      />
      <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>
        {dragActive ? '📥' : '📄'}
      </div>
      <h3 style={{ marginBottom: '0.5rem' }}>
        {fileName || 'Drop your file here'}
      </h3>
      <p style={{ fontSize: '0.85rem' }}>
        Supports PDF, JPG, PNG, TIFF
      </p>
      {!fileName && (
        <button className="btn btn-primary mt-2" disabled={disabled}>
          Choose File
        </button>
      )}
    </div>
  );
}
