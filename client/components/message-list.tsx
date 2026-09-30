"use client";

import { useEffect, useRef } from "react";
import type { ChatItem } from "@/lib/types";
import { ToolCard } from "./tool-card";

export function MessageList({ items }: { items: ChatItem[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items]);

  if (items.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted">
        Send a message to start a conversation
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto p-4">
      {items.map((item) => {
        if (item.kind === "tool") {
          return <ToolCard key={item.id} tool={item} />;
        }
        return (
          <div
            key={item.id}
            className={`max-w-[80%] whitespace-pre-wrap break-words rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
              item.role === "user"
                ? "self-end rounded-br-sm bg-user-bubble"
                : "self-start rounded-bl-sm bg-assistant-bubble"
            }`}
          >
            {item.content}
            {item.streaming && (
              <span className="ml-0.5 animate-pulse text-accent">▍</span>
            )}
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
