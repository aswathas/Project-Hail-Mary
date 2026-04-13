import { render, screen } from '@testing-library/react';
import { PipelineFeed } from '../components/PipelineFeed';

describe('PipelineFeed', () => {
  it('renders stats bar', () => {
    const stats = { blocks: 8, txs: 47, signals: 5, indexed: 189 };
    render(<PipelineFeed logs={[]} stats={stats} />);
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('47')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('189')).toBeInTheDocument();
  });

  it('renders log entries with severity colors', () => {
    const logs = [
      { phase: 'collector', msg: 'Block 5 fetched', severity: 'ok', ts: '12:04:02' },
      { phase: 'signals', msg: 'reentrancy_pattern fired (0.95)', severity: 'crit', ts: '12:04:06' },
    ];
    render(<PipelineFeed logs={logs} stats={{ blocks: 0, txs: 0, signals: 0, indexed: 0 }} />);
    expect(screen.getByText(/Block 5 fetched/)).toBeInTheDocument();
    expect(screen.getByText(/reentrancy_pattern/)).toBeInTheDocument();
  });

  it('groups logs by phase', () => {
    const logs = [
      { phase: 'collector', msg: 'Start', severity: 'ok', ts: '12:00:00' },
      { phase: 'collector', msg: 'Done', severity: 'ok', ts: '12:00:01' },
      { phase: 'normalizer', msg: 'Start', severity: 'ok', ts: '12:00:02' },
    ];
    render(<PipelineFeed logs={logs} stats={{ blocks: 0, txs: 0, signals: 0, indexed: 0 }} />);
    expect(screen.getByText('collector')).toBeInTheDocument();
    expect(screen.getByText('normalizer')).toBeInTheDocument();
  });
});
