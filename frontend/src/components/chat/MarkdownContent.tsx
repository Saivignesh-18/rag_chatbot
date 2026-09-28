import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// Tailwind-styled renderers (no typography plugin needed).
// Prose uses semantic tokens so it adapts to light/dark; code keeps a
// fixed dark "editor" look in both themes for a consistent, readable feel.
const components: Components = {
  p: ({ children }) => <p className="mb-3 leading-relaxed last:mb-0">{children}</p>,
  h1: ({ children }) => <h1 className="mb-3 mt-1 text-lg font-bold text-content">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-2 mt-3 text-base font-bold text-content">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-2 mt-3 text-sm font-semibold text-content">{children}</h3>,
  ul: ({ children }) => <ul className="mb-3 ml-5 list-disc space-y-1 last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="mb-3 ml-5 list-decimal space-y-1 last:mb-0">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed marker:text-subtle">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-content">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-accent underline decoration-brand-400/40 underline-offset-2 hover:text-brand-500"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mb-3 border-l-2 border-brand-400/50 pl-3 text-muted">{children}</blockquote>
  ),
  code: ({ className, children }) => {
    const isBlock = (className ?? "").includes("language-");
    if (isBlock) {
      return <code className={`${className} block`}>{children}</code>;
    }
    return (
      <code className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[0.85em] text-brand-200">
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="mb-3 overflow-x-auto rounded-lg border border-slate-700 bg-slate-900 p-3 font-mono text-xs text-slate-200 last:mb-0">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="mb-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-line bg-card2 px-2 py-1 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => <td className="border border-line px-2 py-1">{children}</td>,
};

export default function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="text-sm text-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
