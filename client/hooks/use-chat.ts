"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { parseSSE } from "@/lib/sse";
import type {
  ChatMessage,
  ConversationSummary,
  LogEntry,
  MessageOut,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let nextId = 0;
const uid = () => String(++nextId);

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  // generation currently streaming — the cancel endpoint's address
  const generationIdRef = useRef<string | null>(null);

  const refreshConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/conversations`);
      if (res.ok) setConversations(await res.json());
    } catch {
      // list is a convenience; chat still works without it
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const selectConversation = useCallback(async (id: string) => {
    const res = await fetch(`${API_URL}/conversations/${id}/messages`);
    if (!res.ok) {
      setError(`Failed to load conversation (HTTP ${res.status})`);
      return;
    }
    const history: MessageOut[] = await res.json();
    setMessages(
      history.map((m) => ({ id: m.id, role: m.role, content: m.content })),
    );
    setConversationId(id);
    setError(null);
  }, []);

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
              generationIdRef.current = frame.data.generation_id;
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
            case "cancelled":
              // partial text stays on screen; stream is about to close
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
        generationIdRef.current = null;
        patchAssistant({ streaming: false });
        // a generation cancelled before any text leaves an empty bubble — drop it
        setMessages((prev) =>
          prev.filter((m) => !(m.id === assistantId && m.content === "")),
        );
        setIsStreaming(false);
        refreshConversations(); // a new conversation may have been created
      }
    },
    [conversationId, appendLog, refreshConversations],
  );

  const stopGeneration = useCallback(async () => {
    const generationId = generationIdRef.current;
    if (!generationId) return;
    try {
      // fire the REQUEST; the stream's `cancelled` event is the fact
      await fetch(`${API_URL}/generations/${generationId}/cancel`, {
        method: "POST",
      });
      appendLog("meta", { note: `cancel requested for ${generationId}` });
    } catch {
      // cancel is best-effort; nothing useful to surface
    }
  }, [appendLog]);

  const resetConversation = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setError(null);
    appendLog("meta", { note: "new conversation" });
  }, [appendLog]);

  return {
    messages,
    conversationId,
    conversations,
    log,
    isStreaming,
    error,
    sendMessage,
    stopGeneration,
    resetConversation,
    selectConversation,
  };
}
