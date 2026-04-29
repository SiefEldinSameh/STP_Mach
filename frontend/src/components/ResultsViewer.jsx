import TablePreview from './TablePreview';
import { getCropsUrl, getCsvUrl } from '../api/client';

export default function ResultsViewer({ jobData, onCellEdit }) {
  if (!jobData?.pages) return null;

  const { job_id: jobId, filename, pages, total_latency_ms: totalLatencyMs } = jobData;
  const totalTables = pages.reduce((sum, page) => sum + (page.tables?.length || 0), 0);
  const totalCells = pages.reduce(
    (sum, page) => sum + (page.tables?.reduce((tableSum, table) => tableSum + (table.cells?.length || 0), 0) || 0),
    0
  );
  const pageErrors = pages.filter(page => page.status === 'error').length;
  const hasTables = totalTables > 0;

  return (
    <div className="animate-fadeIn mt-3">
      <div className="glass-card mb-2">
        <div className="flex items-center justify-between gap-2" style={{ marginBottom: '1rem', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ marginBottom: '0.2rem' }}>Results</h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{filename}</p>
          </div>
          <div className="actions-row">
            {hasTables ? (
              <>
                <a href={getCsvUrl(jobId, 'matrix')} download className="btn btn-primary" style={{ fontSize: '0.85rem', padding: '0.5rem 1.1rem' }}>
                  Download CSV
                </a>
                <a href={getCropsUrl(jobId)} download className="btn btn-secondary" style={{ fontSize: '0.85rem', padding: '0.5rem 1.1rem' }}>
                  Download Crops
                </a>
              </>
            ) : (
              <span className="badge badge-warning">No tables detected</span>
            )}
          </div>
        </div>

        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-value">{pages.length}</div>
            <div className="stat-label">Pages</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{totalTables}</div>
            <div className="stat-label">Tables</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{totalCells}</div>
            <div className="stat-label">Cells</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: '1.2rem' }}>{totalLatencyMs}ms</div>
            <div className="stat-label">Latency</div>
          </div>
        </div>

        {pageErrors > 0 && (
          <p style={{ fontSize: '0.8rem', color: 'var(--warning)', marginTop: '0.75rem' }}>
            {pageErrors} page{pageErrors !== 1 ? 's' : ''} had processing errors — successful pages are still available.
          </p>
        )}
      </div>

      {!hasTables && (
        <div className="glass-card empty-state" style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ marginBottom: '0.5rem' }}>No tables detected</h3>
          <p>
            The upload completed successfully, but the detector did not find any table regions in this file.
          </p>
        </div>
      )}

      {pages.map(page => (
        <div key={page.page}>
          {(pages.length > 1 || page.status !== 'success' || (page.tables?.length || 0) === 0) && (
            <div className="flex items-center gap-2" style={{ margin: '1.5rem 0 0.75rem', flexWrap: 'wrap' }}>
              <h3>Page {page.page + 1}</h3>
              {page.status === 'error' && <span className="badge badge-danger">Error</span>}
              {page.status === 'success' && (page.tables?.length || 0) === 0 && (
                <span className="badge badge-warning">No tables</span>
              )}
              <span className="badge badge-info">{page.latency_ms}ms</span>
            </div>
          )}

          {page.status === 'error' && (
            <div className="glass-card" style={{ borderLeft: '3px solid var(--danger)', marginBottom: '1rem' }}>
              <p style={{ color: 'var(--danger)' }}>{page.error}</p>
            </div>
          )}

          {page.status === 'success' && (page.tables?.length || 0) === 0 && (
            <div className="glass-card empty-state" style={{ marginBottom: '1rem' }}>
              <p>No table structures were extracted from this page.</p>
            </div>
          )}

          {page.tables?.map(table => (
            <TablePreview
              key={`${page.page}-${table.table_id}`}
              table={table}
              pageIdx={page.page}
              onCellEdit={onCellEdit}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
