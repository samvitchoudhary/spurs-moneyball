"use client";

import { useState } from "react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, XAxis, YAxis } from "recharts";

import { PlayerChip } from "@/components/player-chip";
import { formatEuro } from "@/lib/format";

export type ScatterPoint = {
  id: string;
  actual: number;
  predicted: number;
  name: string;
  positionGroup: string;
};

function Dot({
  cx,
  cy,
  payload,
  onPick,
}: {
  cx?: number;
  cy?: number;
  payload?: ScatterPoint;
  onPick: (point: ScatterPoint) => void;
}) {
  if (cx == null || cy == null || payload == null) return null;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={4}
      fill="#132257"
      fillOpacity={0.4}
      onMouseEnter={() => onPick(payload)}
      onClick={() => onPick(payload)}
    />
  );
}

export function ValueScatter({ points }: { points: ScatterPoint[] }) {
  const data = points.filter((point) => point.actual > 0 && point.predicted > 0);
  const [active, setActive] = useState<ScatterPoint | null>(null);

  return (
    <div className="w-full min-w-0">
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#E4E0D6" />
            <XAxis
              dataKey="actual"
              type="number"
              scale="log"
              domain={[100000, 200000000]}
              ticks={[1000000, 10000000, 100000000]}
              tickFormatter={(value) => formatEuro(Number(value))}
              name="Market value"
              stroke="#3A4256"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              dataKey="predicted"
              type="number"
              scale="log"
              domain={[100000, 200000000]}
              ticks={[1000000, 10000000, 100000000]}
              tickFormatter={(value) => formatEuro(Number(value))}
              name="Model value"
              width={56}
              stroke="#3A4256"
              tick={{ fontSize: 12 }}
            />
            <Scatter
              data={data}
              isAnimationActive={false}
              shape={(props: unknown) => <Dot {...(props as object)} onPick={setActive} />}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 min-h-8 text-sm text-[#3A4256]">
        {active ? (
          <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
            <PlayerChip id={active.id} name={active.name} positionGroup={active.positionGroup} />
            <span className="tabular">
              Market {formatEuro(active.actual)} · model {formatEuro(active.predicted)}
            </span>
          </span>
        ) : (
          "Hover a point, or tap one on a phone."
        )}
      </div>
    </div>
  );
}
