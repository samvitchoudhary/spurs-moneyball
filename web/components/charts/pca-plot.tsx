"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ResponsiveContainer, Scatter, ScatterChart, XAxis, YAxis } from "recharts";

import { PlayerChip } from "@/components/player-chip";
import { positionColor } from "@/lib/positions";
import type { PcaPoint, Player } from "@/lib/types";

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

const STYLE_COLORS = ["#3D5A80", "#1F6F5B", "#A15C12", "#6E4C7A", "#9A3E32", "#5E656B"];

type StyleDot = {
  id: string;
  name: string;
  x: number;
  y: number;
  style: string;
  positionGroup: string;
  spurs: boolean;
  fill: string;
};

function StyleMark({
  cx,
  cy,
  payload,
  onHover,
  onOpen,
}: {
  cx?: number;
  cy?: number;
  payload?: StyleDot;
  onHover: (dot: StyleDot) => void;
  onOpen: (id: string) => void;
}) {
  if (cx == null || cy == null || !payload) return null;
  return (
    <g style={{ cursor: "pointer" }} onMouseEnter={() => onHover(payload)} onClick={() => onOpen(payload.id)}>
      <circle
        cx={cx}
        cy={cy}
        r={payload.spurs ? 7 : 4}
        fill={payload.fill}
        fillOpacity={payload.spurs ? 1 : 0.8}
        stroke={payload.spurs ? "#132257" : "none"}
        strokeWidth={payload.spurs ? 1.5 : 0}
      />
      {payload.spurs ? (
        <text x={cx + 9} y={cy + 4} fontSize={11} fill="#132257">
          {payload.name}
        </text>
      ) : null}
    </g>
  );
}

export function StyleMap({
  points,
  players,
  positionGroup,
  spursIds,
}: {
  points: PcaPoint[];
  players: Player[];
  positionGroup: string;
  spursIds: Set<string>;
}) {
  const router = useRouter();
  const [active, setActive] = useState<StyleDot | null>(null);
  const byId = useMemo(() => new Map(players.map((player) => [player.id, player])), [players]);
  const styles = [...new Set(points.map((point) => point.style || "Unlabelled"))].sort();
  const colorOf = new Map(styles.map((style, index) => [style, STYLE_COLORS[index % STYLE_COLORS.length]]));
  const data: StyleDot[] = points.map((point) => {
    const player = byId.get(point.id);
    const style = point.style || "Unlabelled";
    return {
      id: point.id,
      name: player?.name ?? point.id,
      x: point.x,
      y: point.y,
      style,
      positionGroup,
      spurs: spursIds.has(point.id),
      fill: colorOf.get(style) ?? "#5E656B",
    };
  });

  return (
    <div>
      <div className="h-96 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 80, bottom: 8, left: 8 }}>
            <XAxis dataKey="x" type="number" hide />
            <YAxis dataKey="y" type="number" hide />
            <Scatter
              data={data}
              isAnimationActive={false}
              shape={(props: unknown) => (
                <StyleMark
                  {...(props as object)}
                  onHover={setActive}
                  onOpen={(id) => router.push(`/player?id=${id}`)}
                />
              )}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#3A4256]">
        {styles.map((style) => (
          <span key={style} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: colorOf.get(style) }} />
            {style}
          </span>
        ))}
      </div>
      <div className="mt-3 min-h-8 text-sm">
        {active ? <PlayerChip id={active.id} name={active.name} positionGroup={active.positionGroup} /> : <span className="text-[#3A4256]">Hover a point.</span>}
      </div>
    </div>
  );
}
