/**
 * Ollama API — chat and report generation via local LLM.
 */

const DEFAULT_OLLAMA_URL = 'http://localhost:11434';

export function createOllamaClient(ollamaUrl = DEFAULT_OLLAMA_URL) {
  return {
    async chat(messages, model = 'gemma3:1b', temperature = 0.2) {
      const res = await fetch(`${ollamaUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages,
          stream: false,
          options: { temperature },
        }),
      });
      if (!res.ok) throw new Error(`Ollama chat failed: ${res.status}`);
      const data = await res.json();
      return data.message?.content || '';
    },

    async chatStream(messages, model = 'gemma3:1b', temperature = 0.2) {
      const res = await fetch(`${ollamaUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages,
          stream: true,
          options: { temperature },
        }),
      });
      if (!res.ok) throw new Error(`Ollama stream failed: ${res.status}`);
      return res.body;
    },

    async checkModel(model = 'gemma3:1b') {
      try {
        const res = await fetch(`${ollamaUrl}/api/tags`);
        if (!res.ok) return false;
        const data = await res.json();
        return data.models?.some(m => m.name === model) || false;
      } catch {
        return false;
      }
    },
  };
}
