import { BellRing, BriefcaseBusiness, Flame, ShieldAlert, Sparkles, Workflow } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatLabel } from "@/lib/utils";
import { useTriageStore } from "@/store/useTriageStore";

export function DashboardHeader() {
  const tasks = useTriageStore((state) => state.tasks);
  const selectedTaskId = useTriageStore((state) => state.selectedTaskId);
  const resetEnv = useTriageStore((state) => state.resetEnv);
  const currentState = useTriageStore((state) => state.state);
  const analytics = useTriageStore((state) => state.analytics);

  const headerStats = [
    {
      label: "Thread Progress",
      value: currentState ? `${currentState.current_turn}/${currentState.max_steps}` : "0/0",
      note: currentState?.turn_label ?? "Awaiting reset",
      icon: Workflow,
    },
    {
      label: "Completion",
      value: `${(((currentState?.completion_score ?? 0) * 100) || 0).toFixed(0)}%`,
      note: currentState?.sla_status ? `${formatLabel(currentState.sla_status)} SLA state` : "No active episode",
      icon: Flame,
    },
    {
      label: "Feedback Avg",
      value: analytics?.episode.current_episode ? analytics.episode.current_episode.average_feedback_rating.toFixed(1) : "0.0",
      note: analytics?.episode.current_episode ? `${analytics.episode.current_episode.feedback_count} reviewer events` : "No review events yet",
      icon: Sparkles,
    },
  ];

  return (
    <header className="command-surface hero-noise animate-rise rounded-[2.25rem] border border-white/60 p-6 shadow-panel backdrop-blur lg:p-8">
      <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
        <div className="max-w-4xl space-y-5">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200/80 bg-white/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-steel">
            <BellRing className="h-4 w-4 text-ember" />
            Email Operations Command
          </div>
          <div className="space-y-3">
            <h1 className="max-w-4xl text-4xl font-semibold leading-[1.05] text-ink sm:text-5xl xl:text-6xl">
              Train agents inside a living enterprise inbox, not a toy classifier.
            </h1>
            <p className="max-w-3xl text-sm leading-7 text-steel sm:text-base">
              The dashboard now behaves like an operations war room: threaded escalations, reviewer intervention, SLA pressure, and live scoring across each turn of the episode.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-steel">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/75 px-3 py-2 shadow-sm">
              <BriefcaseBusiness className="h-4 w-4 text-ember" /> Multi-turn enterprise workflows
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white/75 px-3 py-2 shadow-sm">
              <ShieldAlert className="h-4 w-4 text-sky-600" /> Reviewer and escalation controls
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white/75 px-3 py-2 shadow-sm">
              <Workflow className="h-4 w-4 text-lime-700" /> Reward and telemetry loop
            </div>
          </div>
        </div>

        <div className="w-full max-w-xl rounded-[1.75rem] border border-slate-200/80 bg-white/80 p-4 shadow-lg backdrop-blur xl:p-5">
          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-steel">Scenario Selector</div>
              <select
                className="w-full rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-ember"
                value={selectedTaskId}
                onChange={(event) => void resetEnv(event.target.value)}
              >
                {tasks.map((task) => (
                  <option key={task.task_id} value={task.task_id}>
                    {formatLabel(task.difficulty)}: {task.title}
                  </option>
                ))}
              </select>
            </div>
            <Button variant="ember" className="h-12 rounded-[1.1rem] px-5" onClick={() => void resetEnv(selectedTaskId)}>
              Reset Episode
            </Button>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {headerStats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div key={stat.label} className="metric-tile rounded-[1.35rem] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-steel">{stat.label}</div>
                    <Icon className="h-4 w-4 text-ember" />
                  </div>
                  <div className="mt-3 text-2xl font-semibold text-ink">{stat.value}</div>
                  <div className="mt-1 text-xs leading-5 text-steel">{stat.note}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </header>
  );
}

