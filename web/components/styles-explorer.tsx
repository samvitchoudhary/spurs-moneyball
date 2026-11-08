"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { StyleMap } from "@/components/charts/pca-plot";
import { PlayerChip } from "@/components/player-chip";
import { SectionHeader } from "@/components/section-header";
import type { Cluster, Player, SquadPlayer } from "@/lib/types";
import { usePlayerData } from "@/lib/use-player-data";

const GROUPS = ["CB", "FB", "CM", "AM_W", "ST"] as const;

const LABEL: Record<string, string> = {
  CB: "Centre-back",
  FB: "Full-back",
  CM: "Central midfield",
  AM_W: "Wide attacker",
  ST: "Striker",
};

type FeatureBit = { label: string; value: string };

const styleCache: { data?: Promise<{ clusters: Cluster[]; squad: SquadPlayer[] }> } = {};

function loadStyleData() {
  if (!styleCache.data) {
    styleCache.data = Promise.all([
      fetch("/data/clusters.json").then((response) => response.json() as Promise<Cluster[]>),
      fetch("/data/squad.json").then((response) => response.json() as Promise<SquadPlayer[]>),
    ]).then(([clusters, squad]) => ({ clusters, squad }));
  }
  return styleCache.data;
}

function parseFeatures(text: string, labels: Record<string, string>): FeatureBit[] {
  return text
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const match = part.match(/^([a-z0-9_]+)\s+\(([+-]?\d+(?:\.\d+)?)\)$/);
      const key = match?.[1] ?? part;
      return { label: labels[key] ?? key.replaceAll("_", " "), value: match?.[2] ?? "" };
    });
}

function FeatureChips({ bits, tone }: { bits: FeatureBit[]; tone: "high" | "low" }) {
  const className =
    tone === "high"
      ? "rounded-full bg-[#F4E8D4] px-2 py-0.5 text-xs text-[#5C471C]"
      : "rounded-full bg-[#F3EFE6] px-2 py-0.5 text-xs text-[#6B7280]";
  return (
    <div className="flex flex-wrap gap-1.5">
      {bits.map((bit) => (
        <span key={`${bit.label}-${bit.value}`} className={className}>
          {bit.label} {bit.value}
        </span>
      ))}
    </div>
  );
}

export function StylesExplorer() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("group");
  const group = GROUPS.includes(requested as (typeof GROUPS)[number]) ? requested! : "ST";
  const { status, bundle } = usePlayerData();
  const [styleData, setStyleData] = useState<{ clusters: Cluster[]; squad: SquadPlayer[] } | null>(null);

  useEffect(() => {
    if (requested !== group) router.replace(`/styles?group=${group}`);
  }, [requested, group, router]);

  useEffect(() => {
    let cancelled = false;
    loadStyleData().then((data) => {
      if (!cancelled) setStyleData(data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const points = bundle?.pca[group] ?? [];
  const labels = bundle?.meta.featureLabels ?? {};
  const byId = useMemo(() => new Map(bundle?.players.map((player) => [player.id, player]) ?? []), [bundle]);
  const groupClusters = styleData?.clusters.filter((cluster) => cluster.positionGroup === group) ?? [];
  const groupSquad = styleData?.squad.filter((player) => player.positionGroup === group) ?? [];
  const spursIds = useMemo(() => new Set(styleData?.squad.map((player) => player.id) ?? []), [styleData]);
  const unnamed = groupSquad.filter((player) => player.style == null);

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <SectionHeader
        eyebrow="How they play"
        title="How players play, not how often they score"
        dek="Each dot is a season of actions, pressed flat so similar players sit together."
      />
      <div className="mt-8 flex flex-wrap gap-2" role="tablist" aria-label="Position group">
        {GROUPS.map((item) => (
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
            onClick={() => router.push(`/styles?group=${item}`)}
          >
            {LABEL[item]}
          </button>
        ))}
      </div>
      {status === "loading" || !styleData ? <p className="mt-8 text-[#3A4256]">Loading the map…</p> : null}
      {bundle && styleData ? (
        <>
          <div className="mt-6">
            <StyleMap points={points} players={bundle.players} positionGroup={group} spursIds={spursIds} />
          </div>
          <section className="mt-10">
            <h2 className="font-serif text-2xl text-[#132257]">The styles</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {groupClusters.map((cluster) => (
                <article key={cluster.id} className="rounded-2xl border border-[#E4E0D6] bg-white p-4">
                  <div className="flex items-baseline justify-between gap-3">
                    <h3 className="font-medium text-[#132257]">{cluster.name}</h3>
                    <p className="text-xs text-[#3A4256]">{cluster.size} players</p>
                  </div>
                  <div className="mt-3 space-y-2">
                    <FeatureChips bits={parseFeatures(cluster.moreOf, labels)} tone="high" />
                    <FeatureChips bits={parseFeatures(cluster.lessOf, labels)} tone="low" />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
                    {cluster.typicalPlayers.map((id) => (
                      <TypicalChip key={id} id={id} player={byId.get(id)} fallbackGroup={group} />
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
          <section className="mt-10">
            <h2 className="font-serif text-2xl text-[#132257]">Spurs by style</h2>
            <div className="mt-4 flex gap-3 overflow-x-auto pb-1">
              {groupClusters.map((cluster) => {
                const members = groupSquad.filter((player) => player.style === cluster.name);
                return (
                  <div key={cluster.id} className="min-w-52 flex-1 rounded-2xl border border-[#E4E0D6] bg-white p-3">
                    <h3 className="text-sm font-medium text-[#132257]">{cluster.name}</h3>
                    <div className="mt-3 flex flex-col gap-2">
                      {members.length ? (
                        members.map((player) => (
                          <PlayerChip
                            key={player.id}
                            id={player.inPlayers ? player.id : null}
                            name={player.name}
                            positionGroup={player.positionGroup}
                          />
                        ))
                      ) : (
                        <p className="text-sm text-[#6B7280]">No Spurs player</p>
                      )}
                    </div>
                  </div>
                );
              })}
              {unnamed.length ? (
                <div className="min-w-52 flex-1 rounded-2xl border border-[#E4E0D6] bg-white p-3">
                  <h3 className="text-sm font-medium text-[#132257]">Not enough 2025-26 minutes</h3>
                  <div className="mt-3 flex flex-col gap-2">
                    {unnamed.map((player) => (
                      <PlayerChip
                        key={player.id}
                        id={player.inPlayers ? player.id : null}
                        name={player.name}
                        positionGroup={player.positionGroup}
                      />
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function TypicalChip({ id, player, fallbackGroup }: { id: string; player: Player | undefined; fallbackGroup: string }) {
  return <PlayerChip id={id} name={player?.name ?? id} positionGroup={player?.positionGroup ?? fallbackGroup} />;
}
