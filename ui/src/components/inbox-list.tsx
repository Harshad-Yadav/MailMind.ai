import { AlertTriangle, ArrowRightCircle, CheckCircle2, Clock3, MailOpen, ShieldAlert, TimerReset } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatLabel } from "@/lib/utils";
import { useTriageStore } from "@/store/useTriageStore";

const slaTone = {
  healthy: "medium",
  at_risk: "high",
  breached: "critical",
} as const;

const senderStyles = {
  customer: "border-amber-100 bg-white",
  agent: "border-sky-100 bg-sky-50/60",
  reviewer: "border-rose-100 bg-rose-50/70",
  system: "border-slate-200 bg-slate-50",
} as const;

export function InboxList() {
  const state = useTriageStore((store) => store.state);

  if (!state) {
    return (
      <Card className="command-surface">
        <CardHeader>
          <CardTitle>Inbox</CardTitle>
          <CardDescription>Waiting for environment reset.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="command-surface animate-rise overflow-hidden border-white/70 bg-white/65 shadow-panel backdrop-blur">
      <CardHeader className="border-b border-slate-200/70 bg-white/55">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-3">
            <div>
              <CardTitle className="text-2xl">Live Enterprise Thread</CardTitle>
              <CardDescription className="mt-1 text-sm">{state.task.title} · Turn {state.current_turn} of {state.max_steps}</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={state.task.difficulty === "hard" ? "critical" : state.task.difficulty === "medium" ? "high" : "medium"}>{state.task.difficulty}</Badge>
              <Badge tone={slaTone[state.sla_status]}>{formatLabel(state.sla_status)}</Badge>
              <Badge tone={state.escalation_level === "executive" ? "critical" : state.escalation_level === "director" ? "high" : "medium"}>{formatLabel(state.escalation_level)}</Badge>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:w-[28rem]">
            <div className="metric-tile rounded-[1.25rem] p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-steel">Progress</div>
              <div className="mt-2 text-2xl font-semibold text-ink">{(state.completion_score * 100).toFixed(0)}%</div>
              <div className="mt-1 text-xs text-steel">Thread completion signal</div>
            </div>
            <div className="metric-tile rounded-[1.25rem] p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-steel">Feedback</div>
              <div className="mt-2 text-2xl font-semibold text-ink">{state.human_feedback.length}</div>
              <div className="mt-1 text-xs text-steel">Reviewer interactions</div>
            </div>
            <div className="metric-tile rounded-[1.25rem] p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-steel">Reward</div>
              <div className="mt-2 text-2xl font-semibold text-ink">{state.reward_total.toFixed(2)}</div>
              <div className="mt-1 text-xs text-steel">Cumulative episode score</div>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 p-6">
        <div className="glow-ring rounded-[1.8rem] bg-gradient-to-br from-white via-orange-50/70 to-sky-50/60 p-6">
          <div className="flex flex-wrap items-center gap-3 text-xs text-steel">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-2"><MailOpen className="h-4 w-4 text-ember" /> {state.email.customer_name}</span>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-2"><Clock3 className="h-4 w-4 text-sky-600" /> Received {new Date(state.email.received_at).toLocaleString()}</span>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-2"><TimerReset className="h-4 w-4 text-lime-700" /> SLA {new Date(state.email.sla_due_at).toLocaleString()}</span>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <h2 className="text-3xl font-semibold leading-tight text-ink">{state.email.subject}</h2>
            {state.human_review_required ? (
              <div className="inline-flex items-center gap-2 rounded-full bg-rose-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-rose-700">
                <ShieldAlert className="h-4 w-4" /> Human review recommended
              </div>
            ) : (
              <div className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-700">
                <CheckCircle2 className="h-4 w-4" /> Autonomous handling allowed
              </div>
            )}
          </div>
          <p className="mt-2 text-sm text-steel">Tier: {formatLabel(state.email.customer_tier)} · {state.turn_label}</p>
          <p className="mt-5 whitespace-pre-wrap text-sm leading-8 text-slate-700">{state.email.email_text}</p>
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
          <div className="rounded-[1.8rem] border border-slate-200/70 bg-white/85 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-steel">Thread Timeline</p>
              <div className="text-xs text-steel">{state.thread_messages.length} messages</div>
            </div>
            <div className="thread-lane mt-5 space-y-4 pl-8">
              {state.thread_messages.map((message) => (
                <div key={message.message_id} className="thread-node">
                  <div className={`rounded-[1.35rem] border p-4 shadow-sm ${senderStyles[message.sender_role]}`}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-ink">{message.subject}</div>
                        <div className="mt-1 text-[11px] uppercase tracking-[0.2em] text-steel">{formatLabel(message.sender_role)}</div>
                      </div>
                      <div className="text-xs text-steel">{new Date(message.created_at).toLocaleString()}</div>
                    </div>
                    <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{message.body}</div>
                    <div className="mt-4 flex flex-wrap gap-2 text-xs text-steel">
                      {message.requires_response ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-white/75 px-3 py-1.5"><ArrowRightCircle className="h-3.5 w-3.5" />Needs response</span>
                      ) : null}
                      {message.tone ? <span className="rounded-full bg-white/75 px-3 py-1.5">Tone: {formatLabel(message.tone)}</span> : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4 rounded-[1.8rem] bg-slate-950 p-5 text-white shadow-panel">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Pending actions</p>
              <div className="mt-3 space-y-2">
                {state.pending_actions.map((item) => (
                  <div key={item} className="rounded-[1.1rem] border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-100">
                    {formatLabel(item)}
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <div className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Current turn</div>
                <div className="mt-2 text-2xl font-semibold">{state.current_turn}</div>
                <div className="mt-1 text-xs text-slate-400">{state.turn_label}</div>
              </div>
              <div className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Escalation</div>
                <div className="mt-2 text-2xl font-semibold">{formatLabel(state.escalation_level)}</div>
                <div className="mt-1 text-xs text-slate-400">Current governance path</div>
              </div>
            </div>

            {state.last_grade && Object.keys(state.last_grade).length > 0 ? (
              <div className="rounded-[1.35rem] border border-amber-400/20 bg-amber-200/10 p-4 text-sm text-slate-100">
                <div className="flex items-center gap-2 font-semibold text-amber-100">
                  <AlertTriangle className="h-4 w-4" /> Latest review notes
                </div>
                <div className="mt-2 leading-6 text-slate-300">
                  {((state.last_grade.mistakes as string[] | undefined) ?? []).join(" | ") || "Current turn evaluated without critical issues."}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

