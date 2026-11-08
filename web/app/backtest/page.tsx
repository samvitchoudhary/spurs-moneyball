import { Suspense } from "react";

import { BacktestExplorer } from "@/components/backtest-explorer";
import { getBacktest, getPlayers } from "@/lib/data";

export const metadata = { title: "Backtest" };

export default function Page() {
  const backtest = getBacktest();
  const playerIds = getPlayers().map((player) => player.id);

  return (
    <Suspense fallback={<p className="mx-auto max-w-6xl px-5 py-16 text-[#3A4256]">Loading the backtest…</p>}>
      <BacktestExplorer signings={backtest.signings} picks={backtest.picks} windows={backtest.windows} playerIds={playerIds} />
    </Suspense>
  );
}
