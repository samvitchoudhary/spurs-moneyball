"use client";

import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ShortlistRow } from "@/lib/types";

const PARTS = [
  { key: "Value", weight: 0.4, fill: "#132257" },
  { key: "Style", weight: 0.3, fill: "#6E4C7A" },
  { key: "Form", weight: 0.2, fill: "#9A7B3C" },
  { key: "Reliability", weight: 0.1, fill: "#1F6F5B" },
] as const;

export function ShortlistBars({ rows }: { rows: ShortlistRow[] }) {
  const data = [...rows]
    .sort((a, b) => a.rank - b.rank)
    .slice(0, 10)
    .map((row) => ({
      name: row.name,
      Value: weighted(row.valuePercentile, 0.4),
      Style: weighted(row.stylePercentile, 0.3),
      Form: weighted(row.formPercentile, 0.2),
      Reliability: weighted(row.reliabilityPercentile, 0.1),
    }));

  return (
    <div className="h-[32rem] w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <XAxis type="number" tick={{ fontSize: 12, fill: "#3A4256" }} />
          <YAxis type="category" dataKey="name" width={168} tick={{ fontSize: 12, fill: "#132257" }} />
          <Tooltip formatter={(value) => Number(value).toFixed(1)} />
          <Legend />
          {PARTS.map((part) => (
            <Bar
              key={part.key}
              dataKey={part.key}
              stackId="score"
              fill={part.fill}
              isAnimationActive={false}
              radius={part.key === "Reliability" ? [0, 4, 4, 0] : undefined}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function weighted(percentile: number | null, weight: number) {
  return percentile == null ? 0 : Math.round(percentile * weight * 10) / 10;
}
