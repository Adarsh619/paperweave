import type { Metadata } from "next";

import { PageOutline, QuestionRail, WithSidebars } from "@/components/Sidebars";
import TrendsView from "@/components/TrendsView";
import type { CoverageStats } from "@/lib/types";
import coverage from "@/public/stats.json";

export const metadata: Metadata = { title: "Trends · PaperWeave" };

const OUTLINE: [string, string][] = [
  ["growing", "Growing topics"],
  ["methods", "Methods on the rise"],
  ["breakout", "Breakout papers"],
];

export default function TrendsPage() {
  const fields = (coverage as CoverageStats).fields.map((f) => f.name);
  return (
    <WithSidebars left={<PageOutline items={OUTLINE} />} right={<QuestionRail />}>
      <div className="mx-auto max-w-5xl px-4 py-12">
        <h1 className="font-serif text-4xl font-semibold tracking-tight">Trends from the papers</h1>
        <p className="mt-3 max-w-3xl text-muted">
          What the data shows: which topics are publishing more, which methods show up in a growing share of papers,
          and which recent papers are gathering citations fastest. These are measurements, not forecasts.
        </p>
        <div className="mt-8">
          <TrendsView fields={fields} />
        </div>
      </div>
    </WithSidebars>
  );
}
