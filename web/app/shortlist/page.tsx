import { Suspense } from "react";

import { ShortlistExplorer } from "@/components/shortlist-explorer";
import { getPlayers, getShortlist } from "@/lib/data";

export const metadata = { title: "Shortlist" };

export default function Page() {
  const seasonClub: Record<string, string> = {};
  const flags: Record<string, string> = {};
  for (const player of getPlayers()) {
    if (player.seasonLabel !== "2025-26" || !player.team) continue;
    seasonClub[player.id] = player.team;
    if (player.flag) flags[player.id] = player.flag;
  }

  return (
    <Suspense fallback={<p className="mx-auto max-w-6xl px-5 py-16 text-[#3A4256]">Loading the shortlist…</p>}>
      <ShortlistExplorer rows={getShortlist()} seasonClub={seasonClub} flags={flags} />
    </Suspense>
  );
}
