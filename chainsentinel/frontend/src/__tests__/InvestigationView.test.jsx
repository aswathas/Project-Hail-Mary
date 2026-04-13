import { render, screen, fireEvent } from '@testing-library/react';
import { InvestigationView } from '../components/InvestigationView';

describe('InvestigationView', () => {
  const defaultProps = {
    investigationId: 'INV-2026-0001',
    severity: 'CRIT',
    attackType: 'Reentrancy Drain',
    attacker: '0xdeadbeef...',
    victim: '0x12345678...',
    fundsDrained: 150.5,
    blockRange: { from: 10, to: 18 },
    timeline: [
      { block_number: 10, event_name: 'Deposit', severity: 'ok', description: 'Normal deposit' },
      { block_number: 15, signal_name: 'reentrancy_pattern', severity: 'crit', description: 'Recursive calls detected' },
    ],
    signals: [
      { signal_name: 'reentrancy_pattern', severity: 'CRIT', score: 0.95, description: 'Recursive withdraw calls' },
      { signal_name: 'internal_eth_drain', severity: 'CRIT', score: 0.85, description: 'ETH drained via internal calls' },
    ],
    totalSignals: 61,
    activeTab: 'timeline',
    onTabChange: vi.fn(),
    onAction: vi.fn(),
  };

  it('renders severity badge and attack type', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText('CRIT')).toBeInTheDocument();
    expect(screen.getByText('Reentrancy Drain')).toBeInTheDocument();
  });

  it('renders case ID in monospace', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText('INV-2026-0001')).toBeInTheDocument();
  });

  it('renders meta bar with attacker and victim info', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText(/0xdeadbeef/)).toBeInTheDocument();
    expect(screen.getByText(/0x12345678/)).toBeInTheDocument();
    expect(screen.getByText(/150\.5/)).toBeInTheDocument();
  });

  it('renders timeline events', () => {
    render(<InvestigationView {...defaultProps} activeTab="timeline" />);
    expect(screen.getByText(/Normal deposit/)).toBeInTheDocument();
    expect(screen.getByText(/Recursive calls detected/)).toBeInTheDocument();
  });

  it('renders signal count header', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText(/2 of 61 signals fired/)).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    render(<InvestigationView {...defaultProps} />);
    expect(screen.getByText(/explain signals/i)).toBeInTheDocument();
    expect(screen.getByText(/trace funds/i)).toBeInTheDocument();
    expect(screen.getByText(/generate report/i)).toBeInTheDocument();
  });

  it('calls onAction when action button clicked', () => {
    render(<InvestigationView {...defaultProps} />);
    fireEvent.click(screen.getByText(/generate report/i));
    expect(defaultProps.onAction).toHaveBeenCalledWith('generate_report');
  });
});
