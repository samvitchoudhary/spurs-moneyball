"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { StyleMap } from "@/components/charts/pca-plot";
import { SectionHeader } from "@/components/section-header";
import { usePlayerData } from "@/lib/use-player-data";

const GROUPS = ["CB", "FB", "CM", "AM_W", "ST"] as const;

const LABEL: Record<string, string> = {
  CB: "Centre-back",
  FB: "Full-back",
  CM: "Central midfield",
  AM_W: "Wide attacker",
  ST: "Striker",
};

export function StylesExplorer() {
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("group");
  const group = GROUPS.includes(requested as (typeof GROUPS)[number]) ? requested! : "ST";
  const { status, bundle } = usePlayerData();

  useEffect(() => {
    if (requested !== group) router.replace(`/styles?group=${group}`);
  }, [requested, group, router]);

  const points = bundle?.pca[group] ?? [];

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
      {status === "loading" ? <p className="mt-8 text-[#3A4256]">Loading the map…</p> : null}
      {bundle ? <div className="mt-6"><StyleMap points={points} players={bundle.players} positionGroup={group} /></div> : null}
    </div>
  );
}
