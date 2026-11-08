import { formatPercentile } from "@/lib/format";

export function StatBar({ label, value, color = "#132257" }: { label: string; value: number | null; color?: string }) {
  const width = value == null ? 0 : Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
        <span className="text-[#1C2333]">{label}</span>
        <span className="tabular text-[#132257]">{formatPercentile(value)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#E7E4DC]" aria-hidden>
        <div className="h-full rounded-full" style={{ width: `${width}%`, background: color }} />
      </div>
    </div>
  );
}
