"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PlayerAvatar } from "@/components/player-avatar";
import { PlayerCard } from "@/components/player-card";
import { SectionHeader } from "@/components/section-header";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { formatSimilarity } from "@/lib/format";
import { usePlayerData } from "@/lib/use-player-data";
import type { Player } from "@/lib/types";

const DEFAULT_ID = "pedro-porro-1999";
const AGE_MIN = 16;
const AGE_MAX = 40;
const LEAGUES = [
  "ENG-Premier League",
  "ESP-La Liga",
  "FRA-Ligue 1",
  "GER-Bundesliga",
  "ITA-Serie A",
] as const;

const LEAGUE_LABEL: Record<string, string> = {
  "ENG-Premier League": "Premier League",
  "ESP-La Liga": "La Liga",
  "FRA-Ligue 1": "Ligue 1",
  "GER-Bundesliga": "Bundesliga",
  "ITA-Serie A": "Serie A",
};

function sideOf(player: Player | undefined): "Left" | "Right" | null {
  const sub = player?.subPosition ?? "";
  if (sub.startsWith("Left")) return "Left";
  if (sub.startsWith("Right")) return "Right";
  return null;
}

type Filters = {
  maxAge: number;
  maxValueM: number | null;
  leagues: string[];
  sameSide: boolean;
};

function readFilters(params: URLSearchParams): Filters {
  const age = Number(params.get("age"));
  const value = params.get("value");
  const listed = params.get("leagues");
  return {
    maxAge: Number.isFinite(age) && age > 0 ? age : AGE_MAX,
    maxValueM: value == null || value === "" || Number.isNaN(Number(value)) ? null : Number(value),
    leagues: listed == null ? [...LEAGUES] : listed.split("|").filter((league) => LEAGUES.includes(league as (typeof LEAGUES)[number])),
    sameSide: params.get("side") === "1",
  };
}

function writeUrl(router: ReturnType<typeof useRouter>, id: string, filters: Filters, mode: "push" | "replace") {
  const query = new URLSearchParams();
  query.set("id", id);
  if (filters.maxAge < AGE_MAX) query.set("age", String(filters.maxAge));
  if (filters.maxValueM != null) query.set("value", String(filters.maxValueM));
  if (filters.leagues.length !== LEAGUES.length) query.set("leagues", filters.leagues.join("|"));
  if (filters.sameSide) query.set("side", "1");
  const href = `/similarity?${query.toString()}`;
  if (mode === "push") router.push(href);
  else router.replace(href);
}

export function SimilarityExplorer() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("id");
  const id = requested || DEFAULT_ID;
  const filters = readFilters(params);
  const filtersRef = useRef(filters);
  const searchRef = useRef(params.toString());
  if (params.toString() !== searchRef.current) {
    searchRef.current = params.toString();
    filtersRef.current = filters;
  }
  const { status, bundle } = usePlayerData();
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!requested) router.replace(`/similarity?id=${DEFAULT_ID}`);
  }, [requested, router]);

  const byId = useMemo(() => new Map(bundle?.players.map((player) => [player.id, player]) ?? []), [bundle]);
  const player = byId.get(id);
  const playerSide = sideOf(player);
  const showSide = (player?.positionGroup === "FB" || player?.positionGroup === "AM_W") && playerSide != null;
  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (needle.length < 2 || !bundle) return [];
    return bundle.players.filter((row) => row.name.toLowerCase().includes(needle)).slice(0, 8);
  }, [bundle, query]);

  const closest = (bundle?.neighbors[id] ?? [])
    .slice(0, 20)
    .map((neighbor) => ({ neighbor, player: byId.get(neighbor.id) }))
    .filter((row): row is { neighbor: (typeof row)["neighbor"]; player: Player } => Boolean(row.player));

  const similar = closest.filter(({ player: match }) => {
    if (match.age != null && match.age > filters.maxAge) return false;
    if (filters.maxValueM != null) {
      if (match.marketValueEur == null || match.marketValueEur / 1_000_000 > filters.maxValueM) return false;
    }
    if (match.league == null || !filters.leagues.includes(match.league)) return false;
    if (showSide && filters.sameSide && sideOf(match) !== playerSide) return false;
    return true;
  });

  function update(next: Partial<Filters>) {
    const merged = { ...filtersRef.current, ...next };
    filtersRef.current = merged;
    writeUrl(router, id, merged, "replace");
  }

  function select(nextId: string) {
    setQuery("");
    writeUrl(router, nextId, filters, "push");
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
        <div className="mt-8 flex flex-wrap items-end gap-x-6 gap-y-4 text-sm text-[#1C2333]">
          <label className="min-w-40">
            <span className="block text-[#3A4256]">
              Max age <span className="tabular text-[#132257]">{filters.maxAge}</span>
            </span>
            <input
              className="mt-1 w-full accent-[#132257]"
              type="range"
              min={AGE_MIN}
              max={AGE_MAX}
              value={filters.maxAge}
              aria-label="Max age"
              onChange={(event) => update({ maxAge: Number(event.target.value) })}
            />
          </label>
          <label>
            <span className="block text-[#3A4256]">Max value, €m</span>
            <input
              className="mt-1 w-24 rounded-lg border border-[#E4E0D6] bg-white px-2 py-1 tabular"
              type="number"
              min={0}
              step={1}
              placeholder="No cap"
              aria-label="Max market value in millions of euros"
              value={filters.maxValueM ?? ""}
              onChange={(event) => update({ maxValueM: event.target.value === "" ? null : Number(event.target.value) })}
            />
          </label>
          <fieldset>
            <legend className="text-[#3A4256]">Leagues</legend>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
              {LEAGUES.map((league) => (
                <label key={league} className="inline-flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={filters.leagues.includes(league)}
                    onChange={(event) => {
                      const current = filtersRef.current.leagues;
                      const leagues = event.target.checked ? [...current, league] : current.filter((item) => item !== league);
                      update({ leagues });
                    }}
                  />
                  {LEAGUE_LABEL[league]}
                </label>
              ))}
            </div>
          </fieldset>
          {showSide ? (
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={filters.sameSide}
                aria-label="Same side"
                onChange={(event) => update({ sameSide: event.target.checked })}
              />
              Same side
            </label>
          ) : null}
        </div>
      ) : null}

      {player ? <p className="mt-4 text-sm text-[#3A4256]">Showing {similar.length} of the 20 closest profiles</p> : null}
      {player && similar.length === 0 ? (
        <p className="mt-4 max-w-xl text-[#1C2333]">None of the 20 closest profiles fit these filters. Loosen the age, the fee, or the leagues.</p>
      ) : null}
      {player && similar.length > 0 ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
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
      ) : null}
    </div>
  );
}
