"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted">
        Send a message to start a conversation
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto p-4">
      {messages.map((m) => (
        <div
          key={m.id}
          className={`max-w-[80%] whitespace-pre-wrap break-words rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
            m.role === "user"
              ? "self-end rounded-br-sm bg-user-bubble"
              : "self-start rounded-bl-sm bg-assistant-bubble"
          }`}
        >
          {m.content}
          {m.streaming && (
            <span className="ml-0.5 animate-pulse text-accent">▍</span>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
