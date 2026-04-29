import { useCallback, useState } from 'react';

const STORAGE_KEY = 'tableextract_job_history';
const MAX_ENTRIES = 20;

function readStorage() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function writeStorage(entries) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

export function useJobHistory() {
  const [history, setHistory] = useState(readStorage);

  const addJob = useCallback((entry) => {
    setHistory(prev => {
      const without = prev.filter(j => j.job_id !== entry.job_id);
      const next = [entry, ...without].slice(0, MAX_ENTRIES);
      writeStorage(next);
      return next;
    });
  }, []);

  const updateJob = useCallback((job_id, updates) => {
    setHistory(prev => {
      const next = prev.map(j => j.job_id === job_id ? { ...j, ...updates } : j);
      writeStorage(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    writeStorage([]);
    setHistory([]);
  }, []);

  return { history, addJob, updateJob, clearHistory };
}
