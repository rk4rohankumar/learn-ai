"use client";

import { useCallback, useState } from "react";
import { parseSSE } from "@/lib/sse";
import type { ChatMessage, LogEntry } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let nextId = 0;
const uid = () => String(++nextId);

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const appendLog = useCallback((event: string, data: unknown) => {
    setLog((prev) => [
      ...prev,
      { id: uid(), event, data: JSON.stringify(data) },
    ]);
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      setError(null);
      setIsStreaming(true);

      const assistantId = uid();
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "user", content: text },
        { id: assistantId, role: "assistant", content: "", streaming: true },
      ]);

      const patchAssistant = (patch: Partial<ChatMessage>) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, ...patch } : m)),
        );

      try {
        const res = await fetch(`${API_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            ...(conversationId && { conversation_id: conversationId }),
          }),
        });

        if (!res.ok) {
          const body = await res
            .json()
            .catch(() => ({ detail: res.statusText }));
          throw new Error(`HTTP ${res.status}: ${body.detail}`);
        }

        for await (const frame of parseSSE(res)) {
          appendLog(frame.event, frame.data);

          switch (frame.event) {
            case "conversation":
              setConversationId(frame.data.conversation_id);
              break;
            case "text":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + frame.data.content }
                    : m,
                ),
              );
              break;
            case "done":
              break;
            case "error":
              throw new Error(frame.data.message || "server error event");
          }
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
        appendLog("fail", { message });
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
      } finally {
        patchAssistant({ streaming: false });
        setIsStreaming(false);
      }
    },
    [conversationId, appendLog],
  );

  const resetConversation = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setError(null);
    appendLog("meta", { note: "new conversation" });
  }, [appendLog]);

  return {
    messages,
    conversationId,
    log,
    isStreaming,
    error,
    sendMessage,
    resetConversation,
  };
}
