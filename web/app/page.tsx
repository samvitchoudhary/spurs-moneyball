import Link from "next/link";

import { BacktestDots } from "@/components/charts/backtest-dots";
import { NeedsBars } from "@/components/charts/needs-bars";
import { ValueScatter } from "@/components/charts/value-scatter";
import { CountUp } from "@/components/count-up";
import { MethodDrawer } from "@/components/method-drawer";
import { PlayerCard } from "@/components/player-card";
import { Reveal } from "@/components/reveal";
import { SectionHeader } from "@/components/section-header";
import { VectorIllustration } from "@/components/vector-illustration";
import { getBacktest, getMeta, getNeeds, getPlayer, getPlayers, getPredictions, getShortlist } from "@/lib/data";
import { formatSignedPercent } from "@/lib/format";

const COSINE = String.raw`\mathrm{similarity}(a,b)=\frac{a\cdot b}{\lVert a\rVert\,\lVert b\rVert}`;

function More({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="mt-6 inline-block text-sm font-medium text-[#132257] underline">
      {label}
    </Link>
  );
}

export default function HomePage() {
  const meta = getMeta();
  const predictions = getPredictions();
  const players = getPlayers();
  const backtest = getBacktest();
  const needs = getNeeds();
  const shortlist = getShortlist();
  const palhinha = getPlayer(meta.examples.palhinha.id);
  const porro = getPlayer(meta.examples.porro.id);
  const headlines = meta.headlines;

  return (
    <div className="mx-auto max-w-6xl px-5">
      <section className="py-16 sm:py-24">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#5C471C]">January window</p>
        <h1 className="mt-4 max-w-3xl font-serif text-5xl leading-[1.05] text-[#132257] sm:text-6xl">
          Can a model find undervalued players who fit what Tottenham needs this January?
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[#3A4256]">
          Five seasons of basic match stats, turned into a value, a playing style, and a shortlist a scout can argue with.
        </p>
        <dl className="mt-10 grid max-w-xl grid-cols-3 gap-4">
          {[
            [meta.playersAnalyzed, "Players"],
            [meta.seasons, "Seasons"],
            [meta.leagues, "Leagues"],
          ].map(([value, label]) => (
            <div key={label}>
              <dt className="font-serif text-4xl text-[#132257]">
                <CountUp value={Number(value)} />
              </dt>
              <dd className="mt-1 text-sm text-[#3A4256]">{label}</dd>
            </div>
          ))}
        </dl>
      </section>

      <Reveal className="border-t border-[#E4E0D6] py-16">
        <SectionHeader
          eyebrow="01"
          title="Every player is a vector"
          dek="A season becomes a list of per-90 numbers. Two players are similar when those lists point the same way."
        />
        <div className="mt-8 max-w-3xl">
          <VectorIllustration />
        </div>
        <MethodDrawer title="How this works" formula={COSINE}>
          <p>Each stat is rescaled inside the position group, so a centre-back is not punished for scoring less than a striker. The score is the cosine of the two vectors: 100% is the same shape of season, not the same number of goals.</p>
        </MethodDrawer>
        <More href="/similarity" label="Open the similarity page" />
      </Reveal>

      <Reveal className="border-t border-[#E4E0D6] py-16">
        <SectionHeader
          eyebrow="02"
          title="Styles, not goals"
          dek="The first fit used goals and assists, so it described what happened, not how a player plays. Dropping those outcomes changed the labels."
        />
        <div className="mt-8 grid max-w-3xl gap-3 sm:grid-cols-2">
          {palhinha ? (
            <div>
              <p className="mb-2 text-sm text-[#3A4256]">Goals made him look like a goalscoring midfielder. Without them, he is a ball-winner.</p>
              <PlayerCard
                id={palhinha.id}
                name={palhinha.name}
                club={palhinha.team}
                age={palhinha.age}
                flag={palhinha.flag}
                positionGroup={palhinha.positionGroup}
                position={palhinha.position}
                style={palhinha.style}
                marketValueEur={palhinha.marketValueEur}
              />
            </div>
          ) : null}
          {porro ? (
            <div>
              <p className="mb-2 text-sm text-[#3A4256]">Goals made him look like a holding full-back. Without them, he is an attacking wing-back.</p>
              <PlayerCard
                id={porro.id}
                name={porro.name}
                club={porro.team}
                age={porro.age}
                flag={porro.flag}
                positionGroup={porro.positionGroup}
                position={porro.position}
                style={porro.style}
                marketValueEur={porro.marketValueEur}
              />
            </div>
          ) : null}
        </div>
        <More href="/styles" label="Open the styles page" />
      </Reveal>

      <Reveal className="border-t border-[#E4E0D6] py-16">
        <SectionHeader
          eyebrow="03"
          title="Pricing players"
          dek="Log axes, so a doubling from €2m to €4m takes the same space as €20m to €40m. The 2025–26 model explains about 83% of fee variation."
        />
        <div className="mt-8">
          <ValueScatter
            points={predictions.points.map((point) => {
              const person = players.find((player) => player.id === point.id);
              return {
                id: point.id,
                actual: point.actual,
                predicted: point.predicted,
                name: person?.name ?? "Player",
                positionGroup: person?.positionGroup ?? "",
              };
            })}
          />
        </div>
        <p className="mt-4 max-w-2xl text-[#1C2333]">
          Cheap fees are over-predicted and expensive fees are under-predicted. The number used later is the log gap minus the average gap in that fee band.
        </p>
        <More href="/value" label="Open the value page" />
      </Reveal>

      <Reveal className="border-t border-[#E4E0D6] py-16">
        <SectionHeader
          eyebrow="04"
          title="Testing it honestly"
          dek={`Across the windows with a follow-up, the model’s picks had a median change of ${formatSignedPercent(headlines.picksMedianPct)}, against about ${formatSignedPercent(headlines.ageMatchedPct, 1)} for age-matched peers. ${headlines.beatSharePct}% of picks beat that bar. Spurs’ own arrivals had a median of ${formatSignedPercent(headlines.signingsMedianPct)}.`}
        />
        <div className="mt-8">
          <BacktestDots windows={backtest.windows} />
        </div>
        <p className="mt-2 text-sm text-[#3A4256]">A missing point means there is no follow-up value yet. January 2026 is that window. A point at zero is a measured zero.</p>
        <MethodDrawer title="How this works">
          <p>A season counts as finished on 30 June, and a summer window opens on 1 July, so the model only trains on seasons that have already ended. A January score uses the last completed season: January 2024 on 2022–23, January 2025 on 2023–24, January 2026 on 2024–25.</p>
          <p>Fees are the value on the cutoff date or earlier. Team strength is rebuilt from those fees, leaving the player himself out, rather than from the July 2026 snapshot. Nothing about how a player later did at Spurs is a feature. Style labels learned from 2025–26 are wiped for any window that could not have seen that season. The player being scored is held out of the fit.</p>
        </MethodDrawer>
        <More href="/backtest" label="Open the backtest page" />
      </Reveal>

      <Reveal className="border-t border-[#E4E0D6] py-16">
        <SectionHeader
          eyebrow="05"
          title="What Spurs need"
          dek="The score mixes how much the group creates, relative to the squad, with whether a useful style is missing. Striker and left-back are the two that stand out."
        />
        <div className="mt-8 max-w-xl">
          <NeedsBars needs={needs} />
        </div>
        <More href="/needs" label="Open the needs page" />
      </Reveal>

      <Reveal className="border-t border-[#E4E0D6] py-16">
        <SectionHeader
          eyebrow="06"
          title="January targets"
          dek="Three names for each need. A scout’s review list, not a recommendation. Check the current fee, and whether a deal is realistic, before treating any of them as a target."
        />
        <div className="mt-8 space-y-8">
          {["ST", "FB"].map((need) => (
            <div key={need}>
              <h3 className="font-serif text-2xl text-[#132257]">{need === "FB" ? "Left-back" : "Striker"}</h3>
              <div className="mt-3 grid gap-3 lg:grid-cols-3">
                {shortlist
                  .filter((row) => row.need === need)
                  .slice(0, 3)
                  .map((row) => {
                    const person = row.id ? getPlayer(row.id) : undefined;
                    return (
                      <PlayerCard
                        key={`${row.need}-${row.rank}-${row.name}`}
                        id={row.id}
                        name={row.name}
                        club={row.club}
                        age={row.age}
                        flag={person?.flag}
                        positionGroup={row.need}
                        position={need === "FB" ? "Left-back" : "Striker"}
                        style={person?.style}
                        marketValueEur={row.marketValueEur}
                        metric={row.totalScore == null ? null : String(Math.round(row.totalScore))}
                        metricLabel="Score"
                      />
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
        <More href="/shortlist" label="Open the shortlist page" />
      </Reveal>
    </div>
  );
}
