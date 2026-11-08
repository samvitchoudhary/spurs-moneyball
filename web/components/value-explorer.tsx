"use client";

import { useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ValueScatter, type ScatterPoint } from "@/components/charts/value-scatter";
import { MethodDrawer } from "@/components/method-drawer";
import { SectionHeader } from "@/components/section-header";
import type { ModelMetrics } from "@/lib/types";

const GROUPS = ["CB", "FB", "CM", "AM_W", "ST"] as const;

const LABEL: Record<string, string> = {
  CB: "Centre-back",
  FB: "Full-back",
  CM: "Central midfield",
  AM_W: "Wide attacker",
  ST: "Striker",
};

const MODEL: Record<string, string> = {
  ridge: "Ridge",
  gradient_boosting: "Gradient boosting",
};

const SPLIT: Record<string, string> = {
  grouped_by_player: "Grouped by player",
  time_split_2025_26: "2025-26 time split",
};

export function ValueExplorer({ metrics, points }: { metrics: ModelMetrics; points: ScatterPoint[] }) {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("group");
  const group = GROUPS.includes(requested as (typeof GROUPS)[number]) ? requested! : "All";
  const shown = useMemo(
    () => (group === "All" ? points : points.filter((point) => point.positionGroup === group)),
    [points, group],
  );

  function selectGroup(next: string) {
    router.push(next === "All" ? "/value" : `/value?group=${next}`);
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <SectionHeader
        eyebrow="What the fee should be"
        title="Pricing players from their stats"
        dek="Each point is a 2025-26 season the model did not train on. Log axes, so a doubling takes the same space at every price."
      />
      <div className="mt-8 overflow-x-auto">
        <table className="w-full min-w-[36rem] text-sm">
          <thead>
            <tr className="border-b border-[#E4E0D6] text-left text-xs text-[#3A4256]">
              <th className="py-2 pr-4 font-medium">Model</th>
              <th className="py-2 pr-4 font-medium">Test</th>
              <th className="py-2 pr-4 text-right font-medium">R²</th>
              <th className="py-2 pr-4 text-right font-medium">MAE (log)</th>
              <th className="py-2 text-right font-medium">Median error</th>
            </tr>
          </thead>
          <tbody>
            {metrics.rows.map((row) => {
              const kept = row.model === metrics.keptModel;
              return (
                <tr key={`${row.model}-${row.split}`} className={kept ? "bg-[#F4E8D4]" : undefined}>
                  <td className="py-2 pr-4 text-[#132257]">{MODEL[row.model] ?? row.model}</td>
                  <td className="py-2 pr-4 text-[#3A4256]">{SPLIT[row.split] ?? row.split}</td>
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{row.r2.toFixed(3)}</td>
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{row.mae_log.toFixed(3)}</td>
                  <td className="py-2 text-right tabular text-[#132257]">{row.median_pct_error.toFixed(1)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="mt-3 max-w-2xl text-sm text-[#3A4256]">{metrics.keptReason}</p>
      </div>
      <div className="mt-8 flex flex-wrap gap-2" role="tablist" aria-label="Position group">
        {["All", ...GROUPS].map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={item === group}
            className={
              item === group
                ? "rounded-full bg-[#132257] px-3 py-1.5 text-sm text-white"
                : "rounded-full border border-[#E4E0D6] bg-white px-3 py-1.5 text-sm text-[#132257]"
            }
            onClick={() => selectGroup(item)}
          >
            {item === "All" ? "All" : LABEL[item]}
          </button>
        ))}
      </div>
      <div className="mt-4">
        <ValueScatter points={shown} onOpen={(id) => router.push(`/player?id=${id}`)} />
      </div>
      <MethodDrawer title="How this works">
        <p>The model prices a season from age, minutes, league, position, playing style, per-90 actions, and the strength of the team around the player.</p>
        <p>It leaves out the previous market value. That figure is the thing being predicted, and using it would let the model copy last year’s fee instead of pricing the stats.</p>
        <p>Contract dates are left out too. They come from one July 2026 snapshot, so a renewal signed later would leak into earlier seasons.</p>
        <p>Each point is an out-of-fold prediction: the fit never saw that player.</p>
      </MethodDrawer>
    </div>
  );
}
