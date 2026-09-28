import { motion } from "framer-motion";
import { BookOpen, Quote, X } from "lucide-react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import EmptyState from "@/components/common/EmptyState";
import { listStagger } from "@/lib/motion";
import type { Source } from "@/types";
import SourceCitation from "./SourceCitation";

function RelevanceChart({ sources }: { sources: Source[] }) {
  const data = sources.map((s, i) => ({
    name: `[${i + 1}]`,
    label: `${s.document_name}${s.page_number ? ` p${s.page_number}` : ""}`,
    value: Math.round(s.similarity_score * 100),
  }));

  return (
    <div className="mb-4 rounded-xl border border-line bg-card p-3">
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-subtle">
        Relevance by source
      </p>
      <ResponsiveContainer width="100%" height={Math.max(90, data.length * 30)}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="name"
            width={28}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            contentStyle={{
              background: "#111827",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number, _n, item) => [`${value}%`, (item?.payload as { label: string })?.label]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={12}>
            {data.map((_, i) => (
              <Cell key={i} fill="#6366f1" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function SourcePanel({ sources, onClose }: { sources: Source[]; onClose?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-start justify-between border-b border-line px-4 py-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-content">
            <Quote size={16} className="text-accent" aria-hidden /> Sources
            {sources.length > 0 && (
              <span className="rounded-full bg-card2 px-2 py-0.5 text-[11px] text-muted">
                {sources.length}
              </span>
            )}
          </h2>
          <p className="mt-0.5 text-[11px] text-subtle">Verified passages from your documents</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted transition hover:bg-card2 hover:text-content lg:hidden"
            aria-label="Close sources"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {sources.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No sources yet"
            description="Ask a question to see the exact passages used to answer it."
          />
        ) : (
          <>
            {sources.length >= 2 && <RelevanceChart sources={sources} />}
            <motion.div variants={listStagger} initial="hidden" animate="show" className="space-y-2.5">
              {sources.map((s, i) => (
                <SourceCitation key={s.chunk_id} source={s} index={i + 1} />
              ))}
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
