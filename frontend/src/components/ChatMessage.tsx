"use client";

import { Message } from "@/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import {
  User,
  Bot,
  Database,
  Clock,
  ChevronDown,
  ChevronRight,
  Search,
  Activity,
  Layers,
  BarChart3,
} from "lucide-react";
import { useState } from "react";

interface Props {
  message: Message;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3.5 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/15">
          <Bot size={16} className="text-white" />
        </div>
      )}

      <div
        className={`max-w-[82%] ${
          isUser
            ? "bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-2xl rounded-br-md px-5 py-3 shadow-lg shadow-indigo-500/15"
            : "glass rounded-2xl rounded-bl-md px-5 py-4"
        }`}
      >
        {isUser ? (
          <p className="text-[14px] leading-relaxed">{message.content}</p>
        ) : (
          <div className="space-y-0">
            {/* Narrations */}
            {message.events
              ?.filter((e) => e.type === "narration")
              .map((event, i) => (
                <NarrationBubble key={i} text={event.text || ""} />
              ))}

            {/* Tool calls */}
            {message.events
              ?.filter((e) => e.type === "tool_result")
              .map((event, i) => (
                <ToolCallBubble
                  key={i}
                  tool={event.tool || ""}
                  input={event.input}
                  result={event.result}
                />
              ))}

            {/* Final answer */}
            {message.content && (
              <div className="mt-3">
                <MarkdownRenderer content={message.content} />
              </div>
            )}
          </div>
        )}

        <div
          className={`text-[10px] mt-2.5 font-medium ${
            isUser ? "text-white/50" : "text-zinc-600"
          }`}
        >
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-white/[0.06] border border-white/[0.08] flex items-center justify-center">
          <User size={16} className="text-zinc-400" />
        </div>
      )}
    </div>
  );
}

function NarrationBubble({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 text-zinc-500 text-[13px] py-2 px-3 my-1 bg-white/[0.02] rounded-lg">
      <Clock size={12} className="text-indigo-400 flex-shrink-0" />
      <span className="italic">{text.replace("NARRATION:", "").trim()}</span>
    </div>
  );
}

function ToolCallBubble({
  tool,
  input,
  result,
}: {
  tool: string;
  input?: Record<string, unknown>;
  result?: unknown;
}) {
  const [expanded, setExpanded] = useState(false);

  const toolConfig = {
    run_sql: { icon: <Database size={12} />, label: "SQL Query", color: "text-emerald-400" },
    search_logs: { icon: <Search size={12} />, label: "Log Search", color: "text-amber-400" },
    list_streams: { icon: <Layers size={12} />, label: "List Streams", color: "text-purple-400" },
    get_metrics: { icon: <BarChart3 size={12} />, label: "Metrics", color: "text-blue-400" },
    get_service_graph: { icon: <Activity size={12} />, label: "Service Graph", color: "text-pink-400" },
  }[tool] || { icon: <Activity size={12} />, label: tool, color: "text-zinc-400" };

  const sqlQuery = input?.sql ? String(input.sql) : null;

  return (
    <div className="my-1.5 bg-white/[0.02] rounded-xl border border-white/[0.04] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3.5 py-2.5 hover:bg-white/[0.03] transition-colors text-left group"
      >
        {expanded ? (
          <ChevronDown size={13} className="text-zinc-600" />
        ) : (
          <ChevronRight size={13} className="text-zinc-600" />
        )}
        <span className={toolConfig.color}>{toolConfig.icon}</span>
        <span className="text-[12px] font-medium text-zinc-400">{toolConfig.label}</span>
        {sqlQuery && (
          <span className="text-[11px] text-zinc-600 truncate ml-1 flex-1 font-mono">
            {sqlQuery.slice(0, 50)}
            {sqlQuery.length > 50 ? "..." : ""}
          </span>
        )}
      </button>

      {expanded && (
        <div className="border-t border-white/[0.04] p-3.5 space-y-3">
          {input && (
            <div>
              <div className="text-[10px] text-zinc-600 uppercase tracking-wider font-semibold mb-1.5">
                Query
              </div>
              <pre className="text-[12px] text-zinc-300 bg-black/30 rounded-lg p-3 overflow-x-auto font-mono leading-relaxed">
                {sqlQuery || JSON.stringify(input, null, 2)}
              </pre>
            </div>
          )}
          {result !== undefined && result !== null && (
            <div>
              <div className="text-[10px] text-zinc-600 uppercase tracking-wider font-semibold mb-1.5">
                Result
              </div>
              <pre className="text-[12px] text-zinc-300 bg-black/30 rounded-lg p-3 overflow-x-auto max-h-64 font-mono leading-relaxed">
                {typeof result === "string"
                  ? result
                  : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
