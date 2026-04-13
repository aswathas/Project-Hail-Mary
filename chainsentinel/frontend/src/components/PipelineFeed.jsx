import React, { useEffect, useRef } from 'react';
import './PipelineFeed.css';

const SEVERITY_CLASS = {
  ok: 'feed__log--ok',
  info: 'feed__log--info',
  warn: 'feed__log--warn',
  high: 'feed__log--high',
  crit: 'feed__log--crit',
  error: 'feed__log--error',
};

export function PipelineFeed({ logs, stats }) {
  const feedEndRef = useRef(null);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Group logs by phase for headers
  let currentPhase = null;

  return (
    <div className="feed">
      {/* Stats Bar */}
      <div className="feed__stats">
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.blocks}</span>
          <span className="feed__stat-label">Blocks</span>
        </div>
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.txs}</span>
          <span className="feed__stat-label">Transactions</span>
        </div>
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.signals}</span>
          <span className="feed__stat-label">Signals</span>
        </div>
        <div className="feed__stat">
          <span className="feed__stat-value">{stats.indexed}</span>
          <span className="feed__stat-label">Indexed</span>
        </div>
      </div>

      {/* Log Stream */}
      <div className="feed__logs">
        {logs.map((log, i) => {
          const showPhaseHeader = log.phase !== currentPhase;
          currentPhase = log.phase;

          return (
            <React.Fragment key={i}>
              {showPhaseHeader && (
                <div className="feed__phase-header">{log.phase}</div>
              )}
              <div className={`feed__log ${SEVERITY_CLASS[log.severity] || ''}`}>
                <span className="feed__log-ts mono">{log.ts}</span>
                <span className="feed__log-msg">{log.msg}</span>
              </div>
            </React.Fragment>
          );
        })}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
