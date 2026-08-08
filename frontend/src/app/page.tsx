"use client";

import { useState, useRef, useEffect } from "react";
import { useSSE } from "@/hooks/useSSE";
import { ChatMessage } from "@/components/ChatMessage";
import { Message } from "@/types";
import { Send, Loader2, Plus, Zap, Database, AlertCircle, BarChart3, Terminal } from "lucide-react";

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const { sendMessage, events, isStreaming, answer, error, reset } = useSSE();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const lastMessageWasUser = useRef(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, events, isStreaming]);

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
    lastMessageWasUser.current = true;

    await sendMessage(q);
  };

  useEffect(() => {
    if (!isStreaming && lastMessageWasUser.current && (answer || error)) {
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: answer || `Error: ${error}`,
        events: events,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      lastMessageWasUser.current = false;
    }
  }, [isStreaming, answer, error, events]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const suggestions = [
    { 
      icon: Database, 
      title: "Database Health",
      query: "How is my database health?",
      color: "text-emerald-600",
      bg: "bg-emerald-50"
    },
    { 
      icon: AlertCircle, 
      title: "Service Errors",
      query: "What errors are happening in the payment service?",
      color: "text-red-600",
      bg: "bg-red-50"
    },
    { 
      icon: BarChart3, 
      title: "Request Metrics",
      query: "Show me the request rate across all services",
      color: "text-blue-600",
      bg: "bg-blue-50"
    },
    { 
      icon: Zap, 
      title: "Active Incidents",
      query: "Are there any incidents right now?",
      color: "text-amber-600",
      bg: "bg-amber-50"
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[var(--bg-primary)]/95 backdrop-blur-sm border-b border-[var(--border-light)]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center shadow-lg shadow-orange-500/20">
                <Terminal size={18} className="text-white" />
              </div>
              <div>
                <h1 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight leading-tight">
                  TraceTalk
                </h1>
                <p className="text-[11px] text-[var(--text-tertiary)] leading-tight">
                  Observability Assistant
                </p>
              </div>
            </div>

            {/* New Chat Button */}
            {messages.length > 0 && (
              <button
                onClick={() => {
                  setMessages([]);
                  reset();
                }}
                className="btn-secondary !py-2 !px-3 !text-[13px] !gap-1.5"
              >
                <Plus size={14} />
                New Chat
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
          {messages.length === 0 && !isStreaming ? (
            /* Empty State */
            <div className="empty-state min-h-[calc(100vh-200px)]">
              <div className="empty-state-icon">
                <Terminal size={32} />
              </div>
              <h2 className="empty-state-title">
                What&apos;s happening in your system?
              </h2>
              <p className="empty-state-description">
                Ask questions about your microservices, databases, errors, and performance. I&apos;ll query live data and investigate.
              </p>

              {/* Suggestions Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl mt-10">
                {suggestions.map((item, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInput(item.query);
                      inputRef.current?.focus();
                    }}
                    className="card card-interactive group text-left p-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-xl ${item.bg} flex items-center justify-center flex-shrink-0`}>
                        <item.icon size={20} className={item.color} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[13px] font-medium text-[var(--text-primary)] mb-0.5">
                          {item.title}
                        </div>
                        <div className="text-[12px] text-[var(--text-tertiary)] line-clamp-2">
                          {item.query}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Messages */
            <div className="space-y-5">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}

              {/* Streaming State */}
              {isStreaming && (
                <div className="animate-fade-in">
                  <div className="flex gap-3">
                    <div className="avatar avatar-brand">
                      <Terminal size={16} />
                    </div>
                    <div className="flex-1">
                      <div className="message-assistant">
                        {/* Narrations */}
                        {events.filter((e) => e.type === "narration").length > 0 && (
                          <div className="space-y-2 mb-4">
                            {events
                              .filter((e) => e.type === "narration")
                              .map((event, i) => (
                                <div
                                  key={i}
                                  className="flex items-center gap-2 text-[13px] text-[var(--text-secondary)]"
                                >
                                  <div className="status-dot status-dot-brand animate-pulse-soft" />
                                  <span>{event.text?.replace("NARRATION:", "").trim()}</span>
                                </div>
                              ))}
                          </div>
                        )}

                        {/* Tool Results */}
                        {events.filter((e) => e.type === "tool_result").length > 0 && (
                          <div className="space-y-1.5 mb-4">
                            {events
                              .filter((e) => e.type === "tool_result")
                              .map((event, i) => (
                                <div
                                  key={i}
                                  className="flex items-center gap-2 text-[12px]"
                                >
                                  <div className="status-dot status-dot-success" />
                                  <span className="text-[var(--text-tertiary)]">
                                    {event.tool === "run_sql"
                                      ? "SQL query executed"
                                      : event.tool === "search_logs"
                                      ? "Logs searched"
                                      : `${event.tool} completed`}
                                  </span>
                                </div>
                              ))}
                          </div>
                        )}

                        {/* Loading indicator */}
                        <div className="flex items-center gap-3">
                          <div className="loading-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                          <span className="text-[13px] text-[var(--text-tertiary)]">
                            Analyzing...
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Error State */}
              {error && !isStreaming && (
                <div className="animate-fade-in">
                  <div className="flex gap-3">
                    <div className="avatar" style={{ background: 'var(--error-light)', color: 'var(--error)' }}>
                      <AlertCircle size={16} />
                    </div>
                    <div className="flex-1 p-4 rounded-xl bg-[var(--error-light)] border border-red-200">
                      <p className="text-[14px] text-[var(--error)]">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input Area */}
      <footer className="sticky bottom-0 bg-[var(--bg-primary)]/95 backdrop-blur-sm border-t border-[var(--border-light)]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <form onSubmit={handleSubmit} className="relative">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about your system..."
                  rows={1}
                  disabled={isStreaming}
                  className="input !pr-4 resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
              <button
                type="submit"
                disabled={!input.trim() || isStreaming}
                className="btn-primary !p-0 !w-12 !h-12 flex-shrink-0"
              >
                {isStreaming ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
          </form>
          
          {/* Keyboard hints */}
          <div className="flex items-center justify-center gap-4 mt-3 text-[11px] text-[var(--text-tertiary)]">
            <span>
              <kbd className="px-1.5 py-0.5 bg-[var(--bg-tertiary)] rounded text-[10px] font-mono">Enter</kbd>
              {" "}to send
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-[var(--bg-tertiary)] rounded text-[10px] font-mono">Shift + Enter</kbd>
              {" "}for new line
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}