"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PlayerChip } from "@/components/player-chip";
import { MethodDrawer } from "@/components/method-drawer";
import { SectionHeader } from "@/components/section-header";
import { formatEuro, formatSignedPercent } from "@/lib/format";
import type { BacktestSigning } from "@/lib/types";

const WINDOWS = [
  "Summer 2023",
  "January 2024",
  "Summer 2024",
  "January 2025",
  "Summer 2025",
  "January 2026",
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

export function BacktestExplorer({ signings, playerIds }: { signings: BacktestSigning[]; playerIds: string[] }) {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("window");
  const known = WINDOWS.find((label) => windowSlug(label) === requested);
  const windowLabel = known ?? "Summer 2023";
  const listed = new Set(playerIds);
  const rows = signings.filter((row) => row.window === windowLabel);

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
      <MethodDrawer title="How leakage was prevented">
        <p>The model trains only on seasons that had already ended before the window opened.</p>
        <p>A January window uses only the last completed season, not the one still in progress.</p>
        <p>Market values are dated on or before the window, never a price from later.</p>
        <p>Team strength is rebuilt for that window, from fees known at the time.</p>
        <p>Nothing that happened after the signing — minutes, form, or the later fee — is used as an input.</p>
        <p>Verified by 7 automated tests.</p>
      </MethodDrawer>
    </div>
  );
}
