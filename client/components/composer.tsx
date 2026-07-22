"use client";

import { useState } from "react";

export function Composer({
  disabled,
  onSend,
}: {
  disabled: boolean;
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    setText("");
    onSend(trimmed);
  }

  return (
    <form onSubmit={submit} className="flex gap-2 border-t border-edge p-3">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type a message…"
        autoFocus
        disabled={disabled}
        aria-label="Message"
        className="flex-1 rounded-lg border border-edge bg-panel px-3.5 py-2.5 text-sm outline-none focus:border-accent disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="rounded-lg border border-edge bg-panel px-4 text-sm hover:border-accent disabled:cursor-not-allowed disabled:opacity-40"
      >
        Send
      </button>
    </form>
  );
}
