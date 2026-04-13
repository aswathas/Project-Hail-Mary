import React from 'react';
import './Sidebar.css';

const MODES = [
  { key: 'watch', label: 'Watch', desc: 'Live block monitoring' },
  { key: 'range', label: 'Range', desc: 'Block range analysis' },
  { key: 'tx', label: 'Tx Analysis', desc: 'Single transaction' },
  { key: 'wallet', label: 'Wallet Hunt', desc: 'Trace wallet activity' },
];

export function Sidebar({
  config,
  onConfigChange,
  health,
  mode,
  onModeChange,
  target,
  onTargetChange,
  onRun,
  isRunning,
  savedCases,
  onRestoreCase,
}) {
  const allConnected = health.rpc && health.es;
  const canRun = allConnected && !isRunning;

  return (
    <div className="sidebar">
      {/* Connection Config */}
      <div className="sidebar__section">
        <h3 className="sidebar__heading">Connection</h3>
        <div className="sidebar__field">
          <label className="sidebar__label">
            <span className={`status-dot ${health.rpc ? 'status-dot--ok' : 'status-dot--error'}`} />
            RPC
          </label>
          <input
            className="input-field"
            placeholder="RPC URL"
            value={config.rpcUrl}
            onChange={(e) => onConfigChange({ ...config, rpcUrl: e.target.value })}
          />
        </div>
        <div className="sidebar__field">
          <label className="sidebar__label">
            <span className={`status-dot ${health.es ? 'status-dot--ok' : 'status-dot--error'}`} />
            ES
          </label>
          <input
            className="input-field"
            placeholder="ES URL"
            value={config.esUrl}
            onChange={(e) => onConfigChange({ ...config, esUrl: e.target.value })}
          />
        </div>
        <div className="sidebar__field">
          <label className="sidebar__label">
            <span className={`status-dot ${health.ollama ? 'status-dot--ok' : 'status-dot--error'}`} />
            Ollama
          </label>
          <input
            className="input-field"
            placeholder="Ollama URL"
            value={config.ollamaUrl}
            onChange={(e) => onConfigChange({ ...config, ollamaUrl: e.target.value })}
          />
        </div>
      </div>

      {/* Mode Selector */}
      <div className="sidebar__section">
        <h3 className="sidebar__heading">Mode</h3>
        <div className="sidebar__modes">
          {MODES.map((m) => (
            <button
              key={m.key}
              className={`sidebar__mode-card ${mode === m.key ? 'sidebar__mode-card--active' : ''}`}
              onClick={() => onModeChange(m.key)}
            >
              <span className="sidebar__mode-label">{m.label}</span>
              <span className="sidebar__mode-desc">{m.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Target Inputs */}
      <div className="sidebar__section">
        <h3 className="sidebar__heading">Target</h3>
        {mode === 'range' && (
          <>
            <input
              className="input-field"
              placeholder="From block"
              value={target.fromBlock || ''}
              onChange={(e) => onTargetChange({ ...target, fromBlock: e.target.value })}
            />
            <input
              className="input-field"
              placeholder="To block"
              value={target.toBlock || ''}
              onChange={(e) => onTargetChange({ ...target, toBlock: e.target.value })}
              style={{ marginTop: 6 }}
            />
          </>
        )}
        {mode === 'tx' && (
          <input
            className="input-field"
            placeholder="Transaction hash"
            value={target.txHash || ''}
            onChange={(e) => onTargetChange({ ...target, txHash: e.target.value })}
          />
        )}
        {mode === 'wallet' && (
          <input
            className="input-field"
            placeholder="Wallet address"
            value={target.walletAddress || ''}
            onChange={(e) => onTargetChange({ ...target, walletAddress: e.target.value })}
          />
        )}
        {mode === 'watch' && (
          <p className="sidebar__hint">No target needed — monitors live blocks</p>
        )}
      </div>

      {/* Run Button */}
      <div className="sidebar__section">
        <button
          className="btn-pill btn-pill--primary sidebar__run-btn"
          onClick={onRun}
          disabled={!canRun}
        >
          {isRunning ? 'Running...' : 'Run Analysis'}
        </button>
      </div>

      {/* Saved Analyses */}
      {savedCases.length > 0 && (
        <div className="sidebar__section sidebar__saved">
          <h3 className="sidebar__heading">Saved Analyses</h3>
          <div className="sidebar__cases">
            {savedCases.map((c) => (
              <button
                key={c.investigationId}
                className="sidebar__case-item"
                onClick={() => onRestoreCase(c)}
              >
                <span className="mono">{c.investigationId}</span>
                <span className={`badge badge--${(c.severity || 'low').toLowerCase()}`}>
                  {c.severity || 'N/A'}
                </span>
                <span className="sidebar__case-type">{c.attackType || 'Unknown'}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
