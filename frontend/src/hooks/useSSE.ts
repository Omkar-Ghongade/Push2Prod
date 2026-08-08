"use client";

import { useCallback, useRef, useState } from "react";
import { SSEEvent } from "@/types";

interface UseSSEReturn {
  sendMessage: (question: string) => Promise<void>;
  events: SSEEvent[];
  isStreaming: boolean;
  answer: string;
  error: string | null;
  reset: () => void;
}

export function useSSE(): UseSSEReturn {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setEvents([]);
    setAnswer("");
    setError(null);
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(
    async (question: string) => {
      abortRef.current?.abort();
      setEvents([]);
      setAnswer("");
      setError(null);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      // 5 minute timeout for long investigations
      const timeout = setTimeout(() => controller.abort(), 300000);

      try {
        const res = await fetch("/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`Server error: ${res.status}`);
        }

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

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const event: SSEEvent = JSON.parse(line.slice(6));
                setEvents((prev) => [...prev, event]);

                if (event.type === "final_answer" && event.text) {
                  setAnswer(event.text);
                  setIsStreaming(false);
                }
                if (event.type === "error") {
                  setError(event.text || "Unknown error");
                  setIsStreaming(false);
                }
              } catch {
                // skip malformed JSON
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        clearTimeout(timeout);
        setIsStreaming(false);
      }
    },
    []
  );

  return { sendMessage, events, isStreaming, answer, error, reset };
}
