import type { ChatEvent, Paper, Subgraph } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

function parseEvent(block: string): ChatEvent | null {
  let event = "";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7).trim();
    else if (line.startsWith("data: ")) data += line.slice(6);
  }
  return event && data ? ({ event, data: JSON.parse(data) } as ChatEvent) : null;
}

/** POST a question and call onEvent for each Server-Sent Event as it arrives.
 *  EventSource can't POST, so the stream is read from fetch directly.
 *  onOpen fires when the server responds: an awake server answers at once (before the agent
 *  has produced anything), while a sleeping free-tier server holds the request until it boots. */
export async function streamChat(
  question: string,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
  onOpen?: () => void,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  onOpen?.();
  if (!res.ok || !res.body) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      message = body.error ?? body.detail?.[0]?.msg ?? message;
    } catch {
      // not JSON; keep the generic message
    }
    throw new ApiError(message, res.status);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n/g, "\n");
    let end: number;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const event = parseEvent(buffer.slice(0, end));
      buffer = buffer.slice(end + 2);
      if (event) onEvent(event);
    }
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(res.status === 404 ? "Not in the indexed corpus" : `Request failed (${res.status})`, res.status);
  return res.json();
}

export const getPaper = (id: string) => getJson<Paper>(`/api/papers/${id}`);
export const getPaperGraph = (id: string) => getJson<Subgraph>(`/api/graph/paper/${id}`);
