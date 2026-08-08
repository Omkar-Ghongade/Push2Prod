export interface SSEEvent {
  type: "narration" | "tool_result" | "final_answer" | "error";
  text?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: unknown;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  events?: SSEEvent[];
  timestamp: Date;
}
