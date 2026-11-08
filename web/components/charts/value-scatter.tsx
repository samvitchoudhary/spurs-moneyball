"use client";

import { useState, type MouseEvent } from "react";
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

const DOMAIN_MIN = 100_000;
const DOMAIN_MAX = 200_000_000;
const HIT_RADIUS = 16;

function valueToPixel(value: number, startPx: number, endPx: number, startValue: number, endValue: number) {
  const t = (Math.log(value) - Math.log(startValue)) / (Math.log(endValue) - Math.log(startValue));
  return startPx + t * (endPx - startPx);
}

function nearestPoint(points: ScatterPoint[], svg: SVGSVGElement, clientX: number, clientY: number): ScatterPoint | null {
  const clip = svg.querySelector("clipPath rect");
  const viewBox = svg.viewBox.baseVal;
  const bounds = svg.getBoundingClientRect();
  if (!clip || !viewBox.width || !viewBox.height || !bounds.width || !bounds.height) return null;
  const plotLeft = Number(clip.getAttribute("x"));
  const plotTop = Number(clip.getAttribute("y"));
  const plotWidth = Number(clip.getAttribute("width"));
  const plotHeight = Number(clip.getAttribute("height"));
  const x = ((clientX - bounds.left) / bounds.width) * viewBox.width;
  const y = ((clientY - bounds.top) / bounds.height) * viewBox.height;
  if (x < plotLeft || x > plotLeft + plotWidth || y < plotTop || y > plotTop + plotHeight) return null;

  let best: ScatterPoint | null = null;
  let bestDistance = HIT_RADIUS;
  for (const point of points) {
    const px = valueToPixel(point.actual, plotLeft, plotLeft + plotWidth, DOMAIN_MIN, DOMAIN_MAX);
    const py = valueToPixel(point.predicted, plotTop + plotHeight, plotTop, DOMAIN_MIN, DOMAIN_MAX);
    const distance = Math.hypot(px - x, py - y);
    if (distance < bestDistance) {
      best = point;
      bestDistance = distance;
    }
  }
  return best;
}

export function ValueScatter({ points, onOpen }: { points: ScatterPoint[]; onOpen?: (id: string) => void }) {
  const data = points.filter((point) => point.actual > 0 && point.predicted > 0);
  const [active, setActive] = useState<ScatterPoint | null>(null);

  function pick(event: MouseEvent<HTMLDivElement>, open: boolean) {
    const svg = event.currentTarget.querySelector("svg");
    if (!svg) return;
    const point = nearestPoint(data, svg, event.clientX, event.clientY);
    if (!point) return;
    setActive((current) => (current?.id === point.id ? current : point));
    if (open) onOpen?.(point.id);
  }

  return (
    <div className="w-full min-w-0">
      <div className="h-80 cursor-crosshair" onMouseMove={(event) => pick(event, false)} onClick={(event) => pick(event, true)}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#E4E0D6" />
            <XAxis
              dataKey="actual"
              type="number"
              scale="log"
              domain={[DOMAIN_MIN, DOMAIN_MAX]}
              ticks={[1_000_000, 10_000_000, 100_000_000]}
              tickFormatter={(value) => formatEuro(Number(value))}
              name="Market value"
              stroke="#3A4256"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              dataKey="predicted"
              type="number"
              scale="log"
              domain={[DOMAIN_MIN, DOMAIN_MAX]}
              ticks={[1_000_000, 10_000_000, 100_000_000]}
              tickFormatter={(value) => formatEuro(Number(value))}
              name="Model value"
              width={56}
              stroke="#3A4256"
              tick={{ fontSize: 12 }}
            />
            <Scatter data={data} isAnimationActive={false} fill="#132257" fillOpacity={0.4} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 min-h-8 text-sm text-[#3A4256]" data-testid="scatter-selection">
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
