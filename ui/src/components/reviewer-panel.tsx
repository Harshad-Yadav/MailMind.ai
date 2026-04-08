import { useState } from "react";
import { ClipboardCheck, Scale, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select, Textarea } from "@/components/ui/input";
import type { FeedbackRequest, FeedbackVerdict } from "@/types/env";
import { useTriageStore } from "@/store/useTriageStore";

const verdicts: FeedbackVerdict[] = ["approve", "revise", "escalate"];

export function ReviewerPanel() {
  const submitFeedback = useTriageStore((state) => state.submitFeedback);
  const lastFeedback = useTriageStore((state) => state.lastFeedback);
  const loading = useTriageStore((state) => state.loading);
  const currentState = useTriageStore((state) => state.state);
  const [feedback, setFeedback] = useState<FeedbackRequest>({
    reviewer: "QA Lead",
    rating: 4,
    verdict: "approve",
    comments: "Looks good for customer delivery.",
  });

  return (
    <Card className="command-surface animate-rise overflow-hidden border-white/70 bg-white/75 shadow-panel backdrop-blur" style={{ animationDelay: "220ms" }}>
      <CardHeader className="border-b border-slate-200/70 bg-gradient-to-r from-white via-rose-50/70 to-orange-50/60">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-xl">Human-in-the-Loop Review</CardTitle>
            <CardDescription className="mt-1">Simulate reviewer feedback, approval gates, and policy oversight on risky turns.</CardDescription>
          </div>
          <div className="rounded-full border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">
            {currentState?.human_review_required ? "Review Needed" : "Optional Review"}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 p-6">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="metric-tile rounded-[1.2rem] p-4">
            <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-steel">
              Reviewer
              <ClipboardCheck className="h-4 w-4 text-rose-500" />
            </div>
            <div className="mt-3 text-sm text-slate-700">Attach explicit comments so the next turn has human context.</div>
          </div>
          <div className="metric-tile rounded-[1.2rem] p-4">
            <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-steel">
              Risk gate
              <ShieldAlert className="h-4 w-4 text-amber-500" />
            </div>
            <div className="mt-3 text-sm text-slate-700">Escalate when the current action feels under-justified for the business impact.</div>
          </div>
          <div className="metric-tile rounded-[1.2rem] p-4">
            <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-steel">
              Policy fit
              <Scale className="h-4 w-4 text-sky-600" />
            </div>
            <div className="mt-3 text-sm text-slate-700">Use revise when the operational choice is sound but the response needs refinement.</div>
          </div>
        </div>

        <div className="rounded-[1.6rem] border border-slate-200/70 bg-slate-50/70 p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Reviewer</label>
              <Input value={feedback.reviewer} onChange={(event) => setFeedback({ ...feedback, reviewer: event.target.value })} />
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Rating</label>
              <Input type="number" min={1} max={5} value={feedback.rating} onChange={(event) => setFeedback({ ...feedback, rating: Number(event.target.value) })} />
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Verdict</label>
              <Select value={feedback.verdict} onChange={(event) => setFeedback({ ...feedback, verdict: event.target.value as FeedbackVerdict })}>
                {verdicts.map((value) => <option key={value}>{value}</option>)}
              </Select>
            </div>
          </div>
        </div>

        <div>
          <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Comments</label>
          <Textarea rows={4} className="bg-white" value={feedback.comments} onChange={(event) => setFeedback({ ...feedback, comments: event.target.value })} />
        </div>

        <Button variant="secondary" className="h-12 w-full rounded-[1.1rem]" disabled={loading} onClick={() => void submitFeedback(feedback)}>
          Submit reviewer feedback
        </Button>

        {lastFeedback ? (
          <div className="rounded-[1.5rem] border border-rose-200 bg-rose-50/75 p-4 text-sm text-ink">
            <div className="font-semibold">Latest feedback delta: {lastFeedback.reward_delta.toFixed(2)}</div>
            <div className="mt-2 leading-6 text-steel">{lastFeedback.feedback.verdict.toUpperCase()} by {lastFeedback.feedback.reviewer}: {lastFeedback.feedback.comments}</div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

