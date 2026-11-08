"use client";

import { useReducedMotion } from "framer-motion";
import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

import { formatSignedPercent } from "@/lib/format";
import type { BacktestWindow } from "@/lib/types";

const SERIES = [
  { key: "picks", name: "Model picks", fill: "#132257" },
  { key: "signings", name: "Spurs signings", fill: "#9A7B3C" },
  { key: "ageMatched", name: "Age-matched peers", fill: "#1F6F5B" },
] as const;

function shortWindow(label: string): string {
  return label.replace("Summer ", "S").replace("January ", "J").replace(" ", "");
}

export function BacktestDots({ windows }: { windows: BacktestWindow[] }) {
  const reduce = useReducedMotion();
  const labels = windows.map((window) => shortWindow(window.window));
  const series = SERIES.map((item) => ({
    ...item,
    data: windows.flatMap((window, index) => {
      const value = window[item.key];
      return value == null ? [] : [{ x: index, value }];
    }),
  }));

  return (
    <div className="h-80 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 8, bottom: 24, left: 8 }}>
          <CartesianGrid stroke="#E4E0D6" vertical={false} />
          <XAxis
            dataKey="x"
            type="number"
            domain={[-0.4, Math.max(windows.length - 0.6, 0.6)]}
            ticks={windows.map((_, index) => index)}
            tickFormatter={(index) => labels[Number(index)] ?? ""}
            stroke="#3A4256"
            tick={{ fontSize: 11, fill: "#3A4256" }}
          />
          <YAxis dataKey="value" tickFormatter={(value) => formatSignedPercent(Number(value))} width={48} stroke="#3A4256" tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value) => formatSignedPercent(Number(value), 1)} labelFormatter={(index) => windows[Number(index)]?.window ?? ""} />
          <Legend />
          {series.map((item) => (
            <Scatter key={item.key} name={item.name} data={item.data} fill={item.fill} isAnimationActive={!reduce} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
