const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SSEEvent<T = unknown> {
  event: string;
  data: T;
}

export interface SSEOptions {
  onMessage: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
  headers?: Record<string, string>;
}

/**
 * Creates an SSE connection using fetch + ReadableStream.
 * Returns an abort function to close the connection.
 */
export function connectSSE(
  path: string,
  options: SSEOptions,
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const url = new URL(path, API_BASE);
      const res = await fetch(url.toString(), {
        headers: {
          Accept: "text/event-stream",
          ...options.headers,
        },
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`SSE connection failed: ${res.status}`);
      }

      options.onOpen?.();

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "message";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            currentData += line.slice(6);
          } else if (line === "") {
            if (currentData) {
              try {
                const parsed = JSON.parse(currentData);
                options.onMessage({ event: currentEvent, data: parsed });
              } catch {
                options.onMessage({ event: currentEvent, data: currentData });
              }
              currentEvent = "message";
              currentData = "";
            }
          }
        }
      }

      options.onClose?.();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        options.onError?.(err as Error);
      }
    }
  })();

  return () => controller.abort();
}

/**
 * POST-based SSE — sends a request body then streams the response.
 * Used for streaming agent responses.
 */
export function streamPost<TBody>(
  path: string,
  body: TBody,
  options: SSEOptions,
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const url = new URL(path, API_BASE);
      const res = await fetch(url.toString(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...options.headers,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`SSE POST failed: ${res.status}`);
      }

      options.onOpen?.();

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "message";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            currentData += line.slice(6);
          } else if (line === "") {
            if (currentData) {
              try {
                const parsed = JSON.parse(currentData);
                options.onMessage({ event: currentEvent, data: parsed });
              } catch {
                options.onMessage({ event: currentEvent, data: currentData });
              }
              currentEvent = "message";
              currentData = "";
            }
          }
        }
      }

      options.onClose?.();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        options.onError?.(err as Error);
      }
    }
  })();

  return () => controller.abort();
}
