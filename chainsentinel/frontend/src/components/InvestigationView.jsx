import React from 'react';
import './InvestigationView.css';

const SEVERITY_DOT = {
  crit: '#d03238',
  high: '#e67e22',
  med: '#3498db',
  low: '#868685',
  ok: '#3498db',
  info: '#868685',
};

export function InvestigationView({
  investigationId,
  severity,
  attackType,
  attacker,
  victim,
  fundsDrained,
  blockRange,
  timeline,
  signals,
  totalSignals,
  activeTab,
  onTabChange,
  onAction,
}) {
  return (
    <div className="investigation">
      {/* Top Bar */}
      <div className="investigation__topbar">
        <span className={`badge badge--${(severity || 'low').toLowerCase()}`}>
          {severity}
        </span>
        <span className="investigation__attack-type">{attackType}</span>
        <span className="investigation__case-id mono">{investigationId}</span>
        <div className="investigation__tabs">
          {['timeline', 'graph', 'raw'].map((tab) => (
            <button
              key={tab}
              className={`investigation__tab ${activeTab === tab ? 'investigation__tab--active' : ''}`}
              onClick={() => onTabChange(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Meta Bar */}
      <div className="investigation__meta">
        <div className="investigation__meta-cell">
          <span className="investigation__meta-label">Attacker</span>
          <span className="mono">{attacker}</span>
        </div>
        <div className="investigation__meta-cell">
          <span className="investigation__meta-label">Victim</span>
          <span className="mono">{victim}</span>
        </div>
        <div className="investigation__meta-cell investigation__meta-cell--danger">
          <span className="investigation__meta-label">Funds Drained</span>
          <span className="mono">{fundsDrained} ETH</span>
        </div>
        <div className="investigation__meta-cell">
          <span className="investigation__meta-label">Block Range</span>
          <span className="mono">{blockRange?.from} - {blockRange?.to}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="investigation__content">
        {/* Timeline Panel */}
        <div className="investigation__timeline">
          <h3>Attack Timeline</h3>
          <div className="timeline">
            {(timeline || []).map((event, i) => {
              const sev = (event.severity || 'info').toLowerCase();
              return (
                <div key={i} className="timeline__event">
                  <div className="timeline__line" />
                  <div
                    className="timeline__dot"
                    style={{ background: SEVERITY_DOT[sev] || SEVERITY_DOT.info }}
                  />
                  <div className="timeline__body">
                    <span className="timeline__name">
                      {event.signal_name || event.event_name || 'Event'}
                    </span>
                    <span className="timeline__desc">{event.description}</span>
                    <span className="timeline__block mono">Block {event.block_number}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Signals Panel */}
        <div className="investigation__signals">
          <h3>{signals.length} of {totalSignals} signals fired</h3>
          <div className="signals-list">
            {signals.map((sig, i) => (
              <div key={i} className="signal-card card--dark">
                <div
                  className="signal-card__bar"
                  style={{
                    background: SEVERITY_DOT[(sig.severity || 'low').toLowerCase()] || SEVERITY_DOT.low,
                  }}
                />
                <div className="signal-card__body">
                  <span className="signal-card__name">{sig.signal_name}</span>
                  <span className="signal-card__desc">{sig.description}</span>
                  <span className="signal-card__score mono">Score: {sig.score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="investigation__actions">
        <button className="btn-pill btn-pill--secondary" onClick={() => onAction('explain_signals')}>
          Explain Signals
        </button>
        <button className="btn-pill btn-pill--secondary" onClick={() => onAction('trace_funds')}>
          Trace Funds
        </button>
        <button className="btn-pill btn-pill--secondary" onClick={() => onAction('pattern_match')}>
          Pattern Match
        </button>
        <button className="btn-pill btn-pill--primary" onClick={() => onAction('generate_report')}>
          Generate Report
        </button>
      </div>
    </div>
  );
}
