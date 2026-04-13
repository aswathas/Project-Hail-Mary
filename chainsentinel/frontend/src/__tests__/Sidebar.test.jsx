import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from '../components/Sidebar';

describe('Sidebar', () => {
  const defaultProps = {
    config: { rpcUrl: '', esUrl: '', ollamaUrl: '' },
    onConfigChange: vi.fn(),
    health: { rpc: false, es: false, ollama: false },
    mode: 'range',
    onModeChange: vi.fn(),
    target: {},
    onTargetChange: vi.fn(),
    onRun: vi.fn(),
    isRunning: false,
    savedCases: [],
    onRestoreCase: vi.fn(),
  };

  it('renders connection config inputs', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByPlaceholderText(/rpc url/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/es url/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/ollama url/i)).toBeInTheDocument();
  });

  it('shows health status dots', () => {
    render(<Sidebar {...defaultProps} health={{ rpc: true, es: true, ollama: false }} />);
    const dots = document.querySelectorAll('.status-dot');
    expect(dots.length).toBeGreaterThanOrEqual(3);
  });

  it('renders mode selector cards', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText('Watch')).toBeInTheDocument();
    expect(screen.getByText('Range')).toBeInTheDocument();
    expect(screen.getByText('Tx Analysis')).toBeInTheDocument();
    expect(screen.getByText('Wallet Hunt')).toBeInTheDocument();
  });

  it('calls onModeChange when mode card is clicked', () => {
    render(<Sidebar {...defaultProps} />);
    fireEvent.click(screen.getByText('Wallet Hunt'));
    expect(defaultProps.onModeChange).toHaveBeenCalledWith('wallet');
  });

  it('shows Run Analysis button', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText(/run analysis/i)).toBeInTheDocument();
  });

  it('disables Run button when not connected', () => {
    render(<Sidebar {...defaultProps} health={{ rpc: false, es: false, ollama: false }} />);
    const btn = screen.getByText(/run analysis/i);
    expect(btn).toBeDisabled();
  });

  it('shows Running state during analysis', () => {
    render(<Sidebar {...defaultProps} isRunning={true} />);
    expect(screen.getByText(/running/i)).toBeInTheDocument();
  });

  it('displays saved cases list', () => {
    const cases = [
      { investigationId: 'INV-001', attackType: 'Reentrancy', severity: 'CRIT', timestamp: '2026-04-12' },
    ];
    render(<Sidebar {...defaultProps} savedCases={cases} />);
    expect(screen.getByText('INV-001')).toBeInTheDocument();
  });
});
