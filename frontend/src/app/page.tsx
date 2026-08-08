"use client";

import { useState, useRef, useEffect } from "react";
import { useSSE } from "@/hooks/useSSE";
import { ChatMessage } from "@/components/ChatMessage";
import { Message, SSEEvent } from "@/types";
import { Send, Loader2, RotateCcw, Sparkles, ArrowRight } from "lucide-react";

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const { sendMessage, events, isStreaming, answer, error, reset } = useSSE();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [streamingEvents, setStreamingEvents] = useState<SSEEvent[]>([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingEvents, isStreaming]);

  useEffect(() => {
    setStreamingEvents(events);
  }, [events]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || isStreaming) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: q,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreamingEvents([]);

    await sendMessage(q);
  };

  useEffect(() => {
    if (!isStreaming && (answer || error) && messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === "user") {
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: answer || `Error: ${error}`,
          events: streamingEvents,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setStreamingEvents([]);
      }
    }
  }, [isStreaming, answer, error]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const exampleQuestions = [
    { icon: "🔴", text: "How is my database health?" },
    { icon: "💳", text: "What errors are happening in the payment service?" },
    { icon: "📊", text: "Show me the request rate across all services" },
    { icon: "⚡", text: "Are there any incidents right now?" },
  ];

  return (
    <div className="min-h-screen bg-[#09090b] flex flex-col relative overflow-hidden">
      {/* Background gradient orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-500/10 rounded-full blur-[100px] animate-float" />
        <div className="absolute top-1/3 -left-40 w-96 h-96 bg-purple-500/8 rounded-full blur-[120px] animate-float" style={{ animationDelay: "2s" }} />
        <div className="absolute -bottom-40 right-1/4 w-80 h-80 bg-pink-500/6 rounded-full blur-[100px] animate-float" style={{ animationDelay: "4s" }} />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/[0.06] bg-[#09090b]/80 backdrop-blur-xl sticky top-0">
        <div className="max-w-3xl mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-white tracking-tight">
                TraceTalk
              </h1>
              <p className="text-[11px] text-zinc-500 font-medium">
                Live system observability
              </p>
            </div>
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => {
                setMessages([]);
                reset();
              }}
              className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all duration-200"
            >
              <RotateCcw size={13} />
              New chat
            </button>
          )}
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto relative z-10">
        <div className="max-w-3xl mx-auto px-5 py-8">
          {messages.length === 0 && !isStreaming ? (
            <div className="flex flex-col items-center justify-center min-h-[65vh] gap-10">
              {/* Hero */}
              <div className="text-center space-y-4">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center mx-auto shadow-2xl shadow-indigo-500/25 animate-float">
                  <Sparkles size={36} className="text-white" />
                </div>
                <h2 className="text-3xl font-bold text-white tracking-tight">
                  What&apos;s happening in your system?
                </h2>
                <p className="text-zinc-500 max-w-md mx-auto text-[15px] leading-relaxed">
                  Ask questions about your microservices, databases, errors, and
                  performance. I&apos;ll query live data and investigate.
                </p>
              </div>

              {/* Example questions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
                {exampleQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInput(q.text);
                      inputRef.current?.focus();
                    }}
                    className="group flex items-center gap-3 text-left px-4 py-3.5 glass rounded-xl text-sm text-zinc-300 hover:text-white hover:bg-white/[0.06] hover:border-white/[0.1] transition-all duration-200"
                  >
                    <span className="text-base">{q.icon}</span>
                    <span className="flex-1">{q.text}</span>
                    <ArrowRight size={14} className="text-zinc-600 group-hover:text-indigo-400 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}

              {/* Streaming indicator */}
              {isStreaming && (
                <div className="flex gap-4 justify-start">
                  <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                    <Loader2 size={16} className="text-white animate-spin" />
                  </div>
                  <div className="glass rounded-2xl rounded-bl-md px-5 py-4 max-w-[85%]">
                    <div className="space-y-0">
                      {streamingEvents
                        .filter((e) => e.type === "narration")
                        .map((event, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 text-zinc-400 text-sm py-1.5 px-3 my-0.5 bg-white/[0.02] rounded-lg"
                          >
                            <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse-glow" />
                            <span className="italic">
                              {event.text?.replace("NARRATION:", "").trim()}
                            </span>
                          </div>
                        ))}
                      {streamingEvents
                        .filter((e) => e.type === "tool_result")
                        .map((event, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 text-zinc-500 text-xs py-1 px-3 my-0.5"
                          >
                            <div className="w-1 h-1 rounded-full bg-emerald-400" />
                            <span>
                              {event.tool === "run_sql"
                                ? "Query executed"
                                : event.tool === "search_logs"
                                ? "Logs searched"
                                : `${event.tool}`}
                            </span>
                          </div>
                        ))}
                    </div>
                    <div className="flex items-center gap-2.5 mt-3 text-zinc-500 text-sm">
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                      <span className="text-xs">Investigating...</span>
                    </div>
                  </div>
                </div>
              )}

              {error && !isStreaming && (
                <div className="flex gap-4 justify-start">
                  <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center">
                    <span className="text-red-400 text-xs font-bold">!</span>
                  </div>
                  <div className="bg-red-500/10 border border-red-500/20 rounded-2xl rounded-bl-md px-5 py-4 max-w-[85%]">
                    <p className="text-red-300 text-sm">{error}</p>
                  </div>
                </div>
              )}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input */}
      <footer className="relative z-10 border-t border-white/[0.06] bg-[#09090b]/80 backdrop-blur-xl p-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto flex gap-3"
        >
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your system..."
              rows={1}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3.5 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/40 resize-none text-[15px] transition-all duration-200"
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 disabled:from-zinc-800 disabled:to-zinc-800 disabled:cursor-not-allowed rounded-xl flex items-center justify-center transition-all duration-200 shadow-lg shadow-indigo-500/20 disabled:shadow-none"
          >
            {isStreaming ? (
              <Loader2 size={18} className="text-white animate-spin" />
            ) : (
              <Send size={18} className="text-white" />
            )}
          </button>
        </form>
        <div className="max-w-3xl mx-auto mt-2.5 text-center text-[11px] text-zinc-600">
          Press <kbd className="px-1.5 py-0.5 bg-white/5 rounded text-zinc-400 font-mono text-[10px]">Enter</kbd> to send · <kbd className="px-1.5 py-0.5 bg-white/5 rounded text-zinc-400 font-mono text-[10px]">Shift+Enter</kbd> for new line
        </div>
      </footer>
    </div>
  );
}
