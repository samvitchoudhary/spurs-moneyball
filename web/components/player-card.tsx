import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import { formatAge, formatEuro } from "@/lib/format";
import { positionColor } from "@/lib/positions";

export function PlayerCard({
  id,
  name,
  club,
  age,
  flag,
  positionGroup,
  position,
  style,
  marketValueEur,
  metric,
  metricLabel,
}: {
  id?: string | null;
  name: string;
  club?: string | null;
  age?: number | null;
  flag?: string;
  positionGroup?: string | null;
  position?: string | null;
  style?: string | null;
  marketValueEur?: number | null;
  metric?: string | null;
  metricLabel?: string;
}) {
  const inner = (
    <article className="flex h-full gap-3 rounded-2xl border border-[#E4E0D6] bg-white p-3">
      <PlayerAvatar name={name} positionGroup={positionGroup} />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="truncate font-medium text-[#132257]">
            {name} {flag ? <span aria-label={flag}>{flag}</span> : null}
          </h3>
          {metric ? (
            <div className="text-right">
              {metricLabel ? <div className="text-[10px] uppercase tracking-wide text-[#5C471C]">{metricLabel}</div> : null}
              <div className="tabular text-lg font-semibold leading-none text-[#132257]">{metric}</div>
            </div>
          ) : null}
        </div>
        <p className="mt-0.5 text-sm text-[#3A4256]">
          {club || "—"} · {formatAge(age)}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          {position ? (
            <span className="rounded-full px-2 py-0.5 text-white" style={{ background: positionColor(positionGroup) }}>
              {position}
            </span>
          ) : null}
          {style ? <span className="rounded-full bg-[#F3EFE6] px-2 py-0.5 text-[#132257]">{style}</span> : null}
          <span className="tabular font-medium text-[#132257]">{formatEuro(marketValueEur)}</span>
        </div>
      </div>
    </article>
  );
  if (!id) return inner;
  return (
    <Link href={`/player/${id}`} className="block rounded-2xl focus-visible:outline-[#132257]">
      {inner}
    </Link>
  );
}
