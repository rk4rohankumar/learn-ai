import type { SSEFrame } from "./types";

// Parses a fetch Response body into typed SSE frames.
// Buffers across chunk boundaries; frames are separated by "\n\n".
export async function* parseSSE(response: Response): AsyncGenerator<SSEFrame> {
  if (!response.body) throw new Error("Response has no body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);

        let event = "message";
        let data = "";
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        yield { event, data: data ? JSON.parse(data) : {} } as SSEFrame;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
