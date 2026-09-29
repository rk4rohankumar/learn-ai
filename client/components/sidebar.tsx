"use client";

import type { ConversationSummary } from "@/lib/types";

export function Sidebar({
  conversations,
  activeId,
  disabled,
  onSelect,
  onNew,
}: {
  conversations: ConversationSummary[];
  activeId: string | null;
  disabled: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  return (
    <nav className="flex w-60 shrink-0 flex-col border-r border-edge">
      <div className="border-b border-edge p-2">
        <button
          type="button"
          onClick={onNew}
          disabled={disabled}
          className="w-full rounded-md border border-edge bg-panel px-3 py-2 text-[13px] hover:border-accent disabled:opacity-40"
        >
          + New conversation
        </button>
      </div>
      <ul className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 && (
          <li className="px-2 py-1 text-[12px] text-muted">
            No conversations yet
          </li>
        )}
        {conversations.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => onSelect(c.id)}
              disabled={disabled}
              className={`mb-1 w-full rounded-md px-2.5 py-2 text-left disabled:opacity-40 ${
                c.id === activeId
                  ? "border border-accent/50 bg-panel"
                  : "border border-transparent hover:bg-panel"
              }`}
            >
              <span className="block truncate font-mono text-[11px] text-foreground/90">
                {c.id.slice(0, 8)}…
              </span>
              <span className="block text-[10.5px] text-muted">
                {new Date(c.created_at).toLocaleString()}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
