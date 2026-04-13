import { useState, useCallback, useRef } from 'react';

/**
 * useAnalysis — SSE connection + state machine for pipeline runs.
 *
 * States: idle -> running -> complete
 *
 * During 'running': receives SSE events, updates logs and stats.
 * On 'complete': stores investigation ID and final stats.
 */
export function useAnalysis() {
  const [state, setState] = useState('idle'); // idle | running | complete
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({ blocks: 0, txs: 0, signals: 0, indexed: 0 });
  const [investigationId, setInvestigationId] = useState(null);
  const eventSourceRef = useRef(null);

  const addLog = useCallback((logEntry) => {
    setLogs((prev) => [...prev, logEntry]);

    // Update stats from log if it contains stat info
    if (logEntry.stats) {
      setStats(logEntry.stats);
    }
  }, []);

  const startRun = useCallback((config) => {
    setState('running');
    setLogs([]);
    setStats({ blocks: 0, txs: 0, signals: 0, indexed: 0 });
    setInvestigationId(config.investigationId || null);

    // SSE connection would be established here by the component
    // using startAnalysis from api/pipeline.js
  }, []);

  const completeRun = useCallback((data) => {
    setState('complete');
    if (data.investigationId) {
      setInvestigationId(data.investigationId);
    }
    if (data.stats) {
      setStats(data.stats);
    }

    // Close SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    setState('idle');
    setLogs([]);
    setStats({ blocks: 0, txs: 0, signals: 0, indexed: 0 });
    setInvestigationId(null);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const restoreCase = useCallback((caseData) => {
    setState('complete');
    setInvestigationId(caseData.investigationId);
    setStats(caseData.stats || { blocks: 0, txs: 0, signals: 0, indexed: 0 });
    setLogs(caseData.logs || []);
  }, []);

  return {
    state,
    logs,
    stats,
    investigationId,
    eventSourceRef,
    addLog,
    startRun,
    completeRun,
    reset,
    restoreCase,
  };
}
