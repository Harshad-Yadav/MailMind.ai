export type Difficulty = "easy" | "medium" | "hard";
export type FeedbackVerdict = "approve" | "revise" | "escalate";

export interface TaskDefinition {
  task_id: string;
  difficulty: Difficulty;
  title: string;
  description: string;
  required_outputs: string[];
  reward_weights: Record<string, number>;
  max_steps: number;
  supports_threading: boolean;
}

export interface EmailMessage {
  email_id: string;
  thread_id: string;
  subject: string;
  customer_name: string;
  customer_tier: string;
  received_at: string;
  sla_due_at: string;
  email_text: string;
}

export interface ThreadMessage {
  message_id: string;
  sender_role: "customer" | "agent" | "reviewer" | "system";
  subject: string;
  body: string;
  created_at: string;
  requires_response: boolean;
  tone?: string | null;
}

export interface HumanFeedbackEntry {
  feedback_id: string;
  reviewer: string;
  rating: number;
  verdict: FeedbackVerdict;
  comments: string;
  created_at: string;
}

export interface TriageObservation {
  environment_id: string;
  episode_id: string;
  task_id: string;
  difficulty: Difficulty;
  step_count: number;
  max_steps: number;
  current_turn: number;
  turn_label: string;
  email: EmailMessage;
  thread_messages: ThreadMessage[];
  pending_actions: string[];
  sla_status: "healthy" | "at_risk" | "breached";
  escalation_level: "none" | "team_lead" | "director" | "executive";
  human_review_required: boolean;
  done: boolean;
  history_length: number;
  completion_score: number;
  queue_depth: number;
  pending_sla_breaches: number;
  reviewer_backlog: number;
  customer_history_summary: string;
  business_impact: string;
  suggested_departments: string[];
  ownership_status: "unassigned" | "assigned" | "reassigned" | "escalated";
}

export interface RewardDetail {
  score: number;
  score_breakdown: Record<string, number>;
  matched: Record<string, boolean>;
  mistakes: string[];
  partial_progress: number;
  penalty_flags: string[];
}

export interface EnvironmentState {
  environment_id: string;
  episode_id: string;
  step_count: number;
  max_steps: number;
  current_turn: number;
  turn_label: string;
  task: TaskDefinition;
  email: EmailMessage;
  thread_messages: ThreadMessage[];
  pending_actions: string[];
  history: Array<Record<string, unknown>>;
  latest_prediction: Record<string, unknown>;
  human_feedback: HumanFeedbackEntry[];
  last_grade: Record<string, unknown>;
  sla_status: "healthy" | "at_risk" | "breached";
  escalation_level: "none" | "team_lead" | "director" | "executive";
  human_review_required: boolean;
  done: boolean;
  reward_total: number;
  completion_score: number;
  queue_depth: number;
  pending_sla_breaches: number;
  reviewer_backlog: number;
  customer_history_summary: string;
  business_impact: string;
  suggested_departments: string[];
  ownership_status: "unassigned" | "assigned" | "reassigned" | "escalated";
}

export interface ResetResponse {
  observation: TriageObservation;
  state: EnvironmentState;
}

export interface StepResponse {
  observation: TriageObservation;
  state: EnvironmentState;
  reward: number;
  reward_detail: RewardDetail;
  done: boolean;
  info: {
    score_breakdown: Record<string, number>;
    mistakes: string[];
    matched: Record<string, boolean>;
    partial_progress: number;
    penalty_flags: string[];
    suggestion: Record<string, unknown>;
    next_turn_generated?: boolean;
    next_turn_label?: string;
  };
}

export interface FeedbackResponse {
  observation: TriageObservation;
  state: EnvironmentState;
  feedback: HumanFeedbackEntry;
  reward_delta: number;
}

export interface AnalyticsResponse {
  dataset: {
    total_emails: number;
    category_distribution: Record<string, number>;
    priority_distribution: Record<string, number>;
    sentiment_distribution: Record<string, number>;
    urgency_distribution: Record<string, number>;
    spam_rate: number;
    strategic_customer_rate: number;
    sla_risk_distribution: Record<string, number>;
    model_metrics: Record<string, { description: string; backend: string; metrics: Record<string, number> }>;
  };
  model_suggestion: Record<string, unknown> | null;
  episode: {
    current_episode: {
      episode_id: string;
      current_turn: number;
      max_steps: number;
      thread_length: number;
      reward_curve: number[];
      matched_ratio_curve: number[];
      feedback_count: number;
      average_feedback_rating: number;
      pending_actions: string[];
      sla_status: string;
      escalation_level: string;
      completion_score: number;
      queue_depth: number;
      pending_sla_breaches: number;
      reviewer_backlog: number;
      ownership_status: string;
    } | null;
    suggested_action: Record<string, unknown> | null;
  };
}

export interface AgentAction {
  category?: string;
  priority?: string;
  department?: string;
  spam?: number;
  sentiment?: string;
  urgency?: string;
  response_draft?: string;
  escalation?: boolean;
  confidence?: number;
  internal_note?: string;
  request_human_review?: boolean;
  assigned_owner?: string;
  resolution_eta_hours?: number;
  customer_follow_up_required?: boolean;
  escalation_target?: "none" | "team_lead" | "director" | "executive";
}

export interface FeedbackRequest {
  reviewer: string;
  rating: number;
  verdict: FeedbackVerdict;
  comments: string;
}
