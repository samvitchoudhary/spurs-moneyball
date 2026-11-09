import { NeedsBars } from "@/components/charts/needs-bars";
import { MethodDrawer } from "@/components/method-drawer";
import { PlayerChip } from "@/components/player-chip";
import { SectionHeader } from "@/components/section-header";
import { getNeedsData, getPlayer, getSquad } from "@/lib/data";
import type { Need, NeedComponents, NeedsSensitivity, SquadPlayer } from "@/lib/types";

const COMPONENTS: { key: keyof NeedComponents; label: string }[] = [
  { key: "quality", label: "Quality" },
  { key: "output", label: "Output" },
  { key: "depth", label: "Depth" },
  { key: "age", label: "Age" },
  { key: "contract", label: "Contract" },
];

export const metadata = { title: "Needs" };

export default function Page() {
  const { positions, needsSensitivity } = getNeedsData();
  const needs = [...positions].sort((a, b) => a.rank - b.rank);
  const squad = getSquad();
  const strikers = squad.filter((player) => player.positionGroup === "ST");
  const fullbacks = squad.filter((player) => player.positionGroup === "FB");
  const robertson = fullbacks.find((player) => player.id === "andy-robertson-1994");
  const robertsonAge = robertson ? getPlayer(robertson.id)?.age : null;
  const fullback = needs.find((need) => need.positionGroup === "FB");
  const ageShare = fullback?.raw.ageShare;

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <SectionHeader
        eyebrow="The squad"
        title="Where Spurs need to recruit"
        dek="Each position compared with the six richest Premier League squads."
      />
      <div className="mt-8 max-w-xl">
        <NeedsBars needs={needs} />
      </div>
      <div className="mt-10 overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[#E4E0D6] text-left text-xs uppercase tracking-wide text-[#5C471C]">
              <th className="py-2 pr-4 font-medium">Position</th>
              {COMPONENTS.map((column) => (
                <th key={column.key} className="px-2 py-2 text-center font-medium">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {needs.map((need) => (
              <tr key={need.positionGroup} className="border-b border-[#E4E0D6]">
                <th className="py-2 pr-4 text-left font-medium text-[#132257]">{need.position}</th>
                {COMPONENTS.map((column) => (
                  <td key={column.key} className="p-1">
                    <ComponentCell need={need} component={column.key} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-10 grid gap-4 md:grid-cols-2">
        <VerdictCard title="Striker: a penalty-box striker. All current strikers drop deep or press." players={strikers} />
        <VerdictCard
          title={`Left-back: a successor to Robertson (${robertsonAge ?? "—"}, ${shareLabel(ageShare)} of full-back minutes).`}
          players={fullbacks}
        />
      </div>
      <MethodDrawer title="How this works">
        <p>Quality is 35% of the score, output 25%, depth 20%, age 10%, and contract 10%.</p>
        <p>{sensitivityLine(needsSensitivity)}</p>
        <p>There is no injury data. The 2026–27 season is only partial, and the comparison uses basic stats only.</p>
      </MethodDrawer>
    </div>
  );
}

function ComponentCell({ need, component }: { need: Need; component: keyof NeedComponents }) {
  const value = need.components[component];
  return (
    <span
      title={rawTooltip(need, component)}
      className="group relative flex h-10 items-center justify-center rounded-md tabular text-[#132257]"
      style={{ backgroundColor: heatColor(value) }}
    >
      {value == null ? "—" : value.toFixed(2)}
      <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-[#132257] px-2 py-1 text-xs text-white group-hover:block">
        {rawTooltip(need, component)}
      </span>
    </span>
  );
}

function VerdictCard({ title, players }: { title: string; players: SquadPlayer[] }) {
  return (
    <article className="rounded-2xl border border-[#E4E0D6] bg-white p-4">
      <h3 className="font-serif text-xl leading-snug text-[#132257]">{title}</h3>
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2">
        {players.map((player) => (
          <PlayerChip
            key={player.id}
            id={player.inPlayers ? player.id : null}
            name={player.name}
            positionGroup={player.positionGroup}
          />
        ))}
      </div>
    </article>
  );
}

function heatColor(value: number | null) {
  if (value == null || value === 0) return "rgba(217, 211, 199, 0.45)";
  const strength = Math.min(Math.abs(value) / 2, 1);
  const alpha = 0.12 + strength * 0.38;
  return value > 0 ? `rgba(154, 123, 60, ${alpha})` : `rgba(19, 34, 87, ${alpha})`;
}

function rawTooltip(need: Need, component: keyof NeedComponents) {
  const raw = need.raw;
  if (component === "quality") return `${euros(raw.spursQualityEur)} vs ${euros(raw.benchmarkQualityEur)}`;
  if (component === "depth") return `${count(raw.spursDepth)} vs ${count(raw.benchmarkDepth)}`;
  if (component === "output") return raw.outputPercentile == null ? "—" : `${raw.outputPercentile}th percentile`;
  if (component === "age") return `${shareLabel(raw.ageShare)} of minutes`;
  return `${shareLabel(raw.contractShare)} of minutes`;
}

function euros(value: number | null) {
  if (value == null) return "—";
  return `€${Math.round(value / 1_000_000)}m`;
}

function count(value: number | null) {
  if (value == null) return "—";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function shareLabel(value: number | null | undefined) {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function sensitivityLine(sensitivity: NeedsSensitivity) {
  if (!sensitivity.top2EqualWeightsChanged && !sensitivity.top2Quality50Changed) {
    return "The top 2 didn't change under equal weights or with quality at 50%.";
  }
  const equal = sensitivity.top2EqualWeightsChanged ? "changed" : "didn't change";
  const quality = sensitivity.top2Quality50Changed ? "changed" : "didn't change";
  return `The top 2 ${equal} under equal weights, and ${quality} with quality at 50%.`;
}
