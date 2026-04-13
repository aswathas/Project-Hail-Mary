import { renderHook, act } from '@testing-library/react';
import { useLocalStorage } from '../hooks/useLocalStorage';

describe('useLocalStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns initial value when no stored value exists', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('returns stored value when it exists', () => {
    localStorage.setItem('test-key', JSON.stringify('stored-value'));
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    expect(result.current[0]).toBe('stored-value');
  });

  it('updates localStorage when setValue is called', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    act(() => {
      result.current[1]('new-value');
    });
    expect(result.current[0]).toBe('new-value');
    expect(JSON.parse(localStorage.getItem('test-key'))).toBe('new-value');
  });

  it('handles object values', () => {
    const obj = { id: 'INV-001', signals: 5 };
    const { result } = renderHook(() => useLocalStorage('test-obj', null));
    act(() => {
      result.current[1](obj);
    });
    expect(result.current[0]).toEqual(obj);
  });

  it('handles array values', () => {
    const { result } = renderHook(() => useLocalStorage('test-arr', []));
    act(() => {
      result.current[1]([{ id: 1 }, { id: 2 }]);
    });
    expect(result.current[0]).toHaveLength(2);
  });
});
