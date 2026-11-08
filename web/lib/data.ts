import fs from "node:fs";
import path from "node:path";

import type {
  BacktestPick,
  BacktestSigning,
  BacktestWindow,
  Cluster,
  Decile,
  Meta,
  ModelMetrics,
  Need,
  Neighbor,
  PcaPoint,
  Player,
  PredictionPoint,
  SearchHit,
  ShortlistRow,
} from "@/lib/types";

function read<T>(name: string): T {
  const file = path.join(process.cwd(), "public", "data", name);
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

let players: Player[] | null = null;
let byId: Map<string, Player> | null = null;

export function getPlayers(): Player[] {
  if (!players) players = read<Player[]>("players.json");
  return players;
}

export function getPlayerMap(): Map<string, Player> {
  if (!byId) byId = new Map(getPlayers().map((player) => [player.id, player]));
  return byId;
}

export function getPlayer(id: string): Player | undefined {
  return getPlayerMap().get(id);
}

export function getSearchIndex(): SearchHit[] {
  return read<SearchHit[]>("search.json");
}

let neighbors: Record<string, Neighbor[]> | null = null;
export function getNeighbors(id: string): Neighbor[] {
  if (!neighbors) neighbors = read<Record<string, Neighbor[]>>("neighbors.json");
  return neighbors[id] ?? [];
}

export function getClusters(): Cluster[] {
  return read<Cluster[]>("clusters.json");
}

let pca: Record<string, PcaPoint[]> | null = null;
export function getPca(positionGroup: string): PcaPoint[] {
  if (!pca) pca = read<Record<string, PcaPoint[]>>("pca.json");
  return pca[positionGroup] ?? [];
}

export function getPredictions(): { points: PredictionPoint[]; deciles: Decile[] } {
  return read("predictions.json");
}

export function getBacktest(): { windows: BacktestWindow[]; picks: BacktestPick[]; signings: BacktestSigning[] } {
  return read("backtest.json");
}

export function getNeeds(): Need[] {
  return read<Need[]>("needs.json");
}

export function getShortlist(): ShortlistRow[] {
  return read<ShortlistRow[]>("shortlist.json");
}

export function getMeta(): Meta {
  return read<Meta>("meta.json");
}

export function getModelMetrics(): ModelMetrics {
  return read<ModelMetrics>("model_metrics.json");
}
