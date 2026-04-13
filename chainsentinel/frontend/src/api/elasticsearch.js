/**
 * Elasticsearch API — direct ES queries from frontend.
 * Used for investigation data retrieval after pipeline completes.
 */

const DEFAULT_ES_URL = 'http://localhost:9200';

export function createEsClient(esUrl = DEFAULT_ES_URL) {
  return {
    async search(index, query, size = 100) {
      const res = await fetch(`${esUrl}/${index}/_search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, size, sort: [{ block_number: 'asc' }] }),
      });
      if (!res.ok) throw new Error(`ES search failed: ${res.status}`);
      return res.json();
    },

    async getSignals(investigationId) {
      return this.search('forensics', {
        bool: {
          must: [
            { term: { investigation_id: investigationId } },
            { term: { layer: 'signal' } },
          ],
        },
      }, 500);
    },

    async getAlerts(investigationId) {
      return this.search('forensics', {
        bool: {
          must: [
            { term: { investigation_id: investigationId } },
            { term: { layer: 'alert' } },
          ],
        },
      }, 100);
    },

    async getDerived(investigationId, derivedType = null) {
      const must = [
        { term: { investigation_id: investigationId } },
        { term: { layer: 'derived' } },
      ];
      if (derivedType) {
        must.push({ term: { derived_type: derivedType } });
      }
      return this.search('forensics', { bool: { must } }, 1000);
    },

    async getAttackerData(investigationId) {
      return this.search('forensics', {
        bool: {
          must: [
            { term: { investigation_id: investigationId } },
            { term: { layer: 'attacker' } },
          ],
        },
      }, 100);
    },

    async getTimeline(investigationId) {
      const res = await fetch(`${esUrl}/forensics/_search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: {
            bool: {
              must: [
                { term: { investigation_id: investigationId } },
                { terms: { layer: ['signal', 'alert', 'derived'] } },
              ],
            },
          },
          size: 500,
          sort: [{ block_number: 'asc' }, { '@timestamp': 'asc' }],
        }),
      });
      if (!res.ok) throw new Error(`ES timeline failed: ${res.status}`);
      return res.json();
    },
  };
}
