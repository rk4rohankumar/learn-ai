"use client";

import { useEffect, useRef } from "react";
import type { LogEntry } from "@/lib/types";

const tagColor: Record<string, string> = {
  conversation: "text-accent",
  text: "text-ok",
  done: "text-warn",
  error: "text-danger",
  fail: "text-danger",
  meta: "text-muted",
};

export function EventLog({ log }: { log: LogEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [log]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto p-3 font-mono text-[11.5px] leading-relaxed"
    >
      {log.length === 0 && (
        <p className="text-muted">SSE frames will appear here…</p>
      )}
      {log.map((entry) => (
        <div key={entry.id} className="break-all">
          <span
            className={`inline-block min-w-24 font-semibold ${
              tagColor[entry.event] ?? "text-muted"
            }`}
          >
            {entry.event}
          </span>
          <span className="text-foreground/80">{entry.data}</span>
        </div>
      ))}
    </div>
  );
}
