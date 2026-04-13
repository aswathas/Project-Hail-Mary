import { useState, useCallback, useMemo } from 'react';
import { createEsClient } from '../api/elasticsearch';

/**
 * useElasticsearch — ES query hook for investigation data.
 */
export function useElasticsearch(esUrl = 'http://localhost:9200') {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const client = useMemo(() => createEsClient(esUrl), [esUrl]);

  const fetchSignals = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getSignals(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchAlerts = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getAlerts(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchTimeline = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getTimeline(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchAttackerData = useCallback(async (investigationId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getAttackerData(investigationId);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  const fetchDerived = useCallback(async (investigationId, derivedType) => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.getDerived(investigationId, derivedType);
      return res.hits?.hits?.map(h => h._source) || [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [client]);

  return {
    loading,
    error,
    fetchSignals,
    fetchAlerts,
    fetchTimeline,
    fetchAttackerData,
    fetchDerived,
  };
}
