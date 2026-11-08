import { Suspense } from "react";

import { MethodDrawer } from "@/components/method-drawer";
import { SimilarityExplorer } from "@/components/similarity-explorer";

const COSINE = String.raw`\mathrm{similarity}(a,b)=\frac{a\cdot b}{\lVert a\rVert\,\lVert b\rVert}`;

export const metadata = { title: "Similarity" };

export default function Page() {
  return (
    <Suspense fallback={<p className="mx-auto max-w-6xl px-5 py-16 text-[#3A4256]">Loading players…</p>}>
      <SimilarityExplorer />
      <div className="mx-auto max-w-6xl px-5 pb-16">
        <MethodDrawer title="How this works" formula={COSINE}>
          <p>Each stat is rescaled inside the position group, so a centre-back is not compared with a striker. The score is the cosine of the two vectors: 100% means the same shape of season, not the same number of goals.</p>
        </MethodDrawer>
      </div>
    </Suspense>
  );
}
