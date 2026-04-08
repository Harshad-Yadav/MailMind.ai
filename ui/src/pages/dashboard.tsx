import { AlertTriangle } from "lucide-react";

import { AnalyticsPanel } from "@/components/analytics-panel";
import { DashboardHeader } from "@/components/dashboard-header";
import { DecisionPanel } from "@/components/decision-panel";
import { InboxList } from "@/components/inbox-list";
import { ReviewerPanel } from "@/components/reviewer-panel";
import { useTriageStore } from "@/store/useTriageStore";

export function DashboardPage() {
  const error = useTriageStore((state) => state.error);

  return (
    <main className="grid-boards min-h-screen px-4 py-5 sm:px-6 lg:px-10 lg:py-8">
      <div className="relative z-10 mx-auto flex max-w-[92rem] flex-col gap-6">
        <DashboardHeader />
        {error ? (
          <div className="flex items-center gap-3 rounded-[1.4rem] border border-rose-200 bg-rose-50/90 px-4 py-3 text-sm text-rose-700 shadow-sm">
            <AlertTriangle className="h-4 w-4" />
            {error}
          </div>
        ) : null}
        <div className="grid gap-6 2xl:grid-cols-[1.35fr_0.65fr]">
          <InboxList />
          <div className="grid gap-6">
            <DecisionPanel />
            <ReviewerPanel />
          </div>
        </div>
        <AnalyticsPanel />
      </div>
    </main>
  );
}
