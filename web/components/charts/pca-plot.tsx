"use client";

import { ResponsiveContainer, Scatter, ScatterChart, XAxis, YAxis } from "recharts";

import { positionColor } from "@/lib/positions";
import type { PcaPoint } from "@/lib/types";

function dots(points: PcaPoint[]) {
  return points.map((point) => ({ x: point.x, y: point.y }));
}

export function PcaPlot({ points, highlight, positionGroup }: { points: PcaPoint[]; highlight: string; positionGroup: string }) {
  const others = dots(points.filter((point) => point.id !== highlight));
  const self = dots(points.filter((point) => point.id === highlight));
  const color = positionColor(positionGroup);
  return (
    <div className="h-64 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <XAxis dataKey="x" type="number" hide />
          <YAxis dataKey="y" type="number" hide />
          <Scatter data={others} fill={color} fillOpacity={0.28} isAnimationActive={false} />
          <Scatter data={self} fill="#132257" isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
