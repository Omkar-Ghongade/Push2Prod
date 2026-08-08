"use client";

import { Message } from "@/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import {
  User,
  Database,
  ChevronDown,
  ChevronRight,
  Search,
  Activity,
  Layers,
  BarChart3,
  Terminal,
  Check,
  Copy,
} from "lucide-react";
import { useState } from "react";

interface Props {
  message: Message;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className="animate-fade-in">
      <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
        {/* Avatar */}
        <div className={`avatar ${isUser ? "avatar-neutral" : "avatar-brand"}`}>
          {isUser ? <User size={16} /> : <Terminal size={16} />}
        </div>

        {/* Message Content */}
        <div className={`flex-1 ${isUser ? "flex justify-end" : ""}`}>
          <div className={isUser ? "message-user max-w-[85%]" : "message-assistant"}>
            {isUser ? (
              <p className="text-[14px] leading-relaxed">{message.content}</p>
            ) : (
              <div className="space-y-3">
                {/* Tool calls - show before the answer */}
                {message.events && message.events.filter((e) => e.type === "tool_result").length > 0 && (
                  <div className="space-y-2">
                    {message.events
                      .filter((e) => e.type === "tool_result")
                      .map((event, i) => (
                        <ToolCallCard
                          key={i}
                          tool={event.tool || ""}
                          input={event.input}
                          result={event.result}
                        />
                      ))}
                  </div>
                )}

                {/* Final answer */}
                {message.content && (
                  <div className="prose-container">
                    <MarkdownRenderer content={message.content} />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Timestamp */}
          <div className={`text-[11px] text-[var(--text-tertiary)] mt-1.5 ${isUser ? "text-right" : ""}`}>
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolCallCard({
  tool,
  input,
  result,
}: {
  tool: string;
  input?: Record<string, unknown>;
  result?: unknown;
}) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const toolConfig: Record<string, { icon: React.ReactNode; label: string; color: string; bg: string }> = {
    run_sql: { 
      icon: <Database size={14} />, 
      label: "SQL Query", 
      color: "text-emerald-600",
      bg: "bg-emerald-50"
    },
    search_logs: { 
      icon: <Search size={14} />, 
      label: "Log Search", 
      color: "text-amber-600",
      bg: "bg-amber-50"
    },
    list_streams: { 
      icon: <Layers size={14} />, 
      label: "List Streams", 
      color: "text-purple-600",
      bg: "bg-purple-50"
    },
    get_metrics: { 
      icon: <BarChart3 size={14} />, 
      label: "Metrics", 
      color: "text-blue-600",
      bg: "bg-blue-50"
    },
    get_service_graph: { 
      icon: <Activity size={14} />, 
      label: "Service Graph", 
      color: "text-pink-600",
      bg: "bg-pink-50"
    },
  };

  const config = toolConfig[tool] || { 
    icon: <Activity size={14} />, 
    label: tool, 
    color: "text-gray-600",
    bg: "bg-gray-50"
  };

  const sqlQuery = input?.sql ? String(input.sql) : null;

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="tool-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="tool-card-header w-full"
      >
        {expanded ? (
          <ChevronDown size={14} className="text-[var(--text-tertiary)]" />
        ) : (
          <ChevronRight size={14} className="text-[var(--text-tertiary)]" />
        )}
        
        <div className={`w-7 h-7 rounded-lg ${config.bg} flex items-center justify-center`}>
          <span className={config.color}>{config.icon}</span>
        </div>
        
        <span className="text-[13px] font-medium text-[var(--text-primary)]">
          {config.label}
        </span>
        
        {sqlQuery && (
          <span className="text-[12px] text-[var(--text-tertiary)] truncate ml-auto max-w-[200px] font-mono">
            {sqlQuery.slice(0, 40)}
            {sqlQuery.length > 40 ? "..." : ""}
          </span>
        )}
        
        <div className="badge badge-success ml-auto !py-0.5">
          <Check size={10} />
          Done
        </div>
      </button>

      {expanded && (
        <div className="tool-card-content space-y-4">
          {/* Query Input */}
          {input && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
                  Query
                </span>
                <button
                  onClick={() => handleCopy(sqlQuery || JSON.stringify(input, null, 2))}
                  className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors p-1"
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                </button>
              </div>
              <pre className="code-block">
                <code className="code-block-content text-[var(--text-primary)] font-mono">
                  {sqlQuery || JSON.stringify(input, null, 2)}
                </code>
              </pre>
            </div>
          )}

          {/* Result */}
          {result !== undefined && result !== null && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
                  Result
                </span>
                <button
                  onClick={() => handleCopy(typeof result === "string" ? result : JSON.stringify(result, null, 2))}
                  className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors p-1"
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                </button>
              </div>
              <pre className="code-block max-h-64 overflow-y-auto">
                <code className="code-block-content text-[var(--text-primary)] font-mono">
                  {typeof result === "string"
                    ? result
                    : JSON.stringify(result, null, 2)}
                </code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}