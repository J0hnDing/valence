export type Family = 'asymmetric_signed' | 'cost' | 'signed_effort' | 'order_preference' | 'reward' | 'reward_overload';
export interface Feature {
  temporal_basis: 'rate' | 'one_time';
  key: string; display_name: string; minimum: number; maximum: number; definition: string;
  anchors: { value: number; description: string }[]; belongs: string[]; excludes: string[];
  distinction: string; response_family: Family; examples: { value: number; description: string }[];
}
export interface Person { id: string; name: string; description?: string | null; created_at: string; updated_at: string }
export interface ActionInput { title: string; duration_minutes: number; net_money_cost: number; features: Record<string, number>; feature_notes: Record<string, string> | null; feature_duration_minutes?: Record<string, number> | null }
export interface Action extends Omit<ActionInput, 'net_money_cost'> { net_money_cost?: number; id: string; created_at: string; updated_at: string; converted_from_legacy?: boolean }
export type NeedKey = 'physical_activity' | 'mental_stimulation' | 'social_interaction' | 'close_connection' | 'goal_progression';
export interface NeedParameters { lower: number; upper: number; sensitivity: number }
export interface HistoricalNeedParameters extends NeedParameters { rate: number }
export interface Homeostasis { needs: Record<NeedKey, NeedParameters>; mental_effort_weight: number }
export interface State { mental_energy?: number | null; physical_energy?: number | null; need_satisfaction?: Partial<Record<NeedKey, number>>; acute_stress: number; date: string; notes?: string | null }
export type Response = { family: Family } & Record<string, number | Family>;
export interface Model {
  homeostasis?: Homeostasis;
  resources?: { time_value: number; money_value: number };
  features: Record<string, Response>;
  transient: Record<string, number>;
  aftereffects: Record<string, { sensitivity: number; half_life_hours: number }>;
}
export interface ModelVersion { id: string; person_id: string; version: number; model: Model; created_at: string; converted_from_legacy?: boolean }
export type PersonInitialization = { method: 'default' } | { method: 'copy'; person_id: string; model_version_id: string } | { method: 'quiz'; version: '5'; answers: Record<string, number | null> };
export interface QuizQuestion { id: string; prompt: string; example: string }
export interface InitializationQuiz { version: '5'; instructions: string[]; options: { label: string; value: number }[]; questions: QuizQuestion[] }
export interface InitializationPreview { model: Model; warnings: string[]; defaulted: string[]; answered: number; total: number; insights: { label: string; description: string }[] }
export interface FeatureTrace { feature_key: string; raw_value: number; response_family: Family; effective_parameters: Record<string, number>; formula: string; utility_rate_contribution: number | null; temporal_basis?: 'rate' | 'one_time'; response_value?: number; utility_contribution?: number; exposure_duration_minutes?: number | null; exposure_duration_hours?: number | null }
export interface AftereffectTrace { name: string; trigger: number; sensitivity: number; half_life_hours: number; sign: number; initial_amplitude: number; integrated_utility: number; formula: string }
export interface TraceNode { id: string; label: string; kind: string; value: unknown; definition: string; inputs: Record<string, unknown>; parameters: Record<string, unknown>; formula: string; note?: string | null }
export interface TraceGraph { nodes: TraceNode[]; edges: { source: string; target: string }[] }
export interface Result {
  base_utility?: number; needs_utility?: number; energy_utility?: number;
  need_traces?: (NeedTrace | HistoricalNeedTrace)[]; energy_traces?: EnergyTrace[];
  action_id: string; action_snapshot: Action; rank: number; during_rate: number; during_utility: number;
  aftereffect_utility: number; total_utility: number; utility_per_action_hour: number | null;
  one_time_utility?: number; time_cost?: number; money_cost?: number; resource_cost?: number; gross_utility?: number;
  feature_traces: FeatureTrace[]; aftereffect_traces: AftereffectTrace[]; graph: TraceGraph;
}
export interface Evaluation {
  engine_version?: '1' | '2' | '3' | '4' | '5' | '6' | '7';
  id: string; person_id: string; person_name: string; model_version_id: string; model_version: number;
  model_snapshot: Model | (Omit<Model, 'homeostasis'> & { homeostasis: { needs: Record<NeedKey, HistoricalNeedParameters>; mental_effort_weight: number } }); state: State; horizon_hours: number; created_at: string; results: Result[];
}
export interface NeedTrace { need_key: NeedKey; available: boolean; current_satisfaction: number | null; feature_value: number; parameters: NeedParameters; deprivation: number | null; overload: number | null; pressure: number; utility_contribution: number; formula: string }
export interface HistoricalNeedTrace { need_key: NeedKey; available: boolean; current_satisfaction: number | null; predicted_satisfaction: number | null; impact: number; parameters: HistoricalNeedParameters; value_before: number | null; value_after: number | null; utility_contribution: number; formula: string }
export interface EnergyTrace { feature_key: string; energy: number | null; alpha: number; modifier: number; base_contribution: number; adjusted_contribution: number; utility_contribution: number; formula: string }
export interface HistoryEntry { id: string; person_id: string; person_name: string; model_version: number; created_at: string; horizon_hours: number; action_count: number; top_action_title: string; top_total_utility: number }
export interface Preview { features: Record<string, { points: { x: number; y: number }[]; preferred_exposure: number | null }>; aftereffects: Record<string, { points: { x: number; y: number }[] }> }
