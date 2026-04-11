import { useEffect, useState } from "react";
import { Bot, ShieldCheck, Sparkles, Target, AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select, Textarea } from "@/components/ui/input";
import type { AgentAction } from "@/types/env";
import { useTriageStore } from "@/store/useTriageStore";

const categories = ["billing", "technical_support", "sales", "legal", "human_resources", "security", "operations", "partnership", ""];
const priorities = ["low", "medium", "high", "critical", ""];
const departments = ["finance", "support", "sales", "legal", "people_ops", "security", "operations", "partnerships", ""];
const sentiments = ["positive", "neutral", "negative", "frustrated", ""];
const urgencies = ["low", "medium", "high", "critical", ""];

// Empty default action to prevent automatic identical baseline passing
const initialAction: AgentAction = {
  category: "",
  priority: "",
  department: "",
  spam: 0,
  sentiment: "",
  urgency: "",
  response_draft: "",
  escalation: false,
  confidence: 0.75,
  internal_note: "",
  request_human_review: false,
};

export function DecisionPanel() {
  const [action, setAction] = useState<AgentAction>(initialAction);
  const [autoMode, setAutoMode] = useState<boolean>(false);
  const [submissionWarning, setSubmissionWarning] = useState<string | null>(null);

  const submitAction = useTriageStore((state) => state.submitAction);
  const lastStep = useTriageStore((state) => state.lastStep);
  const loading = useTriageStore((state) => state.loading);
  const state = useTriageStore((store) => store.state);
  const analytics = useTriageStore((store) => store.analytics);

  // Sync state explicitly per episode to prevent bleed
  useEffect(() => {
    if (state) {
      setAction((current) => ({
        ...initialAction,
        request_human_review: state.human_review_required,
      }));
      setSubmissionWarning(null);
    }
  }, [state?.episode_id]);

  // Hook auto-fill mechanics
  useEffect(() => {
    if (autoMode) {
      let suggested: Partial<AgentAction> = {};
      if (lastStep?.info?.suggestion) {
        suggested = lastStep.info.suggestion as Partial<AgentAction>;
      } else if (analytics?.episode?.suggested_action) {
        suggested = (analytics.episode?.suggested_action ?? {}) as Partial<AgentAction>;
      }
      
      if (Object.keys(suggested).length > 0) {
        setAction((current) => ({
          ...current,
          ...suggested,
          confidence: suggested.confidence ?? 0.85,
          internal_note: suggested.internal_note || "Auto-routed via model suggestion.",
          response_draft: suggested.response_draft || "",
        }));
      }
    }
  }, [autoMode, lastStep, analytics?.episode?.suggested_action, state?.episode_id]);

  const handleSubmit = async () => {
    // Validate submission to ensure fields were modified
    if (!autoMode && action.category === "" && action.priority === "") {
      setSubmissionWarning("Please select valid fields or enable AUTO MODE.");
      return;
    }
    setSubmissionWarning(null);
    await submitAction(action);
  };

  const getFieldErrorClass = (field: string) => {
    if (lastStep && state?.last_grade) {
      const matched = state.last_grade.matched as Record<string, boolean> | undefined;
      if (matched && matched[field] === false) {
        return "border-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)] ring-red-500";
      }
    }
    return autoMode ? "bg-slate-100 opacity-80 cursor-not-allowed" : "";
  };

  const getMistakeText = (field: string) => {
    const mistakes = lastStep?.info?.mistakes as string[] | undefined;
    if (!mistakes) return null;
    const mistake = mistakes.find((m: string) => m.toLowerCase().startsWith(field.toLowerCase()));
    return mistake ? <span className="text-[10px] text-red-600 font-medium block mt-1">{mistake}</span> : null;
  };

  return (
    <Card className="command-surface animate-rise overflow-hidden border-white/70 bg-white/75 shadow-panel backdrop-blur" style={{ animationDelay: "120ms" }}>
      <CardHeader className="border-b border-slate-200/70 bg-gradient-to-r from-white via-orange-50/70 to-sky-50/70">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-xl">Enterprise Operations Command</CardTitle>
            <CardDescription className="mt-1 font-medium text-slate-600">Align every triage decision with enterprise governance and risk policy.</CardDescription>
          </div>
          <div className="flex items-center gap-3">
             <div className="flex items-center border border-slate-300 rounded-lg overflow-hidden text-xs font-bold uppercase overflow-hidden">
                <button 
                  onClick={() => setAutoMode(false)} 
                  className={`px-3 py-1.5 transition-colors ${!autoMode ? 'bg-steel text-white' : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}
                >
                  Manual
                </button>
                <button 
                  onClick={() => setAutoMode(true)} 
                  className={`px-3 py-1.5 transition-colors ${autoMode ? 'bg-emerald-600 text-white' : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}
                >
                  Auto
                </button>
             </div>
            <div className="rounded-full border border-slate-200/70 bg-white/80 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-steel">
              Turn {state?.current_turn ?? 0}
            </div>
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

        {submissionWarning && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 text-red-700 px-4 py-3 text-sm font-medium border border-red-200">
            <AlertTriangle className="h-4 w-4" />
            {submissionWarning}
          </div>
        )}

        <div className="rounded-[1.6rem] border border-slate-200/70 bg-slate-50/70 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-steel">
              <Sparkles className="h-4 w-4 text-ember" /> Structured triage fields
            </div>
            {autoMode && <span className="text-[10px] uppercase font-bold text-emerald-600">Model Tracking Enabled</span>}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Category</label>
              <Select disabled={autoMode} className={getFieldErrorClass("category")} value={action.category} onChange={(event) => setAction({ ...action, category: event.target.value })}>
                {categories.map((value) => <option key={value}>{value}</option>)}
              </Select>
              {getMistakeText("category")}
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Priority</label>
              <Select disabled={autoMode} className={getFieldErrorClass("priority")} value={action.priority} onChange={(event) => setAction({ ...action, priority: event.target.value })}>
                {priorities.map((value) => <option key={value}>{value}</option>)}
              </Select>
              {getMistakeText("priority")}
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Department</label>
              <Select disabled={autoMode} className={getFieldErrorClass("department")} value={action.department} onChange={(event) => setAction({ ...action, department: event.target.value })}>
                {departments.map((value) => <option key={value}>{value}</option>)}
              </Select>
              {getMistakeText("department")}
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Sentiment</label>
              <Select disabled={autoMode} className={getFieldErrorClass("sentiment")} value={action.sentiment} onChange={(event) => setAction({ ...action, sentiment: event.target.value })}>
                {sentiments.map((value) => <option key={value}>{value}</option>)}
              </Select>
              {getMistakeText("sentiment")}
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Urgency</label>
              <Select disabled={autoMode} className={getFieldErrorClass("urgency")} value={action.urgency} onChange={(event) => setAction({ ...action, urgency: event.target.value })}>
                {urgencies.map((value) => <option key={value}>{value}</option>)}
              </Select>
              {getMistakeText("urgency")}
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Spam</label>
              <Input disabled={autoMode} className={getFieldErrorClass("spam_guardrail")} type="number" min={0} max={1} value={action.spam ?? 0} onChange={(event) => setAction({ ...action, spam: Number(event.target.value) })} />
              {getMistakeText("spam")}
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Confidence</label>
              <Input disabled={autoMode} className={getFieldErrorClass("confidence_calibration")} type="number" min={0} max={1} step={0.05} value={action.confidence ?? 0.75} onChange={(event) => setAction({ ...action, confidence: Number(event.target.value) })} />
              {getMistakeText("confidence")}
            </div>
            <div className="flex items-end">
              <label className={`flex min-h-11 items-center gap-2 rounded-[1rem] border bg-white px-4 py-3 text-sm text-steel ${getFieldErrorClass("human_review")} ${autoMode ? 'border-slate-300' : 'border-slate-200'}`}>
                <input disabled={autoMode} type="checkbox" checked={action.request_human_review ?? false} onChange={(event) => setAction({ ...action, request_human_review: event.target.checked })} />
                Request human review on this turn
              </label>
            </div>
          </div>
        </div>

        <div className="grid gap-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Customer-facing response draft</label>
            <Textarea disabled={autoMode} rows={3} className={`bg-white ${getFieldErrorClass("response_draft")}`} value={action.response_draft ?? ""} onChange={(event) => setAction({ ...action, response_draft: event.target.value })} />
            {getMistakeText("response_draft")}
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-steel">Internal triage note</label>
            <Textarea disabled={autoMode} rows={2} className={`bg-white ${getFieldErrorClass("internal_note")}`} value={action.internal_note ?? ""} onChange={(event) => setAction({ ...action, internal_note: event.target.value })} />
            {getMistakeText("internal")}
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-[1.4rem] border border-slate-200/70 bg-white/80 p-4 sm:flex-row sm:items-center sm:justify-between">
          <label className={`flex items-center gap-2 text-sm text-steel ${getFieldErrorClass("escalation")}`}>
            <input disabled={autoMode} type="checkbox" checked={action.escalation ?? false} onChange={(event) => setAction({ ...action, escalation: event.target.checked })} />
            Escalate to a critical path
          </label>
          <Button className="h-12 rounded-[1.1rem] px-5" variant="ember" disabled={loading} onClick={handleSubmit}>
            Submit step()
          </Button>
        </div>

        {lastStep ? (
          <div className={`rounded-[1.5rem] border p-4 text-sm ${lastStep.reward < 1.0 ? "border-amber-200 bg-amber-50/75 text-amber-900" : "border-emerald-200 bg-emerald-50/75 text-emerald-900"}`}>
            <div className="font-semibold">Latest reward: {lastStep.reward.toFixed(3)}</div>
            <div className="mt-2 leading-6">{lastStep.info.mistakes.length > 0 ? lastStep.info.mistakes.map((m: string, i: number) => <div key={i}>• {m}</div>) : "All required outputs matched perfectly for this task."}</div>
            {lastStep.info.next_turn_generated ? <div className="mt-3 font-medium text-ember">Next turn generated: {lastStep.info.next_turn_label}</div> : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
