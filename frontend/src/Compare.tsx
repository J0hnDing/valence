import { useState } from 'react';
import { api } from './api';
import { Empty, Notice, NumericControl, errorMessage, number } from './components';
import { currentStateValid, defaultHomeostasis, needKeys } from './homeostasis';
import { label } from './components';
import type { Action, Evaluation, ModelVersion, Person, State } from './types';

export function Ranking({ evaluation, onInspect }: { evaluation: Evaluation; onInspect: (evaluation: Evaluation, actionId?: string) => void }) {
  const resources = ['3', '4', '5', '6', '7', '8'].includes(evaluation.engine_version ?? '');
  const dynamic = ['6', '7', '8'].includes(evaluation.engine_version ?? '');
  return <section className="ranking"><div className="section-heading"><div><h2>Comparison result</h2><p>{evaluation.person_name} · Model v{evaluation.model_version} · {number(evaluation.horizon_hours)} h aftereffect horizon · State {evaluation.state.date}</p></div><button onClick={() => onInspect(evaluation)}>Inspect evaluation →</button></div>
    <div className="table-scroll"><table><thead><tr><th>Rank / action</th><th>Duration</th><th>{resources ? 'Ongoing' : 'During'}</th>{resources && <th>One-time</th>}<th>Aftereffects</th>{resources && <><th>Time cost</th><th>Money cost</th></>}{dynamic && <><th>Base utility</th><th>Needs</th><th>Energy</th></>}<th>Total utility ↓</th><th>Utility / action-hour</th></tr></thead><tbody>{evaluation.results.map(result => <tr key={result.action_id}>
      <td><button className="text-button action-link" onClick={() => onInspect(evaluation, result.action_id)}><span className="rank">{result.rank}</span>{result.action_snapshot.title}</button></td><td>{number(result.action_snapshot.duration_minutes)} min</td><td className="mono">{number(result.during_utility, true)}</td>{resources && <td className="mono">{number(result.one_time_utility, true)}</td>}<td className="mono">{number(result.aftereffect_utility, true)}</td>{resources && <><td className="mono">{number(result.time_cost, true)}</td><td className="mono">{number(result.money_cost, true)}</td></>}{dynamic && <><td className="mono">{number(result.base_utility, true)}</td><td className="mono">{number(result.needs_utility, true)}</td><td className="mono">{number(result.energy_utility, true)}</td></>}<td className={`total mono ${result.total_utility < 0 ? 'negative' : 'positive'}`}>{number(result.total_utility, true)}</td><td className="mono">{number(result.utility_per_action_hour, true)}{result.utility_per_action_hour == null && <span className="muted"> · zero duration</span>}</td>
    </tr>)}</tbody></table></div>
    {evaluation.engine_version === '6' && <p className="notice">Historical engine 6: needs were scored from predicted satisfaction changes. These recorded results are preserved.</p>}
    <p className="muted small">{dynamic ? 'Total = base utility + needs utility + energy utility. Base = ongoing + one-time + aftereffects − resource cost. Utility / action-hour includes needs and energy, excludes time cost, and is undefined at zero duration. Your state is never updated automatically.' : resources ? 'Total = ongoing + one-time + aftereffects − time cost − money cost. Utility / action-hour = (gross utility − money cost) / duration hours; excludes time cost. Negative money cost credits income.' : 'Legacy calculation: all feature responses were multiplied by duration, without resource costs. Utility / action-hour is recorded total utility divided by duration hours.'} Ranked by total utility. Arbitrary, internally consistent units; values are rounded only for display. This result preserves the submitted inputs.</p>
  </section>;
}

export function ComparePage({ persons, personId, onPersonChanged, onManagePerson, versions, selectedVersion, onVersionChanged, modelLoading, modelError, onModelRetry, actions, state, onStateChanged, stateLoading, stateError, onStateRetry, horizon, onHorizonChanged, onInspect }: {
  persons: Person[]; personId: string; onPersonChanged: (id: string) => void; onManagePerson: () => void;
  versions: ModelVersion[]; selectedVersion?: ModelVersion; onVersionChanged: (id: string) => void; modelLoading: boolean; modelError: string; onModelRetry: () => void;
  actions: Action[]; state: State; onStateChanged: (state: State) => void; stateLoading: boolean; stateError: string; onStateRetry: () => void; horizon: number; onHorizonChanged: (value: number) => void;
  onInspect: (evaluation: Evaluation, actionId?: string) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [evaluation, setEvaluation] = useState<Evaluation>();
  const stateValid = currentStateValid(state);
  const horizonValid = Number.isFinite(horizon) && horizon >= 0;
  const candidateIds = selected.filter(id => actions.some(action => action.id === id));
  async function saveState() {
    setBusy(true); setError(''); setNotice('');
    try { await api.saveState(personId, state); setNotice(`Daily state saved for ${state.date}.`); }
    catch (error) { setError(errorMessage(error)); } finally { setBusy(false); }
  }
  async function run() {
    if (!selectedVersion || selectedVersion.person_id !== personId) return;
    setBusy(true); setError(''); setNotice('');
    try { setEvaluation(await api.evaluate(personId, candidateIds, state, horizon, selectedVersion.id)); }
    catch (error) { setError(errorMessage(error)); } finally { setBusy(false); }
  }
  return <>
    <div className="section-heading"><div><h1>Compare actions</h1><p>Explicit features × person response × transient state. Total utility determines rank.</p></div><code className="concept">Q = F(x, θ, s)</code></div>
    {error && <Notice error>{error}</Notice>}{notice && <Notice>{notice}</Notice>}
    <div className="compare-controls">
      <section className="control-section"><div className="section-heading"><h2>01 / Person & model</h2><button className="text-button" onClick={onManagePerson}>Manage person & model →</button></div>
        {persons.length > 0 && <label>Person<select disabled={busy} value={personId} onChange={event => onPersonChanged(event.target.value)}><option value="" disabled>Select person</option>{persons.map(person => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>}
        {persons.find(person => person.id === personId)?.description && <p className="muted">{persons.find(person => person.id === personId)?.description}</p>}
        {!persons.length && <Empty>Create a person in the Person Model tab to begin.</Empty>}
        {personId && <label>Model version<select disabled={busy || modelLoading || !!modelError} value={selectedVersion?.id ?? ''} onChange={event => onVersionChanged(event.target.value)}><option value="" disabled>Select version</option>{versions.map((version, index) => <option key={version.id} value={version.id}>v{version.version}{index === 0 ? ' · Latest' : ''} · {new Date(version.created_at).toLocaleString()}</option>)}</select></label>}
        {modelLoading && <Notice>Loading model versions…</Notice>}{modelError && <Notice error>Could not load model versions: {modelError} <button onClick={onModelRetry}>Retry models</button></Notice>}
        <p className="small muted">Compare uses this saved version. Create people and edit parameters in Person Model.</p>
      </section>
      <section className="control-section"><div className="section-heading"><h2>02 / Daily state</h2><button onClick={saveState} disabled={!personId || busy || stateLoading || !stateValid || !!stateError}>Save state</button></div>
        <label>Date<input type="date" disabled={busy} value={state.date} onChange={event => onStateChanged({ ...state, date: event.target.value })} /></label>
        {stateLoading && <Notice>Loading saved state…</Notice>}{stateError && <Notice error>Could not load state: {stateError} <button onClick={onStateRetry}>Retry</button></Notice>}
        <fieldset disabled={!personId || busy || stateLoading || !!stateError} className="state-fields"><p className="small muted">Unknown values disable their need or energy contribution. Need pressure scores each action from your current satisfaction. Evaluation never changes your state.</p>
          {(['mental_energy', 'physical_energy'] as const).map(key => <div className="optional-state" key={key}><label>{label(key)} availability<select value={state[key] == null ? 'unknown' : 'provided'} onChange={event => onStateChanged({ ...state, [key]: event.target.value === 'unknown' ? null : NaN })}><option value="unknown">Unknown</option><option value="provided">Provided</option></select></label>{state[key] != null && <NumericControl name={key.replaceAll('_', ' ')} value={state[key]!} min={0} max={1} slider onChange={value => onStateChanged({ ...state, [key]: value })} />}</div>)}
          <NumericControl name="acute stress" value={state.acute_stress} min={0} max={1} slider onChange={value => onStateChanged({ ...state, acute_stress: value })} />
          <h3>Need satisfaction</h3><p className="small muted">Below the lower bound is deficit; within the preferred band is optimal; above the upper bound is overload.</p>
          {needKeys.map(key => { const value = state.need_satisfaction?.[key]; const params = (selectedVersion?.model.homeostasis ?? defaultHomeostasis()).needs[key]; return <div className="optional-state" key={key}><label>{label(key)} availability<select value={value === undefined ? 'unknown' : 'provided'} onChange={event => { const needs = { ...state.need_satisfaction }; if (event.target.value === 'unknown') delete needs[key]; else needs[key] = NaN; onStateChanged({ ...state, need_satisfaction: needs }); }}><option value="unknown">Unknown</option><option value="provided">Provided</option></select></label>{value !== undefined && <NumericControl name={`${label(key)} satisfaction`} value={value} min={0} max={1} slider onChange={value => onStateChanged({ ...state, need_satisfaction: { ...state.need_satisfaction, [key]: value } })} />}<p className="small muted">Preferred band: {number(params.lower)}–{number(params.upper)}{value !== undefined && Number.isFinite(value) ? ` · ${value < params.lower ? 'Deficit' : value > params.upper ? 'Overload' : 'Optimal'}` : ' · Unknown disables contribution'}</p></div>; })}<label>State notes<textarea value={state.notes ?? ''} rows={2} placeholder="Optional diagnostic context" onChange={event => onStateChanged({ ...state, notes: event.target.value })} /></label></fieldset>
      </section>
      <section className="control-section candidates"><div className="section-heading"><h2>03 / Candidates</h2><button className="text-button" onClick={() => setSelected(candidateIds.length === actions.length ? [] : actions.map(action => action.id))}>{candidateIds.length === actions.length && actions.length > 0 ? 'Clear' : 'Select all'}</button></div>
        <div className="candidate-list">{actions.map(action => <label className="candidate" key={action.id}><input type="checkbox" checked={selected.includes(action.id)} onChange={event => setSelected(event.target.checked ? [...selected, action.id] : selected.filter(id => id !== action.id))} /><span>{action.title}<small>{number(action.duration_minutes)} min</small></span></label>)}{!actions.length && <Empty>Create encoded actions in the Actions page.</Empty>}</div>
        <NumericControl name="Aftereffect horizon (hours)" value={horizon} onChange={onHorizonChanged} />
        <button className="primary run" disabled={!personId || !selectedVersion || selectedVersion.person_id !== personId || modelLoading || !!modelError || candidateIds.length === 0 || !stateValid || !horizonValid || busy || stateLoading || !!stateError} onClick={run}>{busy ? 'Working…' : `Evaluate ${candidateIds.length} action${candidateIds.length === 1 ? '' : 's'} →`}</button>
      </section>
    </div>
    {evaluation ? <Ranking evaluation={evaluation} onInspect={onInspect} /> : <Empty>Select a person and candidate actions to calculate their complete utility traces.</Empty>}
  </>;
}
