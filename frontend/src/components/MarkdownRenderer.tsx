"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy } from "lucide-react";
import { useState } from "react";

interface Props {
  content: string;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors p-1.5 rounded-md hover:bg-[var(--bg-tertiary)]"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

export function MarkdownRenderer({ content }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-xl font-bold text-[var(--text-primary)] mt-6 mb-3 tracking-tight leading-tight">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mt-5 mb-2.5 tracking-tight leading-tight">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-[15px] font-semibold text-[var(--text-primary)] mt-4 mb-2 leading-tight">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="text-[14px] text-[var(--text-secondary)] leading-relaxed mb-3 last:mb-0">
            {children}
          </p>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-[var(--text-primary)]">
            {children}
          </strong>
        ),
        em: ({ children }) => (
          <em className="text-[var(--text-secondary)] italic">{children}</em>
        ),
        ul: ({ children }) => (
          <ul className="space-y-1.5 mb-3 text-[14px]">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-inside space-y-1.5 mb-3 text-[14px] text-[var(--text-secondary)]">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="flex items-start gap-2.5 text-[var(--text-secondary)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--brand-primary)] mt-2 flex-shrink-0" />
            <span className="flex-1">{children}</span>
          </li>
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            className="text-[var(--brand-primary)] hover:text-[var(--brand-secondary)] font-medium underline underline-offset-2 decoration-[var(--brand-muted)] hover:decoration-[var(--brand-primary)] transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-[var(--brand-primary)] pl-4 py-1 my-4 bg-[var(--brand-light)] rounded-r-lg text-[var(--text-secondary)] text-[14px]">
            {children}
          </blockquote>
        ),
        code: ({ children, className, ...rest }) => {
          const match = /language-(\w+)/.exec(className || "");
          const isInline = !className;
          const codeString = String(children).replace(/\n$/, "");

          if (isInline) {
            return (
              <code
                className="bg-[var(--bg-tertiary)] text-[var(--brand-primary)] px-1.5 py-0.5 rounded-md text-[13px] font-mono font-medium"
                {...rest}
              >
                {children}
              </code>
            );
          }

          return match ? (
            <div className="code-block my-4">
              <div className="code-block-header flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                    <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
                  </div>
                  <span className="text-[12px] text-[var(--text-tertiary)]">{match[1]}</span>
                </div>
                <CopyButton text={codeString} />
              </div>
              <SyntaxHighlighter
                style={oneLight}
                language={match[1]}
                PreTag="div"
                customStyle={{
                  margin: 0,
                  borderRadius: 0,
                  fontSize: "13px",
                  background: "var(--bg-secondary)",
                  padding: "14px",
                }}
              >
                {codeString}
              </SyntaxHighlighter>
            </div>
          ) : (
            <code className="code-block">
              <code className="code-block-content font-mono">
                {children}
              </code>
            </code>
          );
        },
        table: ({ children }) => (
          <div className="my-4 overflow-x-auto rounded-xl border border-[var(--border-light)]">
            <table className="w-full text-[13px]">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-[var(--bg-tertiary)] border-b border-[var(--border-light)]">
            {children}
          </thead>
        ),
        tbody: ({ children }) => (
          <tbody className="divide-y divide-[var(--border-light)]">{children}</tbody>
        ),
        tr: ({ children }) => (
          <tr className="hover:bg-[var(--bg-secondary)] transition-colors">{children}</tr>
        ),
        th: ({ children }) => (
          <th className="px-4 py-3 text-left text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-4 py-3 text-[var(--text-secondary)]">{children}</td>
        ),
        hr: () => <hr className="border-[var(--border-light)] my-6" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}