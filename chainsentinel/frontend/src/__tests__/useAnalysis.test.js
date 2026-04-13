import { renderHook, act } from '@testing-library/react';
import { useAnalysis } from '../hooks/useAnalysis';

describe('useAnalysis', () => {
  it('starts in idle state', () => {
    const { result } = renderHook(() => useAnalysis());
    expect(result.current.state).toBe('idle');
    expect(result.current.logs).toEqual([]);
    expect(result.current.stats).toEqual({
      blocks: 0, txs: 0, signals: 0, indexed: 0,
    });
  });

  it('transitions to running when startAnalysis is called', () => {
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.startRun({ mode: 'range', rpcUrl: 'http://localhost:8545' });
    });

    expect(result.current.state).toBe('running');
  });

  it('addLog appends to logs array', () => {
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.addLog({
        phase: 'collector',
        msg: 'Block 5 fetched',
        severity: 'ok',
        ts: '12:04:02',
      });
    });

    expect(result.current.logs).toHaveLength(1);
    expect(result.current.logs[0].phase).toBe('collector');
  });

  it('complete transitions state and sets investigation data', () => {
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.completeRun({
        investigationId: 'INV-2026-0001',
        stats: { blocks: 8, txs: 47, signals: 5, indexed: 189 },
      });
    });

    expect(result.current.state).toBe('complete');
    expect(result.current.investigationId).toBe('INV-2026-0001');
    expect(result.current.stats.blocks).toBe(8);
  });

  it('reset returns to idle', () => {
    const { result } = renderHook(() => useAnalysis());

    act(() => {
      result.current.completeRun({
        investigationId: 'INV-001',
        stats: { blocks: 1, txs: 1, signals: 0, indexed: 1 },
      });
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.state).toBe('idle');
    expect(result.current.logs).toEqual([]);
  });
});
