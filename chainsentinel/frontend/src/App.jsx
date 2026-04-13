import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { PipelineFeed } from './components/PipelineFeed';
import { InvestigationView } from './components/InvestigationView';
import { EntityGraph } from './components/EntityGraph';
import { CopilotPanel } from './components/CopilotPanel';
import { StoredAnalyses } from './components/StoredAnalyses';
import { useAnalysis } from './hooks/useAnalysis';
import { useElasticsearch } from './hooks/useElasticsearch';
import { useOllama } from './hooks/useOllama';
import { useLocalStorage } from './hooks/useLocalStorage';
import { checkHealth, startAnalysisPost } from './api/pipeline';

export default function App() {
  // Config
  const [config, setConfig] = useState({
    rpcUrl: 'http://127.0.0.1:8545',
    esUrl: 'http://localhost:9200',
    ollamaUrl: 'http://localhost:11434',
  });

  // Health
  const [health, setHealth] = useState({ rpc: false, es: false, ollama: false });

  // Mode & Target
  const [mode, setMode] = useState('range');
  const [target, setTarget] = useState({});
  const [activeTab, setActiveTab] = useState('timeline');

  // Saved cases
  const [savedCases, setSavedCases] = useLocalStorage('chainsentinel-cases', []);

  // Analysis state machine
  const analysis = useAnalysis();

  // ES hook
  const es = useElasticsearch(config.esUrl);

  // Ollama hook
  const ollama = useOllama(config.ollamaUrl);

  // Investigation data
  const [signals, setSignals] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [attackerData, setAttackerData] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });

  // Copilot
  const [copilotState, setCopilotState] = useState('idle');
  const [copilotMessages, setCopilotMessages] = useState([]);
  const [streamContent, setStreamContent] = useState('');

  // Health check on mount and config change
  useEffect(() => {
    const check = async () => {
      try {
        const h = await checkHealth();
        setHealth({
          rpc: h.rpc === 'ok',
          es: h.elasticsearch === 'ok',
          ollama: h.ollama === 'ok',
        });
      } catch {
        setHealth({ rpc: false, es: false, ollama: false });
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, [config]);

  // Load investigation data when analysis completes
  useEffect(() => {
    if (analysis.state === 'complete' && analysis.investigationId) {
      loadInvestigationData(analysis.investigationId);
      setCopilotState('ready');
    }
  }, [analysis.state, analysis.investigationId]);

  const loadInvestigationData = async (invId) => {
    const [sigs, alts, tl, atk] = await Promise.all([
      es.fetchSignals(invId),
      es.fetchAlerts(invId),
      es.fetchTimeline(invId),
      es.fetchAttackerData(invId),
    ]);

    setSignals(sigs);
    setAlerts(alts);
    setTimeline(tl);
    setAttackerData(atk);

    // Build graph data from attacker + derived data
    buildGraphData(atk, sigs);
  };

  const buildGraphData = (attackerDocs, signalDocs) => {
    const nodesMap = new Map();
    const edges = [];

    for (const doc of attackerDocs) {
      if (doc.cluster_wallets) {
        for (const w of doc.cluster_wallets) {
          if (!nodesMap.has(w)) {
            nodesMap.set(w, { id: w, role: 'unknown' });
          }
        }
      }
      if (doc.attacker_wallet) {
        nodesMap.set(doc.attacker_wallet, { id: doc.attacker_wallet, role: 'attacker' });
      }
    }

    setGraphData({
      nodes: Array.from(nodesMap.values()),
      edges,
    });
  };

  const handleRun = async () => {
    const invId = `INV-${Date.now()}`;
    analysis.startRun({ ...config, mode, ...target, investigationId: invId });
    setCopilotState('watching');

    try {
      const stream = await startAnalysisPost({
        mode,
        rpcUrl: config.rpcUrl,
        investigationId: invId,
        ...target,
      });

      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last potentially incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          // Handle SSE format: lines starting with "data: "
          let jsonStr = trimmed;
          if (trimmed.startsWith('data: ')) {
            jsonStr = trimmed.slice(6);
          } else if (trimmed.startsWith('event:') || trimmed.startsWith('id:') || trimmed.startsWith(':')) {
            continue;
          }

          try {
            const event = JSON.parse(jsonStr);
            if (event.phase === 'complete') {
              analysis.completeRun(event);
              // Save case
              setSavedCases((prev) => [
                { investigationId: invId, mode, severity: 'N/A', timestamp: new Date().toISOString(), ...event },
                ...prev,
              ]);
            } else {
              analysis.addLog(event);
            }
          } catch {
            // Skip non-JSON lines
          }
        }
      }
    } catch (err) {
      analysis.addLog({ phase: 'error', msg: err.message, severity: 'error', ts: new Date().toLocaleTimeString() });
    }
  };

  const handleRestoreCase = (caseData) => {
    analysis.restoreCase(caseData);
    if (caseData.investigationId) {
      loadInvestigationData(caseData.investigationId);
    }
  };

  const handleCopilotMessage = async (text) => {
    setCopilotMessages((prev) => [...prev, { role: 'user', content: text }]);

    const systemMsg = {
      role: 'system',
      content: `You are ChainSentinel Copilot analyzing investigation ${analysis.investigationId}. Signals fired: ${signals.map(s => s.signal_name).join(', ')}. Alerts: ${alerts.map(a => a.pattern_name).join(', ')}. You only summarize and explain what the analysis found. You never invent addresses, amounts, transaction hashes, or block numbers. If context is unavailable, say so.`,
    };

    const response = await ollama.chat([
      systemMsg,
      ...copilotMessages,
      { role: 'user', content: text },
    ]);

    if (response) {
      setCopilotMessages((prev) => [...prev, { role: 'assistant', content: response }]);
    }
  };

  const handleCopilotAction = (action) => {
    const prompts = {
      explain_signals: 'Explain the signals that fired in this investigation and their significance.',
      trace_funds: 'Describe the fund flow from the attacker wallet. Where did the stolen funds go?',
      pattern_match: 'Does this match any known attack patterns? Explain which pattern and confidence.',
      generate_report: 'Generate a full forensic report with: Executive Summary, Attack Timeline, Technical Mechanism, Attacker Attribution, Fund Trail, Signal Evidence, and Remediation Actions.',
      es_summary: 'Summarize what data is stored in Elasticsearch for this investigation.',
    };
    handleCopilotMessage(prompts[action] || action);
  };

  const handleAction = (action) => {
    handleCopilotAction(action);
  };

  // Derive top-level investigation props
  const topAlert = alerts[0] || {};
  const topAttacker = attackerData.find(d => d.attacker_type === 'profile') || {};

  return (
    <div className="app-layout">
      <div className="app-sidebar">
        <Sidebar
          config={config}
          onConfigChange={setConfig}
          health={health}
          mode={mode}
          onModeChange={setMode}
          target={target}
          onTargetChange={setTarget}
          onRun={handleRun}
          isRunning={analysis.state === 'running'}
          savedCases={savedCases}
          onRestoreCase={handleRestoreCase}
        />
      </div>

      <div className="app-workspace">
        {analysis.state === 'running' && (
          <PipelineFeed logs={analysis.logs} stats={analysis.stats} />
        )}
        {analysis.state === 'complete' && activeTab !== 'graph' && (
          <InvestigationView
            investigationId={analysis.investigationId}
            severity={topAlert.severity || (signals.some(s => s.severity === 'CRIT') ? 'CRIT' : 'MED')}
            attackType={topAlert.pattern_name || 'Unknown Pattern'}
            attacker={topAttacker.cluster_wallets?.[0] || topAlert.attacker_wallet || 'Unknown'}
            victim={topAlert.victim_contract || 'Unknown'}
            fundsDrained={topAttacker.total_stolen_eth || topAlert.funds_drained_eth || 0}
            blockRange={{
              from: topAttacker.attack_block_range_from || topAlert.attack_block_range_from,
              to: topAttacker.attack_block_range_to || topAlert.attack_block_range_to,
            }}
            timeline={timeline}
            signals={signals}
            totalSignals={61}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onAction={handleAction}
          />
        )}
        {analysis.state === 'complete' && activeTab === 'graph' && (
          <EntityGraph
            nodes={graphData.nodes}
            edges={graphData.edges}
            onNodeClick={(node) => handleCopilotMessage(`Tell me about address ${node.id}`)}
          />
        )}
        {analysis.state === 'idle' && (
          <StoredAnalyses
            cases={savedCases}
            onRestore={handleRestoreCase}
            onDelete={(id) => setSavedCases((prev) => prev.filter(c => c.investigationId !== id))}
          />
        )}
      </div>

      <div className="app-copilot">
        <CopilotPanel
          state={copilotState}
          messages={copilotMessages}
          onSendMessage={handleCopilotMessage}
          onQuickAction={handleCopilotAction}
          streaming={ollama.streaming}
          streamContent={streamContent}
        />
      </div>
    </div>
  );
}
