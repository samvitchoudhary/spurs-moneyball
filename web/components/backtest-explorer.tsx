"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PlayerChip } from "@/components/player-chip";
import { MethodDrawer } from "@/components/method-drawer";
import { SectionHeader } from "@/components/section-header";
import { formatEuro, formatSignedPercent } from "@/lib/format";
import type { BacktestPick, BacktestSigning, BacktestWindow } from "@/lib/types";

const WINDOWS = [
  "Summer 2023",
  "January 2024",
  "Summer 2024",
  "January 2025",
  "Summer 2025",
  "January 2026",
] as const;

const ROLES = ["CB", "FB", "CM", "AM_W", "ST"] as const;

const ROLE_LABEL: Record<string, string> = {
  CB: "Centre-back",
  FB: "Full-back",
  CM: "Central midfield",
  AM_W: "Wide attacker",
  ST: "Striker",
};

const OUTCOMES = ["hit", "mixed", "miss", "too early"] as const;

const TIERS = [
  { id: "first-team", label: "First team" },
  { id: "development", label: "Development" },
] as const;

const OUTCOME: Record<string, string> = {
  hit: "bg-[#E5F0EB] text-[#1F6F5B]",
  mixed: "bg-[#F4E8D4] text-[#5C471C]",
  miss: "bg-[#F6E8E6] text-[#9A3E32]",
  "too early": "bg-[#F3EFE6] text-[#6B7280]",
};

function windowSlug(label: string) {
  return label.toLowerCase().replace(" ", "-");
}

function formatGap(value: number) {
  return `${value.toFixed(2)}×`;
}

function formatShare(value: number | null) {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function median(values: number[]) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function BacktestExplorer({
  signings,
  picks,
  windows,
  playerIds,
  beatSharePct,
}: {
  signings: BacktestSigning[];
  picks: BacktestPick[];
  windows: BacktestWindow[];
  playerIds: string[];
  beatSharePct: number;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("window");
  const known = WINDOWS.find((label) => windowSlug(label) === requested);
  const windowLabel = known ?? "Summer 2023";
  const listed = new Set(playerIds);
  const rows = signings.filter((row) => row.window === windowLabel);
  const windowPicks = picks.filter((row) => row.window === windowLabel);
  const summary = windows.find((row) => row.window === windowLabel);
  const pickGroups = ROLES.map((role) => ({
    role,
    picks: windowPicks.filter((row) => row.positionGroup === role).sort((a, b) => a.rank - b.rank),
  })).filter((group) => group.picks.length);
  const pickMedian = median(picks.flatMap((row) => (row.valueChangePct == null ? [] : [row.valueChangePct])));
  const ageMatchedMedian = median(windows.flatMap((row) => (row.ageMatched == null ? [] : [row.ageMatched])));
  const firstTeam = signings.filter((row) => row.tier === "first-team");
  const firstTeamMedian = median(firstTeam.flatMap((row) => (row.valueChangePct == null ? [] : [row.valueChangePct])));
  useEffect(() => {
    if (requested !== windowSlug(windowLabel)) router.replace(`/backtest?window=${windowSlug(windowLabel)}`);
  }, [requested, windowLabel, router]);

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <SectionHeader
        eyebrow="Did it work"
        title="Would the model have done better than Spurs?"
        dek="Each past window is replayed using only information available on the day it opened."
      />
      <div className="mt-8 flex flex-wrap gap-2" role="tablist" aria-label="Transfer window">
        {WINDOWS.map((label) => (
          <button
            key={label}
            type="button"
            role="tab"
            aria-selected={label === windowLabel}
            className={
              label === windowLabel
                ? "rounded-full bg-[#132257] px-3 py-1.5 text-sm text-white"
                : "rounded-full border border-[#E4E0D6] bg-white px-3 py-1.5 text-sm text-[#132257]"
            }
            onClick={() => router.push(`/backtest?window=${windowSlug(label)}`)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[56rem] text-sm">
          <thead>
            <tr className="border-b border-[#E4E0D6] text-left text-xs text-[#3A4256]">
              <th className="py-2 pr-4 font-medium">Player</th>
              <th className="py-2 pr-4 text-right font-medium">Fee</th>
              <th className="py-2 pr-4 text-right font-medium">Value then</th>
              <th className="py-2 pr-4 text-right font-medium">Model</th>
              <th className="py-2 pr-4 text-right font-medium">Gap (×)</th>
              <th className="py-2 pr-4 text-right font-medium">Percentile</th>
              <th className="py-2 pr-4 text-right font-medium">Minutes</th>
              <th className="py-2 pr-4 text-right font-medium">After a year</th>
              <th className="py-2 font-medium">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const linked = row.id != null && listed.has(row.id);
              return (
                <tr key={`${row.name}-${row.from}`} className="border-b border-[#E4E0D6]">
                  <td className="py-2 pr-4">
                    <PlayerChip id={linked ? row.id : null} name={row.name} positionGroup={row.positionGroup} />
                  </td>
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{row.isLoan ? "Loan" : formatEuro(row.feeEur)}</td>
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{formatEuro(row.valueAtWindowEur)}</td>
                  {row.scorable ? (
                    <>
                      <td className="py-2 pr-4 text-right tabular text-[#132257]">{formatEuro(row.modelValueEur)}</td>
                      <td className="py-2 pr-4 text-right tabular text-[#132257]">{row.gap == null ? "—" : formatGap(row.gap)}</td>
                      <td className="py-2 pr-4 text-right tabular text-[#132257]">{row.gapPercentile == null ? "—" : row.gapPercentile.toFixed(1)}</td>
                    </>
                  ) : (
                    <td colSpan={3} className="py-2 pr-4 text-[#6B7280]">
                      Not scorable
                    </td>
                  )}
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{formatShare(row.minutesShare)}</td>
                  <td className="py-2 pr-4 text-right tabular text-[#132257]">{formatSignedPercent(row.valueChangePct, 1)}</td>
                  <td className="py-2">
                    {row.outcome ? (
                      <span className={`rounded-full px-2 py-0.5 text-xs ${OUTCOME[row.outcome] ?? "bg-[#F3EFE6] text-[#6B7280]"}`}>
                        {row.outcome}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <section className="mt-10">
        <h2 className="font-serif text-2xl text-[#132257]">What the model would have bought</h2>
        <div className="mt-4 space-y-4">
          {pickGroups.map((group) => (
            <div key={group.role}>
              <h3 className="text-sm font-medium text-[#132257]">{ROLE_LABEL[group.role] ?? group.role}</h3>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
                {group.picks.map((pick) => (
                  <span key={`${pick.positionGroup}-${pick.rank}`} className="inline-flex items-center gap-2">
                    <PlayerChip id={pick.id != null && listed.has(pick.id) ? pick.id : null} name={pick.name} positionGroup={pick.positionGroup} />
                    <span className="tabular text-sm text-[#3A4256]">{formatSignedPercent(pick.valueChangePct, 1)}</span>
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
      {summary ? (
        <section className="mt-10">
          <h2 className="font-serif text-2xl text-[#132257]">How this window compared</h2>
          <div className="mt-4">
            <MedianBars
              rows={[
                { name: "Model picks", value: summary.picks },
                { name: "Spurs signings", value: summary.signings },
                { name: "Age-matched", value: summary.ageMatched, note: "Fair comparison" },
                { name: "Whole role", value: summary.roleBaseline, note: "Reference" },
              ]}
            />
          </div>
        </section>
      ) : null}
      <MethodDrawer title="How leakage was prevented">
        <p>The model trains only on seasons that had already ended before the window opened.</p>
        <p>A January window uses only the last completed season, not the one still in progress.</p>
        <p>Market values are dated on or before the window, never a price from later.</p>
        <p>Team strength is rebuilt for that window, from fees known at the time.</p>
        <p>Nothing that happened after the signing — minutes, form, or the later fee — is used as an input.</p>
        <p>Verified by 7 automated tests.</p>
      </MethodDrawer>
      <section className="mt-12">
        <h2 className="font-serif text-2xl text-[#132257]">All windows</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="border-b border-[#E4E0D6] text-left text-xs text-[#3A4256]">
                <th className="py-2 pr-4 font-medium">Window</th>
                <th className="py-2 pr-4 text-right font-medium">Model picks</th>
                <th className="py-2 pr-4 text-right font-medium">Spurs signings</th>
                <th className="py-2 pr-4 text-right font-medium">Age-matched</th>
                <th className="py-2 text-right font-medium">Whole role</th>
              </tr>
            </thead>
            <tbody>
              {WINDOWS.map((label) => {
                const row = windows.find((item) => item.window === label);
                return (
                  <tr key={label} className="border-b border-[#E4E0D6]">
                    <td className="py-2 pr-4 text-[#132257]">{label}</td>
                    <td className="py-2 pr-4 text-right tabular">{formatSignedPercent(row?.picks, 1)}</td>
                    <td className="py-2 pr-4 text-right tabular">{formatSignedPercent(row?.signings, 1)}</td>
                    <td className="py-2 pr-4 text-right tabular">{formatSignedPercent(row?.ageMatched, 1)}</td>
                    <td className="py-2 text-right tabular">{formatSignedPercent(row?.roleBaseline, 1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[28rem] text-sm">
            <thead>
              <tr className="border-b border-[#E4E0D6] text-left text-xs text-[#3A4256]">
                <th className="py-2 pr-4 font-medium">Signings</th>
                {OUTCOMES.map((outcome) => (
                  <th key={outcome} className="py-2 pr-4 text-right font-medium capitalize">
                    {outcome}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {TIERS.map((tier) => (
                <tr key={tier.id} className="border-b border-[#E4E0D6]">
                  <td className="py-2 pr-4 text-[#132257]">{tier.label}</td>
                  {OUTCOMES.map((outcome) => (
                    <td key={outcome} className="py-2 pr-4 text-right tabular text-[#132257]">
                      {signings.filter((row) => row.tier === tier.id && row.outcome === outcome).length}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-sm text-[#3A4256]">
          Model picks that beat young players in the same role and window: {Math.round(beatSharePct)}%
        </p>
      </section>
      <p className="mt-10 max-w-2xl text-[#1C2333]">
        The model&apos;s picks held their value (median {formatSignedPercent(pickMedian, 0)}), compared with {formatSignedPercent(ageMatchedMedian, 1)} for age-matched peers across the windows. Only {Math.round(beatSharePct)}% beat young players in the same role and window, so there is no reliable edge. Spurs&apos; first-team signings gained {formatSignedPercent(firstTeamMedian, 1)} at the median, and every hit was a first-team signing.
      </p>
    </div>
  );
}

function MedianBars({ rows }: { rows: { name: string; value: number | null | undefined; note?: string }[] }) {
  const max = Math.max(1, ...rows.map((row) => Math.abs(row.value ?? 0)));
  return (
    <div className="max-w-xl space-y-2">
      {rows.map((row) => {
        const value = row.value ?? null;
        const width = value == null ? 0 : (Math.abs(value) / max) * 50;
        const positive = (value ?? 0) >= 0;
        return (
          <div key={row.name} className="grid grid-cols-[11rem_1fr_4.5rem] items-center gap-3">
            <div className="text-sm text-[#132257]">
              {row.name}
              {row.note ? <span className="block text-xs text-[#6B7280]">{row.note}</span> : null}
            </div>
            <div className="relative h-3">
              <div className="absolute inset-y-0 left-1/2 w-px bg-[#132257]" />
              {value != null ? (
                <div
                  className="absolute top-0 h-3"
                  style={{
                    width: `${width}%`,
                    left: positive ? "50%" : `${50 - width}%`,
                    background: positive ? "#132257" : "#9A7B3C",
                  }}
                />
              ) : null}
            </div>
            <div className="text-right text-sm tabular text-[#132257]">{formatSignedPercent(value, 1)}</div>
          </div>
        );
      })}
    </div>
  );
}
