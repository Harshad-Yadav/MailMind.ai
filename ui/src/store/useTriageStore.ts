import { create } from "zustand";

import type { AgentAction, AnalyticsResponse, EnvironmentState, FeedbackRequest, FeedbackResponse, StepResponse, TaskDefinition } from "@/types/env";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

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

interface TriageStore {
  tasks: TaskDefinition[];
  state: EnvironmentState | null;
  analytics: AnalyticsResponse | null;
  lastStep: StepResponse | null;
  lastFeedback: FeedbackResponse | null;
  loading: boolean;
  error: string | null;
  selectedTaskId: string;
  autoMode: boolean;
  formData: AgentAction;
  loadTasks: () => Promise<void>;
  resetEnv: (taskId?: string) => Promise<void>;
  fetchAnalytics: () => Promise<void>;
  submitAction: (actionOverride?: AgentAction) => Promise<void>;
  submitFeedback: (feedback: FeedbackRequest) => Promise<void>;
  setFormData: (data: Partial<AgentAction>) => void;
  setAutoMode: (enabled: boolean) => void;
  syncAutoFill: () => void;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const useTriageStore = create<TriageStore>((set, get) => ({
  tasks: [],
  state: null,
  analytics: null,
  lastStep: null,
  lastFeedback: null,
  loading: false,
  error: null,
  selectedTaskId: "task-email-classification-easy",
  autoMode: false,
  formData: initialAction,

  setFormData: (data) => {
    set((state) => ({ formData: { ...state.formData, ...data } }));
  },

  setAutoMode: (enabled) => {
    set({ autoMode: enabled });
    if (enabled) get().syncAutoFill();
  },

  syncAutoFill: () => {
    const { state, analytics, lastStep } = get();
    let suggested: Partial<AgentAction> = {};
    
    // Priority: lastStep suggestion > analytics current episode suggestion
    if (lastStep?.info?.suggestion) {
      suggested = lastStep.info.suggestion as Partial<AgentAction>;
    } else if (analytics?.episode?.suggested_action) {
      suggested = analytics.episode.suggested_action as Partial<AgentAction>;
    }

    if (Object.keys(suggested).length > 0) {
      set((s) => ({
        formData: {
          ...s.formData,
          ...suggested,
          confidence: suggested.confidence ?? 0.85,
          internal_note: suggested.internal_note || "Auto-routed via model suggestion.",
          response_draft: suggested.response_draft || "",
        }
      }));
    }
  },

  loadTasks: async () => {
    set({ loading: true, error: null });
    try {
      const tasks = await api<TaskDefinition[]>("/tasks");
      set({ tasks, loading: false, selectedTaskId: tasks[0]?.task_id ?? "task-email-classification-easy" });
    } catch (error) {
      set({ loading: false, error: (error as Error).message });
    }
  },

  resetEnv: async (taskId) => {
    const selected = taskId ?? get().selectedTaskId;
    set({ loading: true, error: null, selectedTaskId: selected });
    try {
      const params = new URLSearchParams({ task_id: selected });
      const data = await api<{ state: EnvironmentState }>(`/reset?${params.toString()}`, { method: "POST" });
      
      // Clean reset
      set({ 
        state: data.state, 
        lastStep: null, 
        lastFeedback: null, 
        loading: false,
        formData: { ...initialAction, request_human_review: data.state.human_review_required } 
      });
      
      await get().fetchAnalytics();
      if (get().autoMode) get().syncAutoFill();
    } catch (error) {
      set({ loading: false, error: (error as Error).message });
    }
  },

  fetchAnalytics: async () => {
    try {
      const analytics = await api<AnalyticsResponse>("/analytics");
      set({ analytics });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  submitAction: async (actionOverride) => {
    const action = actionOverride ?? get().formData;
    set({ loading: true, error: null });
    try {
      const result = await api<StepResponse>("/step", {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      
      set({ 
        state: result.state, 
        lastStep: result, 
        loading: false,
        formData: { ...initialAction, request_human_review: result.state.human_review_required }
      });
      
      await get().fetchAnalytics();
      if (get().autoMode) get().syncAutoFill();
    } catch (error) {
      set({ loading: false, error: (error as Error).message });
    }
  },

  submitFeedback: async (feedback) => {
    set({ loading: true, error: null });
    try {
      const result = await api<FeedbackResponse>("/feedback", {
        method: "POST",
        body: JSON.stringify(feedback),
      });
      set({ state: result.state, lastFeedback: result, loading: false });
      await get().fetchAnalytics();
    } catch (error) {
      set({ loading: false, error: (error as Error).message });
    }
  },
}));

