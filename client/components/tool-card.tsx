"use client";

import type { ToolCall } from "@/lib/types";

function StatusBadge({ status }: { status: ToolCall["status"] }) {
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1 text-accent">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
        running
      </span>
    );
  }
  if (status === "error") {
    return <span className="text-red-400">✕ error</span>;
  }
  return <span className="text-emerald-400">✓ done</span>;
}

export function ToolCard({ tool }: { tool: ToolCall }) {
  return (
    <details className="max-w-[80%] self-start rounded-lg border border-edge bg-panel/60 text-[12px]">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 font-mono">
        <span className="text-muted">⚙</span>
        <span className="font-semibold text-foreground/90">{tool.name}</span>
        <span className="ml-auto">
          <StatusBadge status={tool.status} />
        </span>
      </summary>
      <div className="space-y-2 border-t border-edge px-3 py-2">
        <div>
          <div className="mb-1 text-[10.5px] uppercase tracking-wide text-muted">
            arguments
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] text-foreground/80">
            {JSON.stringify(tool.arguments, null, 2)}
          </pre>
        </div>
        {tool.content !== undefined && (
          <div>
            <div className="mb-1 text-[10.5px] uppercase tracking-wide text-muted">
              result
            </div>
            <pre
              className={`overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] ${
                tool.isError ? "text-red-400" : "text-foreground/80"
              }`}
            >
              {tool.content}
            </pre>
          </div>
        )}
      </div>
    </details>
  );
}
