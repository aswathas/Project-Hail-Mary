import React from 'react';
import './StoredAnalyses.css';

export function StoredAnalyses({ cases = [], onRestore, onDelete }) {
  if (cases.length === 0) {
    return (
      <div className="stored">
        <div className="stored__empty">
          No saved analyses. Run an investigation to get started.
        </div>
      </div>
    );
  }

  return (
    <div className="stored">
      <table className="stored__table">
        <thead>
          <tr>
            <th>Case ID</th>
            <th>Mode</th>
            <th>Attack Type</th>
            <th>Severity</th>
            <th>Funds</th>
            <th>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr
              key={c.investigationId}
              className="stored__row"
              onClick={() => onRestore(c)}
            >
              <td className="mono">{c.investigationId}</td>
              <td>{c.mode || '-'}</td>
              <td>{c.attackType || 'Unknown'}</td>
              <td>
                <span className={`badge badge--${(c.severity || 'low').toLowerCase()}`}>
                  {c.severity || 'N/A'}
                </span>
              </td>
              <td className="mono stored__funds">
                {c.fundsDrained ? `${c.fundsDrained} ETH` : '-'}
              </td>
              <td className="stored__date">{c.timestamp || '-'}</td>
              <td>
                <button
                  className="stored__delete"
                  onClick={(e) => { e.stopPropagation(); onDelete(c.investigationId); }}
                >
                  x
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
