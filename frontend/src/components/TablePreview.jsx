import { useState } from 'react';
import ConfidenceViz from './ConfidenceViz';
import { resolveApiUrl } from '../api/client';

export default function TablePreview({ table, pageIdx, onCellEdit }) {
  const {
    table_id: tableId,
    crop_url: cropUrl,
    detection_confidence: detectionConfidence,
    structure_confidence: structureConfidence,
    cells = [],
  } = table;

  const [editingCell, setEditingCell] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const cropSrc = resolveApiUrl(cropUrl);
  const maxRow = Math.max(...cells.map(cell => cell.row + cell.rowspan - 1), 0);

  const startEdit = (cell) => {
    setEditingCell(`${cell.row}-${cell.col}`);
    setEditValue(cell.text);
    setSaveError(null);
  };

  const saveEdit = async (cell) => {
    if (!onCellEdit) return;

    setIsSaving(true);
    setSaveError(null);
    try {
      await onCellEdit({
        page: pageIdx,
        table_id: tableId,
        row: cell.row,
        col: cell.col,
        text: editValue,
      });
      setEditingCell(null);
    } catch (error) {
      setSaveError(error.message || 'Failed to save the edit.');
    } finally {
      setIsSaving(false);
    }
  };

  const cancelEdit = () => {
    if (isSaving) return;
    setEditingCell(null);
    setSaveError(null);
  };

  return (
    <div className="glass-card animate-fadeIn" style={{ marginBottom: '1.5rem' }}>
      <div className="table-preview-layout">
        <div className="table-crop-panel">
          <div className="flex items-center justify-between gap-2">
            <h3>Table {tableId + 1}</h3>
            <span className="badge badge-info">Page {pageIdx + 1}</span>
          </div>

          {cropSrc ? (
            <div className="table-crop-frame">
              <img src={cropSrc} alt={`Table ${tableId + 1} crop`} className="table-crop-image" />
            </div>
          ) : (
            <div className="empty-state" style={{ minHeight: 180 }}>
              <p>Table crop preview is not available.</p>
            </div>
          )}

          <div className="stack-sm">
            <ConfidenceViz label="Detection" confidence={detectionConfidence} />
            <ConfidenceViz
              label="Structure"
              confidence={structureConfidence?.overall ?? null}
              details={[
                { label: 'Rows', value: structureConfidence?.rows_avg ?? null },
                { label: 'Cols', value: structureConfidence?.cols_avg ?? null },
                { label: 'Spans', value: structureConfidence?.spans_avg ?? null },
              ]}
            />
          </div>
        </div>

        <div className="table-grid-panel">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h4 style={{ marginBottom: '0.25rem' }}>Editable Table Grid</h4>
              <p style={{ fontSize: '0.85rem' }}>
                Double-click a cell to correct OCR text before exporting the CSV.
              </p>
            </div>
            <span className="badge badge-success">{cells.length} cells</span>
          </div>

          <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
            <table className="data-table">
              <tbody>
                {Array.from({ length: maxRow + 1 }, (_, ri) => (
                  <tr key={ri}>
                    {cells
                      .filter(cell => cell.row === ri)
                      .sort((a, b) => a.col - b.col)
                      .map(cell => {
                        const key = `${cell.row}-${cell.col}`;
                        const isEditing = editingCell === key;
                        return (
                          <td
                            key={key}
                            rowSpan={cell.rowspan > 1 ? cell.rowspan : undefined}
                            colSpan={cell.colspan > 1 ? cell.colspan : undefined}
                            onDoubleClick={() => !isSaving && startEdit(cell)}
                            style={{
                              cursor: isSaving ? 'progress' : 'pointer',
                              background: isEditing ? 'rgba(99, 102, 241, 0.1)' : undefined,
                              minWidth: 72,
                              verticalAlign: 'top',
                            }}
                            title="Double-click to edit"
                          >
                            {isEditing ? (
                              <div className="stack-sm">
                                <input
                                  value={editValue}
                                  onChange={event => setEditValue(event.target.value)}
                                  onKeyDown={event => {
                                    if (event.key === 'Enter') {
                                      void saveEdit(cell);
                                    }
                                    if (event.key === 'Escape') {
                                      cancelEdit();
                                    }
                                  }}
                                  autoFocus
                                  disabled={isSaving}
                                  style={{ width: '100%', fontSize: '0.85rem' }}
                                />
                                <div className="flex items-center gap-1">
                                  <button
                                    className="btn btn-success"
                                    style={{ padding: '0.3rem 0.5rem', fontSize: '0.75rem' }}
                                    onClick={() => void saveEdit(cell)}
                                    disabled={isSaving}
                                  >
                                    Save
                                  </button>
                                  <button
                                    className="btn btn-secondary"
                                    style={{ padding: '0.3rem 0.5rem', fontSize: '0.75rem' }}
                                    onClick={cancelEdit}
                                    disabled={isSaving}
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <span style={{ fontSize: '0.85rem' }}>{cell.text || '—'}</span>
                            )}
                          </td>
                        );
                      })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {saveError && (
            <p style={{ fontSize: '0.8rem', color: 'var(--danger)', marginTop: '0.75rem' }}>
              {saveError}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
