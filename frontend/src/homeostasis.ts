import type { Homeostasis, NeedKey, State } from './types';

export const needKeys: NeedKey[] = ['physical_activity', 'mental_stimulation', 'social_interaction', 'close_connection', 'goal_progression'];
export function defaultHomeostasis(): Homeostasis {
  return { mental_effort_weight: 0.4, needs: Object.fromEntries(needKeys.map(key => [key, { lower: 0.6, upper: 0.8, sensitivity: 1 }])) as Homeostasis['needs'] };
}
export function homeostasisValid(value: Homeostasis) {
  return Number.isFinite(value.mental_effort_weight) && value.mental_effort_weight >= 0 && value.mental_effort_weight <= 1 &&
    Object.keys(value.needs).length === needKeys.length && needKeys.every(key => {
      const need = value.needs[key];
      return need && Object.keys(need).length === 3 && Object.keys(need).every(parameter => ['lower', 'upper', 'sensitivity'].includes(parameter)) && Object.values(need).every(Number.isFinite) && need.lower > 0 && need.lower <= need.upper && need.upper < 1 && need.sensitivity >= 0 && need.sensitivity <= 64;
    });
}
export function currentStateValid(state: State) {
  const unit = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
  return [state.mental_energy, state.physical_energy].every(value => value == null || unit(value)) && unit(state.acute_stress) &&
    Object.entries(state.need_satisfaction ?? {}).every(([key, value]) => needKeys.includes(key as NeedKey) && unit(value)) && /^\d{4}-\d{2}-\d{2}$/.test(state.date);
}
