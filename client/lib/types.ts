// Mirrors server/events/sse.py — the SSE protocol contract.

export type SSEEventType =
  | "conversation"
  | "message"
  | "text"
  | "done"
  | "cancelled"
  | "error";

export interface ConversationEvent {
  conversation_id: string;
  generation_id: string;
}

export interface TextPayload {
  content: string;
}

export interface ErrorEvent {
  message: string;
}

export type SSEFrame =
  | { event: "conversation"; data: ConversationEvent }
  | { event: "text"; data: TextPayload }
  | { event: "done"; data: Record<string, never> }
  | { event: "error"; data: ErrorEvent };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export interface LogEntry {
  id: string;
  event: string;
  data: string;
}
