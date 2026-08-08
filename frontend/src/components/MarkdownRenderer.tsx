"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Props {
  content: string;
}

export function MarkdownRenderer({ content }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-xl font-bold text-white mt-5 mb-2.5 tracking-tight">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-lg font-semibold text-white mt-4 mb-2 tracking-tight">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-[15px] font-semibold text-zinc-200 mt-3 mb-1.5">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="text-zinc-300 leading-relaxed mb-3 text-[14px]">{children}</p>
        ),
        strong: ({ children }) => (
          <strong className="text-white font-semibold">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="text-zinc-400 italic">{children}</em>
        ),
        ul: ({ children }) => (
          <ul className="list-none space-y-1.5 mb-3 text-zinc-300">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-inside space-y-1.5 mb-3 text-zinc-300">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="ml-1 flex items-start gap-2">
            <span className="text-indigo-400 mt-1.5 text-[8px]">●</span>
            <span>{children}</span>
          </li>
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 decoration-indigo-400/30 hover:decoration-indigo-300/50 transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-indigo-500/50 pl-4 py-2 my-3 bg-indigo-500/5 rounded-r-lg text-zinc-400 text-[14px]">
            {children}
          </blockquote>
        ),
        code: ({ children, className, ...rest }) => {
          const match = /language-(\w+)/.exec(className || "");
          const isInline = !className;

          if (isInline) {
            return (
              <code
                className="bg-white/[0.06] text-indigo-300 px-1.5 py-0.5 rounded text-[13px] font-mono"
                {...rest}
              >
                {children}
              </code>
            );
          }

          return match ? (
            <div className="my-3 rounded-xl overflow-hidden border border-white/[0.06]">
              <div className="bg-white/[0.03] px-4 py-2 text-[11px] text-zinc-500 font-mono border-b border-white/[0.04] flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-500/50" />
                <div className="w-2 h-2 rounded-full bg-yellow-500/50" />
                <div className="w-2 h-2 rounded-full bg-green-500/50" />
                <span className="ml-2">{match[1]}</span>
              </div>
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                customStyle={{
                  margin: 0,
                  borderRadius: 0,
                  fontSize: "0.8125rem",
                  background: "rgba(0,0,0,0.3)",
                }}
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            </div>
          ) : (
            <code className="bg-white/[0.06] text-indigo-300 px-1.5 py-0.5 rounded text-[13px] font-mono block p-3 overflow-x-auto">
              {children}
            </code>
          );
        },
        table: ({ children }) => (
          <div className="my-4 overflow-x-auto rounded-xl border border-white/[0.06]">
            <table className="w-full text-[13px]">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-white/[0.03] border-b border-white/[0.06]">{children}</thead>
        ),
        tbody: ({ children }) => (
          <tbody className="divide-y divide-white/[0.04]">{children}</tbody>
        ),
        tr: ({ children }) => (
          <tr className="hover:bg-white/[0.02] transition-colors">{children}</tr>
        ),
        th: ({ children }) => (
          <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-4 py-2.5 text-zinc-300">{children}</td>
        ),
        hr: () => <hr className="border-white/[0.06] my-5" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
