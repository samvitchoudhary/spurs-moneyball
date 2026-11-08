import { Suspense } from "react";

import { PlayerProfile } from "@/components/player-profile";

export const metadata = { title: "Player" };

export default function PlayerPage() {
  return (
    <Suspense fallback={<p className="mx-auto max-w-6xl px-5 py-16 text-[#3A4256]">Loading player…</p>}>
      <PlayerProfile />
    </Suspense>
  );
}
