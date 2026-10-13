import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { Ranking } from '../Compare';
import { EvaluationPage } from '../Evaluation';
import { ModelEditor } from '../PersonModel';
import fixtures from './fixtures.json';
import type { Action, Evaluation, Feature, Model, ModelVersion, State } from '../types';

vi.mock('../Graph', () => ({ ComputationGraph: () => <div>Recorded graph</div>, output: (value: unknown) => String(value) }));
vi.mock('recharts', () => ({ ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, CartesianGrid: () => null, Line: () => null, XAxis: () => null, YAxis: () => null, Tooltip: () => null }));

const ontology = fixtures.ontology as Feature[];
const model = fixtures.model as Model;
const state: State = { mental_energy: 0.192, physical_energy: 1, acute_stress: 0, date: '2026-10-12' };
const version: ModelVersion = { id: 'model-rest', person_id: 'person-rest', version: 3, model, created_at: '2026-10-12T12:00:00Z' };
const restFormula = 'clip(1 + alpha * (0.7 - mental_energy), 1, 2)';

function savedEvaluation(engine: '7' | '8'): Evaluation {
  const restEnergy = engine === '8';
  const action: Action = { id: 'rest', title: 'Rest', duration_minutes: 60, features: { mental_rest: 1 }, feature_notes: null, created_at: version.created_at, updated_at: version.created_at };
  return {
    engine_version: engine, id: `evaluation-${engine}`, person_id: version.person_id, person_name: 'John', model_version_id: version.id, model_version: version.version, model_snapshot: model, state, horizon_hours: 24, created_at: version.created_at,
    results: [{ action_id: action.id, action_snapshot: action, rank: 1, during_rate: 1.2, during_utility: 1.2, one_time_utility: 0, base_utility: 1.2, needs_utility: 0, energy_utility: restEnergy ? 1.2 : 0, gross_utility: restEnergy ? 2.4 : 1.2, total_utility: restEnergy ? 2.4 : 1.2, utility_per_action_hour: restEnergy ? 2.4 : 1.2, aftereffect_utility: 0, resource_cost: 0, time_cost: 0, money_cost: 0,
      feature_traces: [{ feature_key: 'mental_rest', raw_value: 1, response_family: 'reward', effective_parameters: { sensitivity: 1.2, curvature: 1 }, formula: 'sensitivity * value ** curvature', utility_rate_contribution: 1.2, temporal_basis: 'rate', response_value: 1.2, utility_contribution: 1.2, exposure_duration_minutes: 60, exposure_duration_hours: 1 }],
      energy_traces: restEnergy ? [{ feature_key: 'mental_rest', energy: 0.192, alpha: 2, modifier: 2, base_contribution: 1.2, adjusted_contribution: 2.4, utility_contribution: 1.2, formula: restFormula }] : [],
      need_traces: [], aftereffect_traces: [], graph: { nodes: [], edges: [] },
    }],
  };
}

describe('Mental rest energy reward presentation', () => {
  it('includes resource and energy columns for engine 8 comparisons', () => {
    render(<Ranking evaluation={savedEvaluation('8')} onInspect={vi.fn()} />);
    expect(screen.getByRole('columnheader', { name: 'One-time' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Energy' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Base utility' })).toBeInTheDocument();
    expect(screen.queryByText(/Legacy calculation/)).not.toBeInTheDocument();
    expect(screen.getByText(/Your state is never updated automatically/)).toBeInTheDocument();
  });

  it('shows the engine 8 rest adjustment separately from its base feature contribution', () => {
    render(<EvaluationPage evaluation={savedEvaluation('8')} ontology={ontology} />);
    expect(screen.getByText('Energy utility').parentElement).toHaveTextContent('+1.2');
    fireEvent.click(screen.getByRole('button', { name: 'Feature, need, energy & aftereffect traces' }));
    const energySection = screen.getByRole('heading', { name: 'Energy contributions' }).closest('section')!;
    expect(energySection).toHaveTextContent('effort costs and mental rest rewards');
    const restRow = within(energySection).getByText('Mental rest').closest('tr')!;
    expect(restRow).toHaveTextContent(restFormula);
    expect(within(restRow).getAllByRole('cell').slice(1).map(cell => cell.textContent)).toEqual(['0.192', '2', '2', '+1.2', '+2.4', '+1.2']);
    const featureSection = screen.getByRole('heading', { name: /Feature contributions/ }).closest('section')!;
    expect(within(featureSection).getByRole('cell', { name: '+1.2' })).toBeInTheDocument();
    expect(within(featureSection).queryByText('+2.4')).not.toBeInTheDocument();
  });

  it('retains engine 7 effort-only explanations without inventing a rest adjustment', () => {
    render(<EvaluationPage evaluation={savedEvaluation('7')} ontology={ontology} />);
    fireEvent.click(screen.getByRole('button', { name: 'Feature, need, energy & aftereffect traces' }));
    const energySection = screen.getByRole('heading', { name: 'Energy contributions' }).closest('section')!;
    expect(energySection).toHaveTextContent('adjusted effort contribution minus base effort contribution');
    expect(energySection).not.toHaveTextContent('mental rest rewards');
    expect(within(energySection).queryByText('Mental rest')).not.toBeInTheDocument();
    expect(screen.queryByText(/Legacy calculation/)).not.toBeInTheDocument();
  });

  it('explains the shared mental alpha and sends current energy to the backend curve preview', async () => {
    const preview = vi.spyOn(api, 'preview').mockResolvedValue({ features: {}, aftereffects: {} });
    render(<ModelEditor personId={version.person_id} initial={version} ontology={ontology} state={state} horizon={24} onVersionSaved={vi.fn()} />);
    expect(screen.getByLabelText('Mental effort & rest response strength (alpha)')).toBeInTheDocument();
    expect(screen.getByText('mental rest modifier = clip(1 + alpha · (0.7 − mental energy), 1, 2)')).toBeInTheDocument();
    expect(screen.getByText(/This curve includes the current mental-energy modifier/)).toHaveTextContent('The persistent relief aftereffect is separate');
    await waitFor(() => expect(preview).toHaveBeenCalledOnce());
    expect(preview.mock.calls[0][0]).toEqual(expect.objectContaining({ transient: model.transient, features: model.features }));
    expect(preview.mock.calls[0][1]).toEqual(state);
  });
});
