"use client";

import { useEffect, useState } from "react";

import type { Meta, Neighbor, PcaPoint, Player } from "@/lib/types";

export type PlayerBundle = {
  players: Player[];
  neighbors: Record<string, Neighbor[]>;
  pca: Record<string, PcaPoint[]>;
  meta: Meta;
};

const files = {
  players: "players.json",
  neighbors: "neighbors.json",
  pca: "pca.json",
  meta: "meta.json",
} as const;

const cache: { bundle?: Promise<PlayerBundle> } = {};

export function loadPlayerBundle(): Promise<PlayerBundle> {
  if (!cache.bundle) {
    cache.bundle = Promise.all([
      fetch(`/data/${files.players}`).then((response) => response.json() as Promise<Player[]>),
      fetch(`/data/${files.neighbors}`).then((response) => response.json() as Promise<Record<string, Neighbor[]>>),
      fetch(`/data/${files.pca}`).then((response) => response.json() as Promise<Record<string, PcaPoint[]>>),
      fetch(`/data/${files.meta}`).then((response) => response.json() as Promise<Meta>),
    ]).then(([players, neighbors, pca, meta]) => ({ players, neighbors, pca, meta }));
  }
  return cache.bundle;
}

export function usePlayerData() {
  const [bundle, setBundle] = useState<PlayerBundle | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadPlayerBundle()
      .then((data) => {
        if (!cancelled) setBundle(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    status: bundle ? "ready" : error ? "error" : "loading",
    bundle,
  } as const;
}
