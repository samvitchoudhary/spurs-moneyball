import { Suspense } from "react";

import { MethodDrawer } from "@/components/method-drawer";
import { StylesExplorer } from "@/components/styles-explorer";

export const metadata = { title: "Styles" };

export default function Page() {
  return (
    <Suspense fallback={<p className="mx-auto max-w-6xl px-5 py-16 text-[#3A4256]">Loading the map…</p>}>
      <StylesExplorer />
      <div className="mx-auto max-w-6xl px-5 pb-16">
        <MethodDrawer title="How this works">
          <p>The map squeezes a season of actions into two numbers, so players who do similar things land near each other. The axes are unlabelled because the distance is the point, not which way the chart points.</p>
          <p>The groups are built from those actions, not from goals and assists, so a label describes how a player plays.</p>
        </MethodDrawer>
      </div>
    </Suspense>
  );
}
