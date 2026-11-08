"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Need } from "@/lib/types";

export function NeedsBars({ needs }: { needs: Need[] }) {
  const data = needs.map((need) => ({
    position: need.positionGroup === "FB" ? "Left-back" : need.position,
    needScore: need.needScore,
    positionGroup: need.positionGroup,
  }));
  return (
    <div className="h-72 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <XAxis type="number" domain={[-0.6, 0.9]} tick={{ fontSize: 12, fill: "#3A4256" }} />
          <YAxis type="category" dataKey="position" width={92} tick={{ fontSize: 13, fill: "#132257" }} />
          <Tooltip formatter={(value) => Number(value).toFixed(2)} />
          <Bar dataKey="needScore" isAnimationActive={false} radius={[0, 4, 4, 0]}>
            {data.map((need) => (
              <Cell key={need.positionGroup} fill={need.positionGroup === "ST" || need.positionGroup === "FB" ? "#9A7B3C" : "#D9D3C7"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
