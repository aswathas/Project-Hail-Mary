import { useState, useCallback, useMemo } from 'react';
import { createOllamaClient } from '../api/ollama';

/**
 * useOllama — Ollama chat + report generation hook.
 */
export function useOllama(ollamaUrl = 'http://localhost:11434', model = 'gemma3:1b') {
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);
  const client = useMemo(() => createOllamaClient(ollamaUrl), [ollamaUrl]);

  const chat = useCallback(async (messages) => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.chat(messages, model);
      return response;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [client, model]);

  const chatStream = useCallback(async (messages, onChunk) => {
    setStreaming(true);
    setError(null);
    try {
      const stream = await client.chatStream(messages, model);
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(Boolean);

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.message?.content) {
              fullText += data.message.content;
              onChunk(fullText);
            }
          } catch {
            // Skip non-JSON lines
          }
        }
      }

      return fullText;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setStreaming(false);
    }
  }, [client, model]);

  const checkAvailable = useCallback(async () => {
    return client.checkModel(model);
  }, [client, model]);

  return {
    loading,
    streaming,
    error,
    chat,
    chatStream,
    checkAvailable,
  };
}
