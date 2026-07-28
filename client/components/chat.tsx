"use client";

import { useState } from "react";
import { useChat } from "@/hooks/use-chat";
import { MessageList } from "./message-list";
import { Composer } from "./composer";
import { EventLog } from "./event-log";

export function Chat() {
  const {
    messages,
    conversationId,
    log,
    isStreaming,
    error,
    sendMessage,
    stopGeneration,
    resetConversation,
  } = useChat();
  const [showLog, setShowLog] = useState(true);

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex flex-wrap items-center gap-3 border-b border-edge px-4 py-2.5">
        <h1 className="text-[15px] font-semibold">Chat</h1>
        <span className="rounded-md border border-edge bg-panel px-2 py-1 font-mono text-[11px] text-muted">
          conversation:{" "}
          <b className="font-semibold text-accent">
            {conversationId ?? "none (new)"}
          </b>
        </span>
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={() => setShowLog((v) => !v)}
            className="rounded-md border border-edge bg-panel px-3 py-1.5 text-[13px] hover:border-accent"
          >
            {showLog ? "Hide events" : "Show events"}
          </button>
          <button
            type="button"
            onClick={resetConversation}
            disabled={isStreaming}
            className="rounded-md border border-edge bg-panel px-3 py-1.5 text-[13px] hover:border-accent disabled:opacity-40"
          >
            New conversation
          </button>
        </div>
      </header>

      <main className="flex min-h-0 flex-1">
        <section className="flex min-w-0 flex-[1.4] flex-col">
          <MessageList messages={messages} />
          {error && (
            <p
              role="alert"
              className="mx-4 mb-2 self-center rounded-lg border border-danger px-3 py-2 text-[13px] text-danger"
            >
              ⚠ {error}
            </p>
          )}
          <Composer
            disabled={isStreaming}
            onSend={sendMessage}
            onStop={stopGeneration}
          />
        </section>

        {showLog && (
          <aside className="flex min-w-72 flex-1 flex-col border-l border-edge">
            <h2 className="border-b border-edge px-3.5 py-2 text-[11px] uppercase tracking-widest text-muted">
              Event log (raw SSE)
            </h2>
            <EventLog log={log} />
          </aside>
        )}
      </main>
    </div>
  );
}
