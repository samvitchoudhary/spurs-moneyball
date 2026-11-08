"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PlayerAvatar } from "@/components/player-avatar";
import { PlayerCard } from "@/components/player-card";
import { SectionHeader } from "@/components/section-header";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { formatSimilarity } from "@/lib/format";
import { usePlayerData } from "@/lib/use-player-data";

const DEFAULT_ID = "pedro-porro-1999";

export function SimilarityExplorer() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("id");
  const id = requested || DEFAULT_ID;
  const { status, bundle } = usePlayerData();
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!requested) router.replace(`/similarity?id=${DEFAULT_ID}`);
  }, [requested, router]);

  const byId = useMemo(() => new Map(bundle?.players.map((player) => [player.id, player]) ?? []), [bundle]);
  const player = byId.get(id);
  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (needle.length < 2 || !bundle) return [];
    return bundle.players.filter((row) => row.name.toLowerCase().includes(needle)).slice(0, 8);
  }, [bundle, query]);
  const similar = (bundle?.neighbors[id] ?? [])
    .slice(0, 10)
    .map((neighbor) => ({ neighbor, player: byId.get(neighbor.id) }))
    .filter((row) => row.player);

  function select(nextId: string) {
    setQuery("");
    router.push(`/similarity?id=${nextId}`);
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <SectionHeader
        eyebrow="Players as vectors"
        title="Find players with a similar stat line"
        dek="Cosine similarity of per-90 numbers, compared inside the same position group."
      />
      <div className="mt-8 max-w-xl rounded-2xl border border-[#E4E0D6] bg-white">
        <Command label="Find a player" shouldFilter={false}>
          <CommandInput placeholder="Search a player" value={query} onValueChange={setQuery} />
          {query.trim().length >= 2 ? (
            <CommandList>
              <CommandEmpty>No player matches.</CommandEmpty>
              {matches.map((row) => (
                <CommandItem key={row.id} value={row.id} onSelect={() => select(row.id)}>
                  <PlayerAvatar name={row.name} positionGroup={row.positionGroup} size={28} />
                  <span>
                    <span className="block text-[#132257]">{row.name}</span>
                    <span className="text-xs text-[#3A4256]">
                      {row.team} · {row.position}
                    </span>
                  </span>
                </CommandItem>
              ))}
            </CommandList>
          ) : null}
        </Command>
      </div>

      {status === "loading" ? <p className="mt-8 text-[#3A4256]">Loading players…</p> : null}
      {status !== "loading" && !player ? <p className="mt-8 text-[#132257]">Player not found.</p> : null}
      {player ? (
        <div className="mt-8 max-w-xl">
          <PlayerCard
            id={player.id}
            name={player.name}
            club={player.team}
            age={player.age}
            flag={player.flag}
            positionGroup={player.positionGroup}
            position={player.position}
            style={player.style}
            marketValueEur={player.marketValueEur}
          />
        </div>
      ) : null}
      {player ? (
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {similar.map(({ neighbor, player: match }) =>
            match ? (
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
            ) : null,
          )}
        </div>
      ) : null}
    </div>
  );
}
