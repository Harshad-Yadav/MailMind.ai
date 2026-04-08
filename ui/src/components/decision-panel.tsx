import { useEffect, useState } from "react";
import { Bot, ShieldCheck, Sparkles, Target } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select, Textarea } from "@/components/ui/input";
import type { AgentAction } from "@/types/env";
import { useTriageStore } from "@/store/useTriageStore";

const categories = ["billing", "technical_support", "sales", "legal", "human_resources", "security", "operations", "partnership"];
const priorities = ["low", "medium", "high", "critical"];
const departments = ["finance", "support", "sales", "legal", "people_ops", "security", "operations", "partnerships"];
const sentiments = ["positive", "neutral", "negative", "frustrated"];
const urgencies = ["low", "medium", "high", "critical"];

const initialAction: AgentAction = {
  category: "billing",
  priority: "medium",
  department: "finance",
  spam: 0,
  sentiment: "neutral",
  urgency: "medium",
  response_draft: "",
  escalation: false,
  confidence: 0.75,
  internal_note: "",
  request_human_review: false,
};

export function DecisionPanel() {
  const [action, setAction] = useState<AgentAction>(initialAction);
  const submitAction = useTriageStore((state) => state.submitAction);
  const lastStep = useTriageStore((state) => state.lastStep);
  const loading = useTriageStore((state) => state.loading);
  const state = useTriageStore((store) => store.state);

  useEffect(() => {
    if (state) {
      setAction((current) => ({
        ...current,
        request_human_review: state.human_review_required,
      }));
    }
  }, [state]);

  useEffect(() => {
    if (lastStep?.info?.suggestion) {
      const suggestion = lastStep.info.suggestion as AgentAction;
      setAction((current) => ({ ...current, ...suggestion, confidence: current.confidence ?? 0.75 }));
    }
  }, [lastStep]);

  return (
    <Card className="command-surface animate-rise overflow-hidden border-white/70 bg-white/75 shadow-panel backdrop-blur" style={{ animationDelay: "120ms" }}>
      <CardHeader className="border-b border-slate-200/70 bg-gradient-to-r from-white via-orange-50/70 to-sky-50/70">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-xl">Enterprise Operations Command</CardTitle>
            <CardDescription className="mt-1 font-medium text-slate-600">Align every triage decision with enterprise governance and risk policy.</CardDescription>
          </div>
          <div className="rounded-full border border-slate-200/70 bg-white/80 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-steel">
            Turn {state?.current_turn ?? 0}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5 p-6">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="metric-tile rounded-[1.2rem] p-4">
            <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-steel">
              Guidance
              <Bot className="h-4 w-4 text-ember" />
            </div>
            <div className="mt-3 text-sm text-slate-700">Use model suggestions as a baseline, then adjust for risk and policy.</div>
          </div>
          <div className="metric-tile rounded-[1.2rem] p-4">
            <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-steel">
              Confidence
              <Target className="h-4 w-4 text-sky-600" />
            </div>
            <div className="mt-3 text-sm text-slate-700">High-risk turns should either reduce confidence or request review.</div>
          </div>
          <div className="metric-tile rounded-[1.2rem] p-4">
            <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-steel">
              Governance
              <ShieldCheck className="h-4 w-4 text-lime-700" />
            </div>
            <div className="mt-3 text-sm text-slate-700">Escalate and annotate clearly when the thread enters executive territory.</div>
          </div>
        </div>

        <div className="rounded-[1.6rem] border border-slate-200/70 bg-slate-50/70 p-5">
          <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-steel">
            <Sparkles className="h-4 w-4 text-ember" /> Structured triage fields
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Category</label>
              <Select value={action.category} onChange={(event) => setAction({ ...action, category: event.target.value })}>
                {categories.map((value) => <option key={value}>{value}</option>)}
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Priority</label>
              <Select value={action.priority} onChange={(event) => setAction({ ...action, priority: event.target.value })}>
                {priorities.map((value) => <option key={value}>{value}</option>)}
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Department</label>
              <Select value={action.department} onChange={(event) => setAction({ ...action, department: event.target.value })}>
                {departments.map((value) => <option key={value}>{value}</option>)}
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Sentiment</label>
              <Select value={action.sentiment} onChange={(event) => setAction({ ...action, sentiment: event.target.value })}>
                {sentiments.map((value) => <option key={value}>{value}</option>)}
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Urgency</label>
              <Select value={action.urgency} onChange={(event) => setAction({ ...action, urgency: event.target.value })}>
                {urgencies.map((value) => <option key={value}>{value}</option>)}
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Spam</label>
              <Input type="number" min={0} max={1} value={action.spam ?? 0} onChange={(event) => setAction({ ...action, spam: Number(event.target.value) })} />
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Confidence</label>
              <Input type="number" min={0} max={1} step={0.05} value={action.confidence ?? 0.75} onChange={(event) => setAction({ ...action, confidence: Number(event.target.value) })} />
            </div>
            <div className="flex items-end">
              <label className="flex min-h-11 items-center gap-2 rounded-[1rem] border border-slate-200 bg-white px-4 py-3 text-sm text-steel">
                <input type="checkbox" checked={action.request_human_review ?? false} onChange={(event) => setAction({ ...action, request_human_review: event.target.checked })} />
                Request human review on this turn
              </label>
            </div>
          </div>
        </div>

        {state?.latest_prediction?.model_suggestion ? (
          <div className="rounded-[1.6rem] border border-sky-200 bg-sky-50/40 p-5 backdrop-blur-sm">
            <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.25em] text-sky-800">
              <Bot className="h-4 w-4" /> System Pre-triage (Read-only)
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl bg-white/60 p-3 shadow-sm border border-sky-100">
                <label className="mb-1 block text-[10px] font-bold uppercase text-sky-700/70">Category</label>
                <div className="text-sm font-semibold text-slate-800">{(state.latest_prediction.model_suggestion as any).category}</div>
              </div>
              <div className="rounded-xl bg-white/60 p-3 shadow-sm border border-sky-100">
                <label className="mb-1 block text-[10px] font-bold uppercase text-sky-700/70">Priority</label>
                <div className="text-sm font-semibold capitalize text-slate-800">{(state.latest_prediction.model_suggestion as any).priority}</div>
              </div>
              <div className="rounded-xl bg-white/60 p-3 shadow-sm border border-sky-100">
                <label className="mb-1 block text-[10px] font-bold uppercase text-sky-700/70">Department</label>
                <div className="text-sm font-semibold text-slate-800">{(state.latest_prediction.model_suggestion as any).department}</div>
              </div>
            </div>
          </div>
        ) : null}

        <div className="grid gap-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Customer-facing response draft</label>
            <Textarea rows={5} className="bg-white" value={action.response_draft ?? ""} onChange={(event) => setAction({ ...action, response_draft: event.target.value })} />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Internal triage note</label>
            <Textarea rows={3} className="bg-white" value={action.internal_note ?? ""} onChange={(event) => setAction({ ...action, internal_note: event.target.value })} />
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-[1.4rem] border border-slate-200/70 bg-white/80 p-4 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex items-center gap-2 text-sm text-steel">
            <input type="checkbox" checked={action.escalation ?? false} onChange={(event) => setAction({ ...action, escalation: event.target.checked })} />
            Escalate to a critical path
          </label>
          <Button className="h-12 rounded-[1.1rem] px-5" variant="ember" disabled={loading} onClick={() => void submitAction(action)}>
            Submit step()
          </Button>
        </div>

        {lastStep ? (
          <div className="rounded-[1.5rem] border border-amber-200 bg-amber-50/75 p-4 text-sm text-ink">
            <div className="font-semibold">Latest reward: {lastStep.reward.toFixed(3)}</div>
            <div className="mt-2 leading-6 text-steel">{lastStep.info.mistakes.length > 0 ? lastStep.info.mistakes.join(" | ") : "All required outputs matched for this task."}</div>
            {lastStep.info.next_turn_generated ? <div className="mt-3 font-medium text-ember">Next turn generated: {lastStep.info.next_turn_label}</div> : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

