import { useEffect, useRef, useState } from 'react';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import ResultsViewer from './components/ResultsViewer';
import HealthDashboard from './components/HealthDashboard';
import JobHistory from './components/JobHistory';
import { useJobHistory } from './hooks/useJobHistory';
import { editResults, getResults, uploadFile } from './api/client';

function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <button
      className="btn btn-secondary"
      onClick={() => setTheme(current => current === 'dark' ? 'light' : 'dark')}
      style={{ padding: '0.5rem 0.75rem', fontSize: '1.1rem' }}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  );
}

function applyCellEditToJobData(jobData, edit) {
  if (!jobData?.pages) return jobData;
  return {
    ...jobData,
    pages: jobData.pages.map(page => {
      if (page.page !== edit.page) return page;
      return {
        ...page,
        tables: (page.tables || []).map(table => {
          if (table.table_id !== edit.table_id) return table;
          return {
            ...table,
            cells: (table.cells || []).map(cell =>
              cell.row === edit.row && cell.col === edit.col
                ? { ...cell, text: edit.text }
                : cell
            ),
          };
        }),
      };
    }),
  };
}

export default function App() {
  const [page, setPage] = useState('home');
  const [status, setStatus] = useState('idle');
  const [progressStage, setProgressStage] = useState(null);
  const [error, setError] = useState(null);
  const [jobData, setJobData] = useState(null);
  const [activeJobId, setActiveJobId] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [uploadKey, setUploadKey] = useState(0);

  const jobIdRef = useRef(null);
  const pollRef = useRef(null);

  const { history, addJob, updateJob, clearHistory } = useJobHistory();

  const clearPolling = () => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => () => clearPolling(), []);

  const schedulePoll = (jobId, delay = 2000) => {
    clearPolling();
    pollRef.current = setTimeout(() => { void pollJob(jobId); }, delay);
  };

  const pollJob = async (jobId) => {
    try {
      const result = await getResults(jobId);

      if (result.status === 'completed') {
        clearPolling();
        setJobData(result);
        setProgressStage('completed');
        setStatus('completed');
        setActiveJobId(jobId);
        updateJob(jobId, {
          status: 'completed',
          finished_at: result.finished_at,
          total_latency_ms: result.total_latency_ms,
        });
        return;
      }

      if (result.status === 'error') {
        clearPolling();
        setError(result.error || 'Processing failed');
        setProgressStage('error');
        setStatus('error');
        updateJob(jobId, { status: 'error', finished_at: result.finished_at });
        return;
      }

      setProgressStage(result.progress_stage || 'processing');
      schedulePoll(jobId);
    } catch {
      schedulePoll(jobId, 2500);
    }
  };

  const handleUpload = async (file) => {
    clearPolling();
    setStatus('uploading');
    setProgressStage('queued');
    setError(null);
    setJobData(null);
    setActiveJobId(null);

    try {
      const { job_id: jobId } = await uploadFile(file);
      jobIdRef.current = jobId;
      setStatus('processing');
      setProgressStage('queued');
      setActiveJobId(jobId);

      const now = new Date().toISOString();
      addJob({
        job_id: jobId,
        filename: file.name,
        status: 'processing',
        started_at: now,
        finished_at: null,
        total_latency_ms: null,
      });

      schedulePoll(jobId, 1200);
    } catch (uploadError) {
      setError(uploadError.message);
      setProgressStage('error');
      setStatus('error');
    }
  };

  const handleCellEdit = async (edit) => {
    if (!jobIdRef.current) return;
    await editResults(jobIdRef.current, [edit]);
    setJobData(current => applyCellEditToJobData(current, edit));
  };

  const loadJobFromHistory = async (jobId) => {
    if (jobId === activeJobId) return;
    clearPolling();
    setHistoryLoading(true);
    setError(null);
    setJobData(null);
    setActiveJobId(null);

    try {
      const result = await getResults(jobId);
      jobIdRef.current = jobId;
      setActiveJobId(jobId);

      if (result.status === 'completed') {
        setJobData(result);
        setStatus('completed');
        setProgressStage('completed');
        updateJob(jobId, {
          status: 'completed',
          finished_at: result.finished_at,
          total_latency_ms: result.total_latency_ms,
        });
      } else if (result.status === 'error') {
        setStatus('error');
        setProgressStage('error');
        setError(result.error || 'Job failed');
        updateJob(jobId, { status: 'error' });
      } else {
        // Still processing — resume polling
        setStatus('processing');
        setProgressStage(result.progress_stage || 'queued');
        schedulePoll(jobId);
      }
    } catch {
      setStatus('error');
      setError('Job not found. The server may have restarted and the result was not saved.');
    } finally {
      setHistoryLoading(false);
    }
  };

  const navigateToJob = (job) => {
    // Ensure the job is in localStorage history (addJob deduplicates by job_id)
    addJob({
      job_id: job.job_id,
      filename: job.filename,
      status: job.status,
      started_at: job.started_at,
      finished_at: job.finished_at,
      total_latency_ms: job.total_latency_ms,
    });
    setPage('home');
    void loadJobFromHistory(job.job_id);
  };

  const resetUpload = () => {
    clearPolling();
    setStatus('idle');
    setProgressStage(null);
    setError(null);
    setJobData(null);
    setActiveJobId(null);
    jobIdRef.current = null;
    setUploadKey(k => k + 1);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          background: 'var(--bg-glass)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--border-glass)',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        <div className="container flex items-center justify-between" style={{ padding: '0.75rem 1.5rem' }}>
          <div className="flex items-center gap-2">
            <div className="logo-mark">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="1" y="1" width="6" height="6" rx="1" fill="white" fillOpacity="0.9"/>
                <rect x="9" y="1" width="6" height="6" rx="1" fill="white" fillOpacity="0.6"/>
                <rect x="1" y="9" width="6" height="6" rx="1" fill="white" fillOpacity="0.6"/>
                <rect x="9" y="9" width="6" height="6" rx="1" fill="white" fillOpacity="0.9"/>
              </svg>
            </div>
            <h1
              style={{
                fontSize: '1.2rem',
                background: 'var(--accent-gradient)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.02em',
              }}
            >
              TableExtract
            </h1>
          </div>

          <nav className="flex items-center gap-2">
            <button
              className={`btn ${page === 'home' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
              onClick={() => setPage('home')}
            >
              Extract
            </button>
            <button
              className={`btn ${page === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
              onClick={() => setPage('dashboard')}
            >
              Health
            </button>
            <ThemeToggle />
          </nav>
        </div>
      </header>

      <main className="container" style={{ flex: 1, padding: '2rem 1.5rem' }}>
        {page === 'home' && (
          <>
            <div style={{ maxWidth: 720, margin: '0 auto' }}>
              <div className="text-center mb-2">
                <h2 style={{ marginBottom: '0.5rem' }}>Extract Tables from Documents</h2>
                <p>
                  Upload an image or PDF to detect tables, recognize structure, run OCR, and
                  export the reconstructed tables.
                </p>
              </div>

              <FileUpload
                key={uploadKey}
                onUpload={handleUpload}
                disabled={status === 'uploading' || status === 'processing' || historyLoading}
              />

              <ProcessingStatus status={status} progressStage={progressStage} error={error} />

              {(status === 'completed' || status === 'error') && (
                <div className="text-center mt-2">
                  <button className="btn btn-secondary" onClick={resetUpload}>
                    Upload Another File
                  </button>
                </div>
              )}

              <JobHistory
                history={history}
                activeJobId={activeJobId}
                onLoad={loadJobFromHistory}
                onClear={clearHistory}
                loading={historyLoading}
              />
            </div>

            {jobData && (
              <div style={{ maxWidth: 1100, margin: '2rem auto 0' }}>
                <ResultsViewer jobData={jobData} onCellEdit={handleCellEdit} />
              </div>
            )}
          </>
        )}

        {page === 'dashboard' && <HealthDashboard onLoadJob={navigateToJob} />}
      </main>

      <footer style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
        MACHATHON 7.0 - Table Extraction Pipeline
      </footer>
    </div>
  );
}
