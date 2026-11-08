"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { PcaPlot } from "@/components/charts/pca-plot";
import { PlayerAvatar } from "@/components/player-avatar";
import { PlayerCard } from "@/components/player-card";
import { StatBar } from "@/components/stat-bar";
import { formatAge, formatEuro, formatSimilarity } from "@/lib/format";
import { positionColor } from "@/lib/positions";
import { usePlayerData } from "@/lib/use-player-data";
import type { Neighbor, Player } from "@/lib/types";

function gapCopy(market: number | null, model: number | null, gap: number | null): string {
  if (market == null || model == null) return "This profile has no model value to set beside the market fee.";
  const lead = `The market lists him at ${formatEuro(market)}. The model’s raw estimate is ${formatEuro(model)}.`;
  if (gap == null) return lead;
  if (gap > 0.05) return `${lead} After subtracting the average miss in his fee band, the gap is still positive: the stats implied a higher fee.`;
  if (gap < -0.05) return `${lead} After subtracting the average miss in his fee band, the gap is negative: the stats implied a lower fee.`;
  return `${lead} After the fee-band adjustment, he sits close to the market.`;
}

export function PlayerProfile() {
  const id = useSearchParams().get("id");
  const { status, bundle } = usePlayerData();
  const player = id && bundle ? (bundle.players.find((row) => row.id === id) ?? null) : null;
  const byId = bundle ? new Map(bundle.players.map((row) => [row.id, row])) : new Map<string, Player>();
  const similar: { neighbor: Neighbor; player: Player }[] =
    id && bundle
      ? (bundle.neighbors[id] ?? [])
          .slice(0, 10)
          .map((neighbor) => ({ neighbor, player: byId.get(neighbor.id) }))
          .filter((row): row is { neighbor: Neighbor; player: Player } => Boolean(row.player))
      : [];
  const pca = player && bundle ? (bundle.pca[player.positionGroup] ?? []) : [];
  const labels = bundle?.meta.featureLabels ?? {};

  if (status === "loading") {
    return <p className="mx-auto max-w-6xl px-5 py-16 text-[#3A4256]">Loading player…</p>;
  }
  if (status === "error" || !id || !player) {
    return (
      <article className="mx-auto max-w-2xl px-5 py-16">
        <h1 className="font-serif text-4xl text-[#132257]">Player not found</h1>
        <Link href="/" className="mt-6 inline-block text-[#132257] underline">
          Back to the story
        </Link>
      </article>
    );
  }

  const color = positionColor(player.positionGroup);
  const stats = Object.entries(player.percentiles).filter((entry): entry is [string, number] => entry[1] != null);

  return (
    <article className="mx-auto max-w-6xl px-5 py-10">
      <p className="text-sm text-[#3A4256]">
        <Link href="/" className="text-[#132257] hover:underline">
          Home
        </Link>
      </p>
      <header className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-start">
        <PlayerAvatar name={player.name} positionGroup={player.positionGroup} size={72} />
        <div className="max-w-2xl">
          <h1 className="font-serif text-4xl text-[#132257] sm:text-5xl">
            {player.name} {player.flag}
          </h1>
          <p className="mt-2 text-lg text-[#3A4256]">
            {player.team} · {formatAge(player.age)} · {player.nationality || "Nationality not listed"}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <span className="rounded-full px-2.5 py-1 text-white" style={{ background: color }}>
              {player.position}
            </span>
            {player.style ? <span className="rounded-full bg-[#F3EFE6] px-2.5 py-1 text-[#132257]">{player.style}</span> : null}
          </div>
          <p className="mt-4 text-[#1C2333]">{gapCopy(player.marketValueEur, player.predictedValueEur, player.calibratedGap)}</p>
        </div>
      </header>

      <section className="mt-12 grid gap-10 lg:grid-cols-[minmax(0,36rem)_1fr]">
        <div>
          <h2 className="font-serif text-2xl text-[#132257]">Per 90, inside his position group</h2>
          <p className="mt-2 text-sm text-[#3A4256]">100 means he is at the top of {player.position.toLowerCase()}s this season. 50 is typical.</p>
          <div className="mt-5 space-y-3">
            {stats.map(([key, value]) => (
              <StatBar key={key} label={labels[key] ?? key} value={value} color={color} />
            ))}
          </div>
        </div>
        <div>
          <h2 className="font-serif text-2xl text-[#132257]">Where he sits</h2>
          <p className="mt-2 text-sm text-[#3A4256]">A flat map of playing style. He is the dark dot. Axes are the first two components, with no labels because the distance is the point.</p>
          {pca.length ? <PcaPlot points={pca} highlight={player.id} positionGroup={player.positionGroup} /> : <p className="mt-4 text-sm text-[#3A4256]">No style map for this position.</p>}
        </div>
      </section>

      <section className="mt-14">
        <h2 className="font-serif text-2xl text-[#132257]">Ten players with a similar stat line</h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {similar.map(({ neighbor, player: match }) => (
            <PlayerCard
              key={match.id}
              id={match.id}
              name={match.name}
              club={match.team}
              age={match.age}
              flag={match.flag}
              positionGroup={match.positionGroup}
              position={match.position}
              style={match.style}
              marketValueEur={match.marketValueEur}
              metric={formatSimilarity(neighbor.similarity)}
              metricLabel="Similar"
            />
          ))}
        </div>
      </section>
    </article>
  );
}
