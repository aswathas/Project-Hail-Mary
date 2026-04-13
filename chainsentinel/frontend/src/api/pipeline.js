/**
 * Pipeline API — communicates with FastAPI backend.
 * POST /analyze — starts pipeline, returns SSE stream
 * GET /health — checks service connectivity
 */

const BASE_URL = '';

export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export function startAnalysis(config) {
  const url = `${BASE_URL}/analyze`;
  const eventSource = new EventSource(url + '?' + new URLSearchParams({
    mode: config.mode,
    rpc_url: config.rpcUrl,
    target: config.target || '',
    investigation_id: config.investigationId,
    manifest_path: config.manifestPath || '',
    from_block: config.fromBlock || '',
    to_block: config.toBlock || '',
  }));
  return eventSource;
}

export async function startAnalysisPost(config) {
  let target = '';
  if (config.mode === 'tx') {
    target = config.txHash || '';
  } else if (config.mode === 'range') {
    target = {
      from_block: config.fromBlock ? parseInt(config.fromBlock) : null,
      to_block: config.toBlock ? parseInt(config.toBlock) : null,
    };
  } else if (config.mode === 'wallet') {
    target = config.walletAddress || '';
  }

  const res = await fetch(`${BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mode: config.mode,
      rpc_url: config.rpcUrl,
      target,
    }),
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
  return res.body;
}

export async function getAnalysis(investigationId) {
  const res = await fetch(`${BASE_URL}/analysis/${investigationId}`);
  if (!res.ok) throw new Error(`Fetch analysis failed: ${res.status}`);
  return res.json();
}

export async function runSimulation(scenario) {
  const res = await fetch(`${BASE_URL}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  });
  if (!res.ok) throw new Error(`Simulation failed: ${res.status}`);
  return res.json();
}
