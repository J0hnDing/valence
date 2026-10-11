import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { ActionEditor, actionValid } from '../Actions';
import { App } from '../App';
import { ComparePage, Ranking } from '../Compare';
import { currentStateValid, defaultHomeostasis, homeostasisValid } from '../homeostasis';
import { ModelEditor, modelValid } from '../PersonModel';
import { ComputationGraph, output } from '../Graph';
import { EvaluationPage } from '../Evaluation';
import { HistoryPage } from '../History';
import { displayJson, number, NumericControl, today } from '../components';
import fixtures from './fixtures.json';
import type { Action, Evaluation, Feature, Model, ModelVersion, Person, Preview, State, TraceGraph, NeedKey, HistoricalNeedParameters } from '../types';

vi.mock('recharts', () => ({ ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, CartesianGrid: () => null, Line: () => null, XAxis: () => null, YAxis: () => null, Tooltip: () => null }));
vi.mock('@xyflow/react', () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useReactFlow: () => ({ fitView: vi.fn(), setCenter: vi.fn() }),
  ReactFlow: ({ nodes, onNodeClick, children }: { nodes: { id: string; data: { trace: { label: string; value: number } } }[]; onNodeClick: (event: unknown, node: unknown) => void; children: React.ReactNode }) => <div>{nodes.map(node => <button key={node.id} onClick={() => onNodeClick({}, node)}>{node.data.trace.label}: {node.data.trace.value}</button>)}{children}</div>,
  Background: () => null, Controls: () => null, MiniMap: () => null, Handle: () => null, Position: { Left: 'left', Right: 'right' },
}));

const ontology = fixtures.ontology as Feature[];
const model: Model = { ...fixtures.model as Model, homeostasis: defaultHomeostasis() };
const action = { ...fixtures.action, id: 'action-one', title: 'Study ML', duration_minutes: 120 } as Action;
const second = { ...action, id: 'action-two', title: 'Play tennis', duration_minutes: 90 };
const person: Person = { id: 'person-one', name: 'DEMO Person', description: 'Engineering demonstration', created_at: '2026-10-06T12:00:00Z', updated_at: '2026-10-06T12:00:00Z' };
const state: State = { mental_energy: 0.5, physical_energy: 0.5, acute_stress: 0, date: '2026-10-06', notes: '' };
const version: ModelVersion = { id: 'model-one', person_id: person.id, version: 1, model, created_at: person.created_at };
const graph: TraceGraph = {
  nodes: [
    { id: 'raw', label: 'Learning input', kind: 'input', value: 0.7, definition: 'Caller encoded learning', inputs: {}, parameters: {}, formula: 'value', note: 'Read the paper' },
    { id: 'response', label: 'Learning response', kind: 'response', value: 0.83, definition: 'Backend-owned feature response', inputs: { raw: 0.7 }, parameters: { reward_sensitivity: 1.2 }, formula: 'reward_sensitivity * x^curvature' },
    { id: 'total', label: 'Total utility', kind: 'aggregate', value: 6.82, definition: 'Integrated utility', inputs: { during: 2, aftereffects: 4.82 }, parameters: {}, formula: 'during + aftereffects' },
  ], edges: [{ source: 'raw', target: 'response' }, { source: 'response', target: 'total' }],
};
const evaluation: Evaluation = { id: 'evaluation-one', person_id: person.id, person_name: person.name, model_version_id: version.id, model_version: 1, model_snapshot: model, state, horizon_hours: 168, created_at: person.created_at, results: [
  { action_id: action.id, action_snapshot: action, rank: 1, during_rate: 1, during_utility: 2, aftereffect_utility: 4.82, total_utility: 6.82, utility_per_action_hour: 3.41, feature_traces: [{ feature_key: 'learning_curiosity', raw_value: 0.7, response_family: 'reward', effective_parameters: { reward_sensitivity: 1.2, curvature: 1 }, formula: 'reward_sensitivity * x^curvature', utility_rate_contribution: 0.83 }], aftereffect_traces: [{ name: 'inspiration', trigger: 0.5, sensitivity: 0.3, half_life_hours: 8, sign: 1, initial_amplitude: 0.15, integrated_utility: 4.82, formula: 'A * half_life_hours / ln(2)' }], graph },
  { action_id: second.id, action_snapshot: second, rank: 2, during_rate: -1, during_utility: -1.5, aftereffect_utility: 1, total_utility: -0.5, utility_per_action_hour: -0.33333, feature_traces: [], aftereffect_traces: [], graph },
] };
const preview: Preview = { features: Object.fromEntries(ontology.map(feature => [feature.key, { points: [{ x: 0, y: 0 }, { x: 1, y: 1 }], preferred_exposure: feature.response_family === 'reward_overload' ? 0.375 : null }])), aftereffects: Object.fromEntries(Object.keys(model.aftereffects).map(name => [name, { points: [{ x: 0, y: 0.3 }, { x: 168, y: 0 }] }])) };

function mockAppData(people: Person[] = [person], savedVersions: ModelVersion[] = [version]) {
  vi.spyOn(api, 'ontology').mockResolvedValue({ features: ontology });
  vi.spyOn(api, 'persons').mockResolvedValue(people);
  vi.spyOn(api, 'actions').mockResolvedValue([action]);
  vi.spyOn(api, 'state').mockResolvedValue({ ...state, date: today() });
  vi.spyOn(api, 'modelVersions').mockResolvedValue(savedVersions);
  vi.spyOn(api, 'preview').mockResolvedValue(preview);
}

describe('Three-decimal numbers throughout the UI', () => {
  it('rounds both signs and carry boundaries without padding integers or showing signed zero', () => {
    expect(number(1.2345)).toBe('1.235');
    expect(number(-1.2345)).toBe('-1.235');
    expect(number(9.9999)).toBe('10');
    expect(number(2, true)).toBe('+2');
    expect(number(0.0004, true)).toBe('0');
    expect(number(-0.0004, true)).toBe('0');
    expect(number(null)).toBe('—');
  });

  it('rounds numeric fields and slider edits while leaving untouched source values exact', () => {
    const onChange = vi.fn();
    const props = { name: 'Precision', value: 0.123456, min: 0, max: 1, slider: true, onChange };
    const { rerender } = render(<NumericControl {...props} />);
    const input = screen.getByRole('spinbutton', { name: 'Precision' });
    expect(input).toHaveValue(0.123);
    expect(input).toHaveAttribute('step', '0.001');
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: '0.98765' } });
    expect(onChange).toHaveBeenLastCalledWith(0.988);
    rerender(<NumericControl {...props} value={0.988} />);
    expect(input).toHaveValue(0.988);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0.45678' } });
    expect(onChange).toHaveBeenLastCalledWith(0.457);
    fireEvent.change(input, { target: { value: '' } });
    expect(onChange).toHaveBeenLastCalledWith(NaN);
    rerender(<NumericControl {...props} value={NaN} />);
    expect(input).toHaveValue(null);
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(props.value).toBe(0.123456);
  });

  it('rounds nested trace and snapshot displays without modifying numbers or text in the source', () => {
    const source = { rate: 1.234567, nested: [-0.987654, { note: 'Version 1.234567', value: 9.9999 }] };
    const original = structuredClone(source);
    expect(JSON.parse(displayJson(source))).toEqual({ rate: 1.235, nested: [-0.988, { note: 'Version 1.234567', value: 10 }] });
    expect(output(source)).toBe(displayJson(source));
    expect(source).toEqual(original);
  });

  it('rounds comparison durations, horizons, and evaluation model snapshots', () => {
    const exact = structuredClone(evaluation);
    exact.horizon_hours = 12.345678;
    exact.results[0].action_snapshot.duration_minutes = 45.678912;
    exact.model_snapshot.transient.low_mental_energy_cognitive_multiplier = 1.234567;
    const { unmount } = render(<Ranking evaluation={exact} onInspect={vi.fn()} />);
    expect(screen.getByText(/12.346 h aftereffect horizon/)).toBeInTheDocument();
    expect(screen.getByText('45.679 min')).toBeInTheDocument();
    expect(screen.getByText('-0.333')).toBeInTheDocument();
    unmount();
    const { container } = render(<EvaluationPage evaluation={exact} ontology={ontology} />);
    expect(screen.getByText(/12.346 h horizon/)).toBeInTheDocument();
    expect(container.querySelector('pre')).toHaveTextContent('"low_mental_energy_cognitive_multiplier": 1.235');
    expect(container.querySelector('pre')).not.toHaveTextContent('1.234567');
    expect(exact.model_snapshot.transient.low_mental_energy_cognitive_multiplier).toBe(1.234567);
  });
});

describe('Person Model management and version browsing', () => {
  it('keeps the person when deletion is cancelled or fails', async () => {
    mockAppData();
    const remove = vi.spyOn(api, 'deletePerson').mockRejectedValue(new Error('SQLite is busy'));
    render(<App />);
    await screen.findByLabelText('Person');
    fireEvent.click(screen.getByRole('button', { name: 'Person Model' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete person' }));
    expect(screen.getByRole('group', { name: 'Confirm person deletion' })).toHaveTextContent('Saved evaluations and their snapshots remain in History.');
    expect(remove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel deletion' }));
    expect(screen.queryByRole('group', { name: 'Confirm person deletion' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Delete person' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete person' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not delete person: SQLite is busy');
    expect(screen.getByLabelText('Person')).toHaveValue(person.id);
    expect(screen.getByRole('button', { name: 'Confirm delete person' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Compare' }));
    expect(screen.getByRole('option', { name: person.name })).toBeInTheDocument();
  });

  it('deletes the selected person and switches to the remaining person and model', async () => {
    const other = { ...person, id: 'person-two', name: 'Remaining Person' };
    const otherVersion = { ...version, id: 'model-two', person_id: other.id };
    mockAppData([person, other]);
    vi.mocked(api.modelVersions).mockImplementation(async id => id === other.id ? [otherVersion] : [version]);
    let finish!: () => void;
    const remove = vi.spyOn(api, 'deletePerson').mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('Model version')).toHaveValue(version.id));
    fireEvent.click(screen.getByRole('button', { name: 'Person Model' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete person' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete person' }));
    expect(remove).toHaveBeenCalledWith(person.id);
    expect(screen.getByLabelText('Person')).toBeDisabled();
    expect(screen.getByLabelText('Competence / mastery · Positive sensitivity')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Deleting…' })).toBeDisabled();
    await act(async () => finish());
    await waitFor(() => expect(screen.getByLabelText('Person')).toHaveValue(other.id));
    await waitFor(() => expect(screen.getByLabelText('Model version')).toHaveValue(otherVersion.id));
    expect(screen.queryByRole('option', { name: person.name })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Compare' }));
    expect(screen.getByLabelText('Person')).toHaveValue(other.id);
    expect(screen.getByLabelText('Model version')).toHaveValue(otherVersion.id);
    expect(screen.queryByRole('option', { name: person.name })).not.toBeInTheDocument();
  });

  it('opens creation after deleting the last person and clears Compare selection', async () => {
    mockAppData();
    vi.spyOn(api, 'deletePerson').mockResolvedValue(undefined);
    render(<App />);
    await screen.findByLabelText('Person');
    fireEvent.click(screen.getByRole('button', { name: 'Person Model' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete person' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete person' }));
    expect(await screen.findByRole('heading', { name: 'Create person' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: /Response parameters/ })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Person')).toHaveValue('');
    fireEvent.click(screen.getByRole('button', { name: 'Compare' }));
    expect(screen.queryByRole('option', { name: person.name })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Model version')).not.toBeInTheDocument();
  });

  it('creates and edits a person in Person Model, with no creation form in Compare', async () => {
    mockAppData([]);
    const created = { ...person, name: 'Ada', description: 'Manual model' };
    const edited = { ...created, name: 'Ada revised', description: 'Updated description' };
    const create = vi.spyOn(api, 'createPerson').mockResolvedValue(created);
    const update = vi.spyOn(api, 'updatePerson').mockResolvedValue(edited);
    render(<App />);
    await screen.findByRole('button', { name: 'Manage person & model →' });
    expect(screen.queryByRole('button', { name: '+ Create person' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Name')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Manage person & model →' }));
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Ada' } });
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'Manual model' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create person' }));
    await waitFor(() => expect(create).toHaveBeenCalledWith('Ada', 'Manual model'));
    await screen.findByRole('heading', { name: /Response parameters/ });
    expect(screen.getByLabelText('Person')).toHaveValue(created.id);
    fireEvent.click(screen.getByRole('button', { name: 'Edit person' }));
    expect(screen.getByLabelText('Name')).toHaveValue('Ada');
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Ada revised' } });
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'Updated description' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save person' }));
    await waitFor(() => expect(update).toHaveBeenCalledWith(created.id, 'Ada revised', 'Updated description'));
    expect(await screen.findByText('Person details saved.')).toBeVisible();
    expect(screen.getByRole('option', { name: 'Ada revised' })).toBeInTheDocument();
    expect(screen.getByLabelText('Model version')).toHaveValue(version.id);
    fireEvent.click(screen.getByRole('button', { name: 'Compare' }));
    expect(screen.getByRole('option', { name: 'Ada revised' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Name')).not.toBeInTheDocument();
  }, 10000);

  it('inspects an older model, evaluates it explicitly, and saves its edits as a new version', async () => {
    const laterModel = structuredClone(model);
    laterModel.features.competence_mastery.positive_sensitivity = 3;
    laterModel.aftereffects.fatigue.half_life_hours = 9;
    const later = { ...version, id: 'model-two', version: 2, model: laterModel };
    const editedModel = structuredClone(model);
    editedModel.features.competence_mastery.positive_sensitivity = 2.5;
    const saved = { ...version, id: 'model-three', version: 3, model: editedModel };
    mockAppData([person], [later, version]);
    const evaluate = vi.spyOn(api, 'evaluate').mockResolvedValue(evaluation);
    const save = vi.spyOn(api, 'saveModel').mockResolvedValue(saved);
    render(<App />);
    await screen.findByLabelText('Model version');
    await waitFor(() => expect(screen.getByLabelText('Model version')).toHaveValue(later.id));
    fireEvent.click(screen.getByRole('button', { name: 'Person Model' }));
    expect(screen.getByLabelText('Competence / mastery · Positive sensitivity')).toHaveValue(3);
    expect(screen.getByLabelText('Fatigue half-life (hours)')).toHaveValue(9);
    fireEvent.change(screen.getByLabelText('Model version'), { target: { value: version.id } });
    expect(screen.getByLabelText('Competence / mastery · Positive sensitivity')).toHaveValue(1);
    expect(screen.getByLabelText('Fatigue half-life (hours)')).toHaveValue(4);
    await waitFor(() => expect(api.preview).toHaveBeenLastCalledWith(model, expect.any(Object), 168));
    fireEvent.click(screen.getByRole('button', { name: 'Compare' }));
    expect(screen.getByLabelText('Model version')).toHaveValue(version.id);
    fireEvent.click(screen.getByRole('button', { name: 'Select all' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Evaluate 1 action →' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate 1 action →' }));
    await waitFor(() => expect(evaluate).toHaveBeenCalledWith(person.id, [action.id], expect.any(Object), 168, version.id));
    fireEvent.click(screen.getByRole('button', { name: 'Person Model' }));
    fireEvent.change(screen.getByLabelText('Competence / mastery · Positive sensitivity'), { target: { value: '2.5' } });
    fireEvent.click(screen.getAllByRole('button', { name: 'Save new version' })[0]);
    await waitFor(() => expect(save).toHaveBeenCalledWith(person.id, editedModel));
    await waitFor(() => expect(screen.getByLabelText('Model version')).toHaveValue(saved.id));
    expect(screen.getByRole('option', { name: /^v3 · Latest/ })).toBeInTheDocument();
    expect(screen.getByText('Saved model version 3. Previous versions remain available.')).toBeVisible();
    fireEvent.change(screen.getByLabelText('Model version'), { target: { value: version.id } });
    expect(screen.getByLabelText('Competence / mastery · Positive sensitivity')).toHaveValue(1);
    expect(model.features.competence_mastery.positive_sensitivity).toBe(1);
  }, 10000);

  it('ignores another person’s delayed version list after switching people', async () => {
    const other = { ...person, id: 'person-two', name: 'Second Person' };
    mockAppData([person, other]);
    let resolveFirst!: (value: ModelVersion[]) => void; let resolveSecond!: (value: ModelVersion[]) => void;
    vi.mocked(api.modelVersions).mockImplementation(id => new Promise(resolve => { if (id === person.id) resolveFirst = resolve; else resolveSecond = resolve; }));
    render(<App />);
    await screen.findByLabelText('Person');
    await waitFor(() => expect(resolveFirst).toBeDefined());
    fireEvent.change(screen.getByLabelText('Person'), { target: { value: other.id } });
    await waitFor(() => expect(resolveSecond).toBeDefined());
    const otherVersion = { ...version, person_id: other.id, id: 'other-model' };
    await act(async () => resolveSecond([otherVersion]));
    expect(screen.getByLabelText('Model version')).toHaveValue(otherVersion.id);
    await act(async () => resolveFirst([version]));
    expect(screen.getByLabelText('Model version')).toHaveValue(otherVersion.id);
    expect(screen.queryByRole('option', { name: person.name })).not.toBeNull();
  });
});

describe('action feature entry', () => {
  it('saves all 19 explicit values and notes, rejecting out-of-range feature input', async () => {
    const save = vi.spyOn(api, 'saveAction').mockResolvedValue(action);
    const onSaved = vi.fn(); render(<ActionEditor ontology={ontology} onSaved={onSaved} />);
    expect(screen.getAllByRole('slider')).toHaveLength(19);
    expect(screen.queryByLabelText('Preference alignment value')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Study ML' } });
    fireEvent.change(screen.getByLabelText('Net money cost (currency units)'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Knowledge / learning gained value'), { target: { value: '1.5' } });
    expect(screen.getByText('Use a value from 0 to 1.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Create action' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Knowledge / learning gained value'), { target: { value: '0.7' } });
    fireEvent.change(screen.getByLabelText('Duration (minutes)'), { target: { value: '0' } });
    fireEvent.change(screen.getAllByLabelText('Caller note')[0], { target: { value: 'Caller provenance' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create action' }));
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    const submitted = save.mock.calls[0][0];
    expect(Object.keys(submitted.features)).toHaveLength(19);
    expect(Object.keys(submitted.features)).toEqual(ontology.map(feature => feature.key));
    expect(submitted.features).not.toHaveProperty('preference_alignment');
    expect(submitted.features.learning_gain).toBe(0.7);
    expect(submitted.duration_minutes).toBe(0);
    expect(submitted.feature_notes?.mental_effort).toBe('Caller provenance');
    expect(onSaved).toHaveBeenCalledWith(action);
  });
  it('blocks non-finite or negative duration and retains existing encoded data when editing', () => {
    render(<ActionEditor ontology={ontology} action={action} onSaved={vi.fn()} />);
    const duration = screen.getByLabelText('Duration (minutes)');
    fireEvent.change(duration, { target: { value: '-1' } });
    expect(screen.getAllByRole('button', { name: 'Save action' })[0]).toBeDisabled();
    fireEvent.change(duration, { target: { value: '' } });
    expect(screen.getByText('Enter a finite number.')).toBeVisible();
    expect(screen.getByLabelText('Knowledge / learning gained value')).toHaveValue(action.features.learning_gain);
  });
  it('records effort and bodily pleasure independently, with optional exposure durations', async () => {
    const save = vi.spyOn(api, 'saveAction').mockResolvedValue(action);
    render(<ActionEditor ontology={ontology} action={action} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Physical effort value'), { target: { value: '0.8' } });
    fireEvent.change(screen.getByLabelText('Physical pleasure / comfort value'), { target: { value: '0.7' } });
    const exposure = screen.getByLabelText('Physical effort · Exposure duration (minutes)');
    expect(exposure).toHaveValue(null);
    expect(exposure).toHaveAttribute('aria-invalid', 'false');
    expect(screen.queryByLabelText('Knowledge / learning gained · Exposure duration (minutes)')).not.toBeInTheDocument();
    fireEvent.change(exposure, { target: { value: '120.001' } });
    expect(screen.getAllByRole('button', { name: 'Save action' })[0]).toBeDisabled();
    fireEvent.change(exposure, { target: { value: '30.12345' } });
    expect(exposure).toHaveValue(30.123);
    fireEvent.change(screen.getByLabelText('Mental rest / relief · Exposure duration (minutes)'), { target: { value: '0' } });
    fireEvent.click(screen.getAllByRole('button', { name: 'Save action' })[0]);
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(save.mock.calls[0][0].features).toMatchObject({ physical_effort: 0.8, physical_pleasure: 0.7 });
    expect(save.mock.calls[0][0].feature_duration_minutes).toEqual({ physical_effort: 30.123, mental_rest: 0 });
  });
  it('preserves exposure overrides on edit and clears an override back to the whole action', async () => {
    const save = vi.spyOn(api, 'saveAction').mockResolvedValue(action);
    render(<ActionEditor ontology={ontology} action={{ ...action, feature_duration_minutes: { mental_effort: 20 } }} onSaved={vi.fn()} />);
    const exposure = screen.getByLabelText('Mental effort · Exposure duration (minutes)');
    expect(exposure).toHaveValue(20);
    fireEvent.change(screen.getByLabelText('Duration (minutes)'), { target: { value: '10' } });
    expect(screen.getAllByRole('button', { name: 'Save action' })[0]).toBeDisabled();
    fireEvent.change(exposure, { target: { value: '' } });
    fireEvent.click(screen.getAllByRole('button', { name: 'Save action' })[0]);
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(save.mock.calls[0][0].feature_duration_minutes).toEqual({});
  });
  it('rejects duration overrides for outcomes, unknown features, and invalid numbers', () => {
    const input = { ...action, net_money_cost: 0 };
    const invalid: Record<string, number>[] = [{ learning_gain: 10 }, { missing: 10 }, { mental_effort: -1 }, { mental_effort: NaN }, { mental_effort: Infinity }, { mental_effort: 121 }];
    for (const durations of invalid) {
      expect(actionValid({ ...input, feature_duration_minutes: durations }, ontology)).toBe(false);
    }
    expect(actionValid({ ...input, feature_duration_minutes: { mental_effort: 0, physical_pleasure: 120 } }, ontology)).toBe(true);
  });
});

describe('Person Model editing', () => {
  it('persists independent effort, rest, pleasure, structure, and uncertainty responses', async () => {
    vi.spyOn(api, 'preview').mockResolvedValue(preview);
    const save = vi.spyOn(api, 'saveModel').mockResolvedValue(version);
    render(<ModelEditor personId={person.id} initial={version} ontology={ontology} state={state} horizon={168} onVersionSaved={vi.fn()} />);
    const parameters = [
      ['Mental effort · Cost sensitivity', 'mental_effort', 'cost_sensitivity', 2],
      ['Mental rest / relief · Reward sensitivity', 'mental_rest', 'reward_sensitivity', 3],
      ['Physical effort · Cost sensitivity', 'physical_effort', 'cost_sensitivity', 4],
      ['Physical pleasure / comfort · Reward sensitivity', 'physical_pleasure', 'reward_sensitivity', 5],
      ['Structure / planning · Preference sensitivity', 'structure_planning', 'preference_sensitivity', 6],
      ['Outcome uncertainty · Preference sensitivity', 'outcome_uncertainty', 'preference_sensitivity', -7],
    ] as const;
    for (const [name, , , value] of parameters) fireEvent.change(screen.getByLabelText(name), { target: { value: String(value) } });
    fireEvent.click(screen.getAllByRole('button', { name: 'Save new version' })[0]);
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    for (const [, key, parameter, value] of parameters) expect(save.mock.calls[0][1].features[key][parameter]).toBe(value);
  });
  it('exposes all response/transient/effect parameters, validates positive fields and saves a new version', async () => {
    vi.spyOn(api, 'preview').mockResolvedValue(preview);
    const save = vi.spyOn(api, 'saveModel').mockResolvedValue({ ...version, version: 2 });
    const onSaved = vi.fn(); render(<ModelEditor personId={person.id} initial={version} ontology={ontology} state={state} horizon={168} onVersionSaved={onSaved} />);
    const parameterCount = Object.values(model.features).reduce((total, response) => total + Object.keys(response).filter(key => key !== 'family').length, 0)
      + 2 + 16 + Object.keys(model.transient).length + Object.values(model.aftereffects).reduce((total, effect) => total + Object.keys(effect).length, 0);
    expect(screen.getAllByRole('spinbutton')).toHaveLength(parameterCount);
    expect(screen.queryByLabelText('Preference alignment · Positive sensitivity')).not.toBeInTheDocument();
    const curvature = screen.getByLabelText('Competence / mastery · Positive curvature');
    fireEvent.change(curvature, { target: { value: '0' } });
    expect(screen.getAllByRole('button', { name: 'Save new version' })[0]).toBeDisabled();
    expect(screen.getByText('Must be greater than zero.')).toBeVisible();
    fireEvent.change(curvature, { target: { value: '1.5' } });
    fireEvent.change(screen.getByLabelText('Fatigue half-life (hours)'), { target: { value: '6' } });
    fireEvent.change(screen.getByLabelText('Stress negative multiplier'), { target: { value: '0.75' } });
    await waitFor(() => expect(screen.getAllByRole('img')).toHaveLength(ontology.length + Object.keys(model.aftereffects).length));
    expect(screen.getAllByText('0.375')).toHaveLength(2);
    fireEvent.click(screen.getAllByRole('button', { name: 'Save new version' })[0]);
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(save.mock.calls[0][1].features.competence_mastery.positive_curvature).toBe(1.5);
    expect(save.mock.calls[0][1].aftereffects.fatigue.half_life_hours).toBe(6);
    expect(save.mock.calls[0][1].transient.stress_negative_multiplier).toBe(0.75);
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ version: 2 }));
    expect(screen.getByRole('status')).toHaveTextContent('Saved model version 2');
  });
});

describe('comparison results', () => {
  it('submits person, selected candidates, exact transient state and horizon, then renders backend ranking', async () => {
    const evaluate = vi.spyOn(api, 'evaluate').mockResolvedValue(evaluation);
    render(<ComparePage persons={[person]} personId={person.id} onPersonChanged={vi.fn()} onManagePerson={vi.fn()} versions={[version]} selectedVersion={version} onVersionChanged={vi.fn()} modelLoading={false} modelError="" onModelRetry={vi.fn()} actions={[action, second]} state={state} onStateChanged={vi.fn()} stateLoading={false} stateError="" onStateRetry={vi.fn()} horizon={168} onHorizonChanged={vi.fn()} onInspect={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Evaluate 0 actions →' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Select all' }));
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate 2 actions →' }));
    await waitFor(() => expect(evaluate).toHaveBeenCalledWith(person.id, [action.id, second.id], state, 168, version.id));
    expect(await screen.findByRole('heading', { name: 'Comparison result' })).toBeVisible();
    const rows = within(screen.getByRole('table')).getAllByRole('row');
    expect(rows[1]).toHaveTextContent('Study ML'); expect(rows[1]).toHaveTextContent('+6.82');
    expect(rows[2]).toHaveTextContent('Play tennis'); expect(rows[2]).toHaveTextContent('-0.5');
  });
  it('preserves null utility/hour for zero-duration actions instead of deriving a score', () => {
    render(<Ranking evaluation={{ ...evaluation, results: [{ ...evaluation.results[0], action_snapshot: { ...action, duration_minutes: 0 }, utility_per_action_hour: null }] }} onInspect={vi.fn()} />);
    expect(screen.getByText('· zero duration')).toBeVisible();
  });
});

describe('resource costs and one-time outcomes', () => {
  const current: Evaluation = { ...evaluation, engine_version: '3', results: [{ ...evaluation.results[0], one_time_utility: 3, gross_utility: 9.82, time_cost: 4, money_cost: 1, resource_cost: 5, total_utility: 4.82, utility_per_action_hour: 4.41, feature_traces: [{ ...evaluation.results[0].feature_traces[0], temporal_basis: 'one_time', response_value: 0.83, utility_contribution: 0.83, utility_rate_contribution: null }] }] };

  it('requires an explicit finite money amount and submits income as a negative cost', async () => {
    const save = vi.spyOn(api, 'saveAction').mockResolvedValue(action);
    render(<ActionEditor ontology={ontology} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Paid work' } });
    const submit = screen.getByRole('button', { name: 'Create action' });
    expect(submit).toBeDisabled();
    const money = screen.getByLabelText('Net money cost (currency units)');
    fireEvent.change(money, { target: { value: '-25.5' } });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(save.mock.calls[0][0].net_money_cost).toBe(-25.5);
  });

  it('validates and persists both resource coefficients in a new version', async () => {
    vi.spyOn(api, 'preview').mockResolvedValue(preview);
    const save = vi.spyOn(api, 'saveModel').mockResolvedValue(version);
    render(<ModelEditor personId={person.id} initial={version} ontology={ontology} state={state} horizon={168} onVersionSaved={vi.fn()} />);
    const time = screen.getByLabelText('Time value (utility / hour)');
    const money = screen.getByLabelText('Money value (utility / currency unit)');
    fireEvent.change(time, { target: { value: '-1' } });
    expect(screen.getAllByRole('button', { name: 'Save new version' })[0]).toBeDisabled();
    fireEvent.change(time, { target: { value: '2' } });
    fireEvent.change(money, { target: { value: '' } });
    expect(screen.getAllByRole('button', { name: 'Save new version' })[0]).toBeDisabled();
    fireEvent.change(money, { target: { value: '0.5' } });
    fireEvent.click(screen.getAllByRole('button', { name: 'Save new version' })[0]);
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(save.mock.calls[0][1].resources).toEqual({ time_value: 2, money_value: 0.5 });
  });

  it('renders backend resource totals and one-time traces without deriving a new score', () => {
    const { unmount } = render(<Ranking evaluation={current} onInspect={vi.fn()} />);
    expect(screen.getByRole('columnheader', { name: 'One-time' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Time cost' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Money cost' })).toBeVisible();
    expect(screen.getByText('+4.41')).toBeVisible();
    expect(screen.getByText(/excludes time cost/)).toBeVisible();
    unmount();
    render(<EvaluationPage evaluation={current} ontology={ontology} />);
    expect(screen.getByText('Gross utility')).toBeVisible();
    expect(screen.getByText('Resource cost')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Feature & aftereffect traces' }));
    expect(screen.getByText('One-time · utility per action')).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Action utility' })).toBeVisible();
    expect(screen.getAllByText('+0.83')).toHaveLength(2);
  });
  it.each(['4', '5'] as const)('shows resource totals for engine %s', engine => {
    render(<Ranking evaluation={{ ...current, engine_version: engine }} onInspect={vi.fn()} />);
    expect(screen.getByRole('columnheader', { name: 'One-time' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Time cost' })).toBeVisible();
  });
  it('shows the recorded exposure duration of ongoing engine5 responses', () => {
    const result = structuredClone(current);
    result.engine_version = '5';
    result.results[0].feature_traces.push({ feature_key: 'mental_rest', raw_value: 0.5, response_family: 'reward', effective_parameters: { reward_sensitivity: 1, curvature: 1 }, formula: 'reward_sensitivity * x^curvature', temporal_basis: 'rate', response_value: 0.5, utility_rate_contribution: 0.5, utility_contribution: 0.125, exposure_duration_minutes: 15, exposure_duration_hours: 0.25 });
    render(<EvaluationPage evaluation={result} ontology={ontology} />);
    fireEvent.click(screen.getByRole('button', { name: 'Feature & aftereffect traces' }));
    expect(screen.getByText('Exposure: 15 min (0.25 h)')).toBeVisible();
    expect(screen.getByText('+0.125')).toBeVisible();
  });

  it('keeps legacy evaluation labels and recorded duration-based semantics', () => {
    render(<Ranking evaluation={evaluation} onInspect={vi.fn()} />);
    expect(screen.queryByRole('columnheader', { name: 'Time cost' })).not.toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'During' })).toBeVisible();
    expect(screen.getByText(/Legacy calculation: all feature responses were multiplied by duration/)).toBeVisible();
    expect(screen.getByText('+3.41')).toBeVisible();
  });
});

describe('backend computation traces', () => {
  it('renders every graph node value and exposes backend formula, parameters and caller provenance on selection', () => {
    render(<ComputationGraph graph={graph} />);
    expect(screen.getByRole('button', { name: 'Total utility: 6.82' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Learning response: 0.83' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Learning response: 0.83' }));
    const inspector = screen.getByRole('complementary', { name: 'Node inspector' });
    expect(inspector).toHaveTextContent('Backend-owned feature response');
    expect(inspector).toHaveTextContent('reward_sensitivity * x^curvature');
    expect(inspector).toHaveTextContent('1.2'); expect(inspector).toHaveTextContent('0.83');
    fireEvent.change(screen.getByLabelText('Select graph node'), { target: { value: 'raw' } });
    expect(inspector).toHaveTextContent('Read the paper'); expect(inspector).toHaveTextContent('Caller-supplied note');
  });
  it('shows feature and all aftereffect trace fields for an immutable evaluation', () => {
    render(<EvaluationPage evaluation={evaluation} ontology={ontology} />);
    fireEvent.click(screen.getByRole('button', { name: 'Feature & aftereffect traces' }));
    expect(screen.getByText('reward_sensitivity * x^curvature')).toBeVisible();
    expect(screen.getByText('A * half_life_hours / ln(2)')).toBeVisible();
    expect(screen.getByText('Initial amplitude')).toBeVisible();
    expect(screen.getByText('+0.83')).toBeVisible(); expect(screen.getByText('+0.15')).toBeVisible();
  });
});

describe('persistence workflows', () => {
  it('reopens a saved evaluation through the history API', async () => {
    vi.spyOn(api, 'history').mockResolvedValue([{ id: evaluation.id, person_id: person.id, person_name: person.name, model_version: 1, created_at: evaluation.created_at, horizon_hours: 168, action_count: 2, top_action_title: action.title, top_total_utility: 6.82 }]);
    const get = vi.spyOn(api, 'evaluation').mockResolvedValue(evaluation); const open = vi.fn();
    render(<HistoryPage onInspect={open} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open trace →' }));
    await waitFor(() => expect(get).toHaveBeenCalledWith(evaluation.id));
    expect(open).toHaveBeenCalledWith(evaluation);
  });
  it('preserves unsaved transient values when navigating between Compare and Person Model', async () => {
    vi.spyOn(api, 'ontology').mockResolvedValue({ features: ontology }); vi.spyOn(api, 'persons').mockResolvedValue([person]); vi.spyOn(api, 'actions').mockResolvedValue([action]);
    const loadState = vi.spyOn(api, 'state').mockResolvedValue({ ...state, date: today() });
    vi.spyOn(api, 'model').mockResolvedValue(version); vi.spyOn(api, 'preview').mockResolvedValue(preview);
    vi.spyOn(api, 'modelVersions').mockResolvedValue([version]);
    render(<App />);
    await waitFor(() => expect(loadState).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByLabelText('mental energy')).not.toBeDisabled());
    fireEvent.change(screen.getByLabelText('mental energy'), { target: { value: '0.9' } });
    fireEvent.click(screen.getByRole('button', { name: 'Person Model' }));
    await screen.findByRole('heading', { name: /Response parameters/ });
    fireEvent.click(screen.getByRole('button', { name: 'Compare' }));
    expect(screen.getByLabelText('mental energy')).toHaveValue(0.9);
    expect(loadState).toHaveBeenCalledTimes(1);
  });
  it('ignores a previous person’s delayed daily-state response after selection changes', async () => {
    const otherPerson = { ...person, id: 'person-two', name: 'Second Person' };
    vi.spyOn(api, 'ontology').mockResolvedValue({ features: ontology }); vi.spyOn(api, 'persons').mockResolvedValue([person, otherPerson]); vi.spyOn(api, 'actions').mockResolvedValue([action]);
    vi.spyOn(api, 'modelVersions').mockImplementation(async id => [{ ...version, id: `model-${id}`, person_id: id }]);
    let resolveFirst!: (value: State) => void; let resolveSecond!: (value: State) => void;
    vi.spyOn(api, 'state').mockImplementation(id => new Promise(resolve => { if (id === person.id) resolveFirst = resolve; else resolveSecond = resolve; }));
    render(<App />);
    await screen.findByLabelText('Person');
    await waitFor(() => expect(resolveFirst).toBeDefined());
    fireEvent.change(screen.getByLabelText('Person'), { target: { value: otherPerson.id } });
    await waitFor(() => expect(resolveSecond).toBeDefined());
    await act(async () => { resolveSecond({ ...state, date: today(), mental_energy: 0.7 }); });
    expect(screen.getByLabelText('mental energy')).toHaveValue(0.7);
    await act(async () => { resolveFirst({ ...state, date: today(), mental_energy: 0.1 }); });
    expect(screen.getByLabelText('mental energy')).toHaveValue(0.7);
  });
  it('keeps failed API mutations visible without claiming a saved action', async () => {
    vi.spyOn(api, 'saveAction').mockRejectedValue(new Error('SQLite is busy')); const saved = vi.fn();
    render(<ActionEditor ontology={ontology} action={action} onSaved={saved} />);
    expect(screen.getAllByRole('button', { name: 'Save action' })[0]).toBeEnabled();
    fireEvent.click(screen.getAllByRole('button', { name: 'Save action' })[0]);
    expect(await screen.findByRole('alert')).toHaveTextContent('SQLite is busy');
    expect(saved).not.toHaveBeenCalled();
    await act(async () => {});
  });
});


describe('dynamic needs and optional current state', () => {
  it('validates known values and treats missing energy and needs as unknown', () => {
    expect(currentStateValid({ acute_stress: 0, date: state.date })).toBe(true);
    expect(currentStateValid({ ...state, mental_energy: null, need_satisfaction: { physical_activity: 0 } })).toBe(true);
    for (const bad of [-0.001, 1.001, NaN, Infinity]) {
      expect(currentStateValid({ ...state, mental_energy: bad })).toBe(false);
      expect(currentStateValid({ ...state, need_satisfaction: { physical_activity: bad } })).toBe(false);
    }
    expect(currentStateValid({ ...state, need_satisfaction: { unknown: 0.5 } } as State)).toBe(false);
    const params = defaultHomeostasis();
    expect(homeostasisValid(params)).toBe(true);
    for (const [key, bad] of [['lower', 0], ['upper', 1], ['sensitivity', 64.001]] as const) {
      expect(homeostasisValid({ ...params, needs: { ...params.needs, physical_activity: { ...params.needs.physical_activity, [key]: bad } } })).toBe(false);
    }
    expect(homeostasisValid({ ...params, needs: { ...params.needs, physical_activity: { ...params.needs.physical_activity, lower: 0.9 } } })).toBe(false);
    expect(homeostasisValid({ ...params, mental_effort_weight: NaN })).toBe(false);
    const obsolete = { ...params, needs: { ...params.needs, physical_activity: { ...params.needs.physical_activity, rate: 0.25 } } };
    expect(homeostasisValid(obsolete)).toBe(false);
    expect(modelValid({ ...model, homeostasis: obsolete })).toBe(false);
    expect(modelValid({ ...model, transient: { ...model.transient, low_mental_energy_cognitive_multiplier: 65 } })).toBe(false);
  });

  it('requires an explicit value when enabling state, allows unknowns, saves manually, and leaves state unchanged after evaluation', async () => {
    const initial: State = { acute_stress: 0, date: state.date, mental_energy: null, physical_energy: null, need_satisfaction: {} };
    let current = initial;
    const changed = vi.fn((value: State) => { current = value; });
    const props = { persons: [person], personId: person.id, onPersonChanged: vi.fn(), onManagePerson: vi.fn(), versions: [version], selectedVersion: version, onVersionChanged: vi.fn(), modelLoading: false, modelError: '', onModelRetry: vi.fn(), actions: [action], state: initial, onStateChanged: changed, stateLoading: false, stateError: '', onStateRetry: vi.fn(), horizon: 168, onHorizonChanged: vi.fn(), onInspect: vi.fn() };
    const evaluate = vi.spyOn(api, 'evaluate').mockResolvedValue(evaluation);
    const save = vi.spyOn(api, 'saveState').mockResolvedValue(initial);
    const { rerender } = render(<ComparePage {...props} />);
    expect(screen.getByLabelText('Mental energy availability')).toHaveValue('unknown');
    expect(screen.queryByLabelText('mental energy')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Select all' }));
    expect(screen.getByRole('button', { name: 'Evaluate 1 action →' })).toBeEnabled();
    fireEvent.change(screen.getByLabelText('Mental energy availability'), { target: { value: 'provided' } });
    rerender(<ComparePage {...props} state={current} />);
    expect(screen.getByLabelText('mental energy')).toHaveValue(null);
    expect(screen.getByRole('button', { name: 'Evaluate 1 action →' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('mental energy'), { target: { value: '0.12345' } });
    rerender(<ComparePage {...props} state={current} />);
    expect(screen.getByLabelText('mental energy')).toHaveValue(0.123);
    fireEvent.change(screen.getByLabelText('Physical activity availability'), { target: { value: 'provided' } });
    rerender(<ComparePage {...props} state={current} />);
    fireEvent.change(screen.getByLabelText('Physical activity satisfaction'), { target: { value: '0.7' } });
    rerender(<ComparePage {...props} state={current} />);
    expect(screen.getByText(/Preferred band: 0.6–0.8 · Optimal/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Save state' }));
    await waitFor(() => expect(save).toHaveBeenCalledWith(person.id, current));
    await screen.findByText(`Daily state saved for ${state.date}.`);
    const callsBefore = changed.mock.calls.length;
    fireEvent.click(screen.getByRole('button', { name: 'Evaluate 1 action →' }));
    await waitFor(() => expect(evaluate).toHaveBeenCalledWith(person.id, [action.id], current, 168, version.id));
    await screen.findByRole('heading', { name: 'Comparison result' });
    expect(changed).toHaveBeenCalledTimes(callsBefore);
    expect(save).toHaveBeenCalledOnce();
    fireEvent.change(screen.getByLabelText('Physical activity availability'), { target: { value: 'unknown' } });
    expect(current.need_satisfaction).toEqual({});
    fireEvent.change(screen.getByLabelText('Mental energy availability'), { target: { value: 'unknown' } });
    expect(current.mental_energy).toBeNull();
  });

  it('defaults legacy model parameters and validates bounds before saving the edited model', async () => {
    vi.spyOn(api, 'preview').mockResolvedValue(preview);
    const save = vi.spyOn(api, 'saveModel').mockResolvedValue(version);
    render(<ModelEditor personId={person.id} initial={{ ...version, model: fixtures.model as Model }} ontology={ontology} state={{ ...state, mental_energy: null }} horizon={168} onVersionSaved={vi.fn()} />);
    expect(screen.getByLabelText('Physical activity · Lower')).toHaveValue(0.6);
    expect(screen.queryByLabelText('Physical activity · Rate')).not.toBeInTheDocument();
    expect(screen.queryByText(/predicted =/)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Mental stimulation · Mental effort weight')).toHaveValue(0.4);
    fireEvent.change(screen.getByLabelText('Physical activity · Lower'), { target: { value: '0.9' } });
    expect(screen.getAllByRole('button', { name: 'Save new version' })[0]).toBeDisabled();
    expect(screen.getByText('Use 0 < lower ≤ upper < 1.')).toBeVisible();
    fireEvent.change(screen.getByLabelText('Physical activity · Lower'), { target: { value: '0.5' } });
    fireEvent.change(screen.getByLabelText('Mental stimulation · Mental effort weight'), { target: { value: '0.3' } });
    expect(screen.getByText(/Learning gain weight: 0.7/)).toBeVisible();
    fireEvent.click(screen.getAllByRole('button', { name: 'Save new version' })[0]);
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(save.mock.calls[0][1].homeostasis).toEqual({ ...defaultHomeostasis(), mental_effort_weight: 0.3, needs: { ...defaultHomeostasis().needs, physical_activity: { lower: 0.5, upper: 0.8, sensitivity: 1 } } });
    expect((fixtures.model as Model).homeostasis).toBeUndefined();
  });

  it('shows recorded engine7 current-state pressure and action scoring without predicted state', () => {
    const current: Evaluation = { ...evaluation, engine_version: '7', state: { ...state, mental_energy: null, need_satisfaction: { physical_activity: 0.3 } }, results: [{ ...evaluation.results[0], base_utility: 6.82, needs_utility: 0.321987, energy_utility: -0.2, gross_utility: 6.941987, total_utility: 6.941987, resource_cost: 0, one_time_utility: 0, time_cost: 0, money_cost: 0, need_traces: [{ need_key: 'physical_activity', available: true, current_satisfaction: 0.3, feature_value: 0.6, parameters: defaultHomeostasis().needs.physical_activity, deprivation: 0.5, overload: 0, pressure: 0.25, utility_contribution: 0.321987, formula: 'saved need formula' }, { need_key: 'social_interaction', available: false, current_satisfaction: null, feature_value: 0, parameters: defaultHomeostasis().needs.social_interaction, deprivation: null, overload: null, pressure: 0, utility_contribution: 0, formula: 'unknown contributes zero' }], energy_traces: [{ feature_key: 'mental_effort', energy: null, alpha: 1, modifier: 1, base_contribution: -1, adjusted_contribution: -1, utility_contribution: 0, formula: 'saved energy formula' }] }] };
    const { unmount } = render(<Ranking evaluation={current} onInspect={vi.fn()} />);
    expect(screen.getByRole('columnheader', { name: 'Base utility' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Needs' })).toBeVisible();
    expect(screen.getByText('+0.322')).toBeVisible();
    unmount();
    const detail = render(<EvaluationPage evaluation={current} ontology={ontology} />);
    expect(screen.getByText('Needs utility')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Feature, need, energy & aftereffect traces' }));
    expect(screen.getByRole('heading', { name: 'Need contributions' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Energy contributions' })).toBeVisible();
    expect(screen.getByText('saved need formula')).toBeVisible();
    expect(screen.getByText('saved energy formula')).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Pressure' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Action-feature value' })).toBeVisible();
    expect(screen.queryByRole('columnheader', { name: 'Predicted satisfaction' })).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Impact' })).not.toBeInTheDocument();
    expect(screen.getAllByText('Unknown').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Need utility = current-state pressure/)).toBeVisible();
    detail.unmount();
    render(<EvaluationPage evaluation={{ ...evaluation, engine_version: '5' }} ontology={ontology} />);
    fireEvent.click(screen.getByRole('button', { name: 'Feature & aftereffect traces' }));
    expect(screen.queryByRole('heading', { name: 'Need contributions' })).not.toBeInTheDocument();
    expect(screen.queryByText('Needs utility')).not.toBeInTheDocument();
  });

  it('preserves historical engine6 prediction traces and model snapshots as read-only recorded data', () => {
    const historical: Evaluation = { ...evaluation, engine_version: '6', model_snapshot: { ...model, homeostasis: { ...defaultHomeostasis(), needs: Object.fromEntries(Object.entries(defaultHomeostasis().needs).map(([key, params]) => [key, { ...params, rate: 0.25 }])) as Record<NeedKey, HistoricalNeedParameters> } }, results: [{ ...evaluation.results[0], base_utility: 6.82, needs_utility: 0.25, energy_utility: 0, need_traces: [{ need_key: 'physical_activity', available: true, current_satisfaction: 0.3, predicted_satisfaction: 0.45, impact: 0.6, parameters: { ...defaultHomeostasis().needs.physical_activity, rate: 0.25 }, value_before: -0.5, value_after: -0.25, utility_contribution: 0.25, formula: 'recorded engine6 need formula' }], energy_traces: [] }] };
    const original = structuredClone(historical);
    const ranking = render(<Ranking evaluation={historical} onInspect={vi.fn()} />);
    expect(screen.getByText(/Historical engine 6:/)).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Needs' })).toBeVisible();
    ranking.unmount();
    const { container } = render(<EvaluationPage evaluation={historical} ontology={ontology} />);
    expect(screen.getByText(/Historical engine 6: this evaluation scored needs from predicted satisfaction changes/)).toBeVisible();
    expect(container.querySelector('pre')).toHaveTextContent('"rate": 0.25');
    fireEvent.click(screen.getByRole('button', { name: 'Feature, need, energy & aftereffect traces' }));
    expect(screen.getByRole('heading', { name: 'Historical need contributions' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Predicted satisfaction' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Impact' })).toBeVisible();
    expect(screen.getByText('recorded engine6 need formula')).toBeVisible();
    expect(screen.queryByRole('columnheader', { name: 'Pressure' })).not.toBeInTheDocument();
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
    expect(historical).toEqual(original);
  });

});
