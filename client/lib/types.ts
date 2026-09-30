// Mirrors server/events/sse.py — the SSE protocol contract.

export type SSEEventType =
  | "conversation"
  | "message"
  | "text"
  | "tool_started"
  | "tool_finished"
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

export interface ToolStartedPayload {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolFinishedPayload {
  id: string;
  name: string;
  status: string;
  content: string;
  is_error: boolean;
}

export interface ErrorEvent {
  message: string;
}

export type SSEFrame =
  | { event: "conversation"; data: ConversationEvent }
  | { event: "text"; data: TextPayload }
  | { event: "tool_started"; data: ToolStartedPayload }
  | { event: "tool_finished"; data: ToolFinishedPayload }
  | { event: "done"; data: Record<string, never> }
  | { event: "cancelled"; data: Record<string, never> }
  | { event: "error"; data: ErrorEvent };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export interface ToolCall {
  id: string; // tool_use_id from the server
  name: string;
  arguments: Record<string, unknown>;
  status: "running" | "completed" | "error";
  content?: string; // result, once finished
  isError?: boolean;
}

// The chat stream interleaves messages and tool calls in arrival order.
export type ChatItem =
  | ({ kind: "message" } & ChatMessage)
  | ({ kind: "tool" } & ToolCall);

// GET /conversations
export interface ConversationSummary {
  id: string;
  created_at: string;
}

// GET /conversations/{id}/messages
export interface MessageOut {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface LogEntry {
  id: string;
  event: string;
  data: string;
}
