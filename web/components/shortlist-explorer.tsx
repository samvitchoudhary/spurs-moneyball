"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ShortlistBars } from "@/components/charts/shortlist-bars";
import { PlayerCard } from "@/components/player-card";
import { SectionHeader } from "@/components/section-header";
import { StatBar } from "@/components/stat-bar";
import type { ShortlistRow } from "@/lib/types";

const TABS = [
  { slug: "st", need: "ST", label: "Striker (penalty-box striker)", position: "Striker", group: "ST" },
  { slug: "lb", need: "FB", label: "Left-back (successor to Robertson)", position: "Left-back", group: "FB" },
] as const;

export function ShortlistExplorer({
  rows,
  seasonClub,
  flags,
}: {
  rows: ShortlistRow[];
  seasonClub: Record<string, string>;
  flags: Record<string, string>;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("need");
  const tab = TABS.find((item) => item.slug === requested) ?? TABS[0];
  const listed = [...rows].filter((row) => row.need === tab.need).sort((a, b) => a.rank - b.rank).slice(0, 10);

  useEffect(() => {
    if (requested !== tab.slug) router.replace(`/shortlist?need=${tab.slug}`);
  }, [requested, tab.slug, router]);

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <SectionHeader
        eyebrow="January"
        title="January targets"
        dek="A scout's review list, not a recommendation."
      />
      <div className="mt-8 flex flex-wrap gap-2" role="tablist" aria-label="Shortlist">
        {TABS.map((item) => (
          <button
            key={item.slug}
            type="button"
            role="tab"
            aria-selected={item.slug === tab.slug}
            className={
              item.slug === tab.slug
                ? "rounded-full bg-[#132257] px-3 py-1.5 text-sm text-white"
                : "rounded-full border border-[#E4E0D6] bg-white px-3 py-1.5 text-sm text-[#132257]"
            }
            onClick={() => router.push(`/shortlist?need=${item.slug}`)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="mt-8">
        <ShortlistBars rows={listed} />
      </div>
      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {listed.map((row) => (
          <Candidate key={`${row.need}-${row.rank}`} row={row} tab={tab} seasonClub={seasonClub} flags={flags} />
        ))}
      </div>
      <p className="mt-10 max-w-2xl text-sm text-[#3A4256]">
        Values are from June 2026. Final picks need a manual check of the current fee, contract, and availability.
      </p>
    </div>
  );
}

function Candidate({
  row,
  tab,
  seasonClub,
  flags,
}: {
  row: ShortlistRow;
  tab: (typeof TABS)[number];
  seasonClub: Record<string, string>;
  flags: Record<string, string>;
}) {
  const priorClub = row.id ? seasonClub[row.id] : undefined;
  const moved = priorClub != null && priorClub !== row.club;
  const weakStyle = row.stylePercentile != null && row.stylePercentile < 50;
  const flagText = splitFlags(row.flags);

  return (
    <div className="space-y-3">
      <PlayerCard
        id={row.id}
        name={row.name}
        club={row.club}
        age={row.age}
        flag={row.id ? flags[row.id] : undefined}
        positionGroup={tab.group}
        position={tab.position}
        style={row.targetStyle}
        marketValueEur={row.marketValueEur}
        metric={row.totalScore == null ? null : row.totalScore.toFixed(1)}
        metricLabel="Score"
      />
      <div className="space-y-2 px-1">
        <StatBar label="Value" value={row.valuePercentile} color="#132257" />
        <StatBar label="Style" value={row.stylePercentile} color="#6E4C7A" />
        <StatBar label="Form" value={row.formPercentile} color="#9A7B3C" />
        <StatBar label="Reliability" value={row.reliabilityPercentile} color="#1F6F5B" />
      </div>
      {flagText.length || moved || weakStyle ? (
        <div className="flex flex-wrap gap-1.5 px-1">
          {flagText.map((text) => (
            <span key={text} className="rounded-full bg-[#F3EFE6] px-2 py-0.5 text-xs text-[#132257]">
              {text}
            </span>
          ))}
          {moved ? (
            <span className="rounded-full bg-[#F4E8D4] px-2 py-0.5 text-xs text-[#5C471C]">
              Moved summer 2026, recheck value
            </span>
          ) : null}
          {weakStyle ? (
            <span className="rounded-full bg-[#F3EFE6] px-2 py-0.5 text-xs text-[#3A4256]">Weak style fit</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function splitFlags(flags: string | null) {
  if (!flags) return [];
  return flags
    .split(". ")
    .map((part) => part.trim().replace(/\.$/, ""))
    .filter(Boolean);
}
