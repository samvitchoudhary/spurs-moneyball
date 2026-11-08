"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bar, BarChart, Cell, LabelList, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from "recharts";

import { ValueScatter, type ScatterPoint } from "@/components/charts/value-scatter";
import { PlayerChip } from "@/components/player-chip";
import { MethodDrawer } from "@/components/method-drawer";
import { SectionHeader } from "@/components/section-header";
import { formatAge, formatEuro } from "@/lib/format";
import type { Decile, ModelMetrics } from "@/lib/types";

type ValuePoint = ScatterPoint & {
  calibratedGap: number | null;
  position: string;
  team: string;
  age: number | null;
};

function formatGap(value: number) {
  const rounded = Number(value.toFixed(3));
  const text = `${rounded > 0 ? "+" : ""}${rounded}`;
  return text.replace("-", "−");
}

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

export function ValueExplorer({ metrics, points, deciles }: { metrics: ModelMetrics; points: ValuePoint[]; deciles: Decile[] }) {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("group");
  const group = GROUPS.includes(requested as (typeof GROUPS)[number]) ? requested! : "All";
  const [maxAge, setMaxAge] = useState(27);
  const [minMillions, setMinMillions] = useState(2);
  const shown = useMemo(
    () => (group === "All" ? points : points.filter((point) => point.positionGroup === group)),
    [points, group],
  );
  const ranked = useMemo(() => {
    const minValue = minMillions * 1_000_000;
    return shown
      .filter((point) => point.calibratedGap != null && point.age != null && point.age <= maxAge && point.actual >= minValue)
      .sort((a, b) => (b.calibratedGap ?? 0) - (a.calibratedGap ?? 0) || a.name.localeCompare(b.name));
  }, [shown, maxAge, minMillions]);
  const top = ranked.slice(0, 15);
  const bars = [...deciles]
    .sort((a, b) => a.decile - b.decile)
    .map((row) => ({ decile: String(row.decile), gap: row.meanLogGap ?? 0 }));

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
      <div className="mt-10">
        <h2 className="font-serif text-2xl text-[#132257]">Where the model leans</h2>
        <div className="mt-4 h-56 w-full min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bars} margin={{ top: 16, right: 8, bottom: 8, left: 8 }}>
              <XAxis dataKey="decile" tick={{ fontSize: 12, fill: "#3A4256" }} />
              <YAxis tick={{ fontSize: 12, fill: "#3A4256" }} width={40} />
              <ReferenceLine y={0} stroke="#132257" />
              <Bar dataKey="gap" isAnimationActive={false}>
                {bars.map((row) => (
                  <Cell key={row.decile} fill={row.gap >= 0 ? "#132257" : "#9A7B3C"} />
                ))}
                <LabelList dataKey="gap" position="top" formatter={(value) => formatGap(Number(value))} style={{ fontSize: 11, fill: "#3A4256" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 max-w-2xl text-sm text-[#3A4256]">Cheap players were over-predicted and expensive ones under-predicted, so rankings compare each player only against others at a similar price.</p>
      </div>
      <div className="mt-10">
        <h2 className="font-serif text-2xl text-[#132257]">Largest gaps at a similar price</h2>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-[#132257]">
          <label>
            Max age
            <input
              type="number"
              min={17}
              max={40}
              value={maxAge}
              onChange={(event) => setMaxAge(Number(event.target.value))}
              className="ml-2 w-20 rounded-lg border border-[#E4E0D6] bg-white px-2 py-1 tabular"
            />
          </label>
          <label>
            Min value, €m
            <input
              type="number"
              min={0}
              step={0.5}
              value={minMillions}
              onChange={(event) => setMinMillions(Number(event.target.value))}
              className="ml-2 w-20 rounded-lg border border-[#E4E0D6] bg-white px-2 py-1 tabular"
            />
          </label>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[44rem] text-sm">
            <thead>
              <tr className="border-b border-[#E4E0D6] text-left text-xs text-[#3A4256]">
                <th className="py-2 pr-4 font-medium">Player</th>
                <th className="py-2 pr-4 font-medium">Club</th>
                <th className="py-2 pr-4 font-medium">Age</th>
                <th className="py-2 pr-4 font-medium">Position</th>
                <th className="py-2 pr-4 text-right font-medium">Market</th>
                <th className="py-2 pr-4 text-right font-medium">Model</th>
                <th className="py-2 text-right font-medium">Gap (×)</th>
              </tr>
            </thead>
            <tbody>
              {top.map((row) => (
                <tr key={row.id} className="border-b border-[#E4E0D6]">
                  <td className="py-2 pr-4"><PlayerChip id={row.id} name={row.name} positionGroup={row.positionGroup} /></td>
                  <td className="py-2 pr-4 text-[#3A4256]">{row.team}</td>
                  <td className="py-2 pr-4 tabular text-[#132257]">{formatAge(row.age)}</td>
                  <td className="py-2 pr-4 text-[#3A4256]">{row.position}</td>
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{formatEuro(row.actual)}</td>
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{formatEuro(row.predicted)}</td>
                  <td className="py-2 text-right tabular text-[#132257]">{formatGap(row.calibratedGap ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-[#3A4256]">Showing {top.length} of {ranked.length}</p>
        <p className="mt-2 max-w-2xl text-sm text-[#3A4256]">A scout&apos;s shortlist, not a verdict. The market knows things the model can&apos;t see (injuries, wages, contracts).</p>
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
