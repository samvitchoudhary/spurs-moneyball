import { Suspense } from "react";

import { ValueExplorer } from "@/components/value-explorer";
import { getModelMetrics, getPlayers, getPredictions } from "@/lib/data";

export const metadata = { title: "Value" };

export default function Page() {
  const metrics = getModelMetrics();
  const players = new Map(getPlayers().map((player) => [player.id, player]));
  const points = getPredictions().points.map((point) => {
    const person = players.get(point.id);
    return {
      id: point.id,
      actual: point.actual,
      predicted: point.predicted,
      name: person?.name ?? "Player",
      positionGroup: person?.positionGroup ?? "",
    };
  });

  return (
    <Suspense fallback={<p className="mx-auto max-w-6xl px-5 py-16 text-[#3A4256]">Loading the model…</p>}>
      <ValueExplorer metrics={metrics} points={points} />
    </Suspense>
  );
}
