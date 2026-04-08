import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, BarChart3, Gauge, Radar } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatLabel } from "@/lib/utils";
import { useTriageStore } from "@/store/useTriageStore";

function toSeries(record?: Record<string, number>) {
  return Object.entries(record ?? {}).map(([name, value]) => ({ name: formatLabel(name), value }));
}

export function AnalyticsPanel() {
  const analytics = useTriageStore((state) => state.analytics);
  const lastStep = useTriageStore((state) => state.lastStep);
  const episode = analytics?.episode.current_episode;
  const rewardCurve = (episode?.reward_curve ?? []).map((value, index) => ({ step: `S${index + 1}`, reward: value }));
  const matchedCurve = (episode?.matched_ratio_curve ?? []).map((value, index) => ({ step: `S${index + 1}`, matched: Number((value * 100).toFixed(0)) }));
  const modelMetrics = Object.entries(analytics?.dataset.model_metrics ?? {}).map(([name, payload]) => ({
    name: formatLabel(name),
    accuracy: Number((((payload as { metrics: Record<string, number> }).metrics.accuracy ?? 0) * 100).toFixed(1)),
  }));

  const episodeStats = [
    {
      label: "Thread length",
      value: String(episode?.thread_length ?? 0),
      note: "Messages in current episode",
      icon: Activity,
    },
    {
      label: "Completion",
      value: `${(((episode?.completion_score ?? 0) * 100) || 0).toFixed(0)}%`,
      note: `${formatLabel(episode?.sla_status ?? "healthy")} workflow state`,
      icon: Gauge,
    },
    {
      label: "Escalation",
      value: formatLabel(episode?.escalation_level ?? "none"),
      note: `${episode?.feedback_count ?? 0} feedback events`,
      icon: Radar,
    },
  ];

  return (
    <Card className="command-surface animate-rise overflow-hidden border-white/70 bg-white/75 shadow-panel backdrop-blur" style={{ animationDelay: "180ms" }}>
      <CardHeader className="border-b border-slate-200/70 bg-gradient-to-r from-white via-sky-50/70 to-orange-50/60">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-xl">Advanced Analytics and Evaluation</CardTitle>
            <CardDescription className="mt-1">Reward curves, match rates, model benchmarks, and live episode telemetry.</CardDescription>
          </div>
          {lastStep ? <Badge tone={lastStep.reward >= 0 ? "medium" : "critical"}>Reward {lastStep.reward.toFixed(2)}</Badge> : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-6 p-6">
        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-[1.8rem] bg-slate-950 p-5 text-white shadow-panel">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
              <BarChart3 className="h-4 w-4 text-amber-300" /> Episode telemetry
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
              {episodeStats.map((stat) => {
                const Icon = stat.icon;
                return (
                  <div key={stat.label} className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-slate-400">
                      {stat.label}
                      <Icon className="h-4 w-4 text-white" />
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-white">{stat.value}</div>
                    <div className="mt-1 text-xs leading-5 text-slate-400">{stat.note}</div>
                  </div>
                );
              })}
            </div>
            <div className="mt-5 rounded-[1.35rem] border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Suggested action snapshot</div>
              <div className="mt-3 grid gap-2">
                {Object.entries(analytics?.model_suggestion ?? {}).slice(0, 5).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-3 rounded-[1rem] bg-white/5 px-3 py-2 text-sm">
                    <span className="text-slate-400">{formatLabel(key)}</span>
                    <span className="font-medium text-white">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-[1.6rem] border border-slate-200/70 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-steel">Category mix</p>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={toSeries(analytics?.dataset.category_distribution)}>
                    <CartesianGrid vertical={false} strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-24} height={70} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#ea580c" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-[1.6rem] border border-slate-200/70 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-steel">Priority distribution</p>
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={toSeries(analytics?.dataset.priority_distribution)} dataKey="value" nameKey="name" outerRadius={84} fill="#0284c7" />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <div className="rounded-[1.6rem] border border-slate-200/70 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-steel">Reward curve</p>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={rewardCurve}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis dataKey="step" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="reward" stroke="#ea580c" fill="#fed7aa" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-slate-200/70 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-steel">Matched ratio</p>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={matchedCurve}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis dataKey="step" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="matched" stroke="#0284c7" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-[1.6rem] border border-slate-200/70 bg-white p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-steel">Model benchmark accuracy</p>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modelMetrics} layout="vertical">
                  <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="accuracy" fill="#3f6212" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
