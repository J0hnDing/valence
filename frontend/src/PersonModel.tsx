import { useEffect, useState } from 'react';
import { api } from './api';
import { PersonCreationForm } from './PersonCreation';
import type { PersonCreationDraft } from './PersonCreation';
import { Curve, Empty, FeatureInfo, Notice, NumericControl, errorMessage, formula, label, number } from './components';
import { currentStateValid, defaultHomeostasis, homeostasisValid, needKeys } from './homeostasis';
import type { Feature, Model, ModelVersion, Person, Preview, State } from './types';

export function modelValid(model: Model) {
  return Object.values(model.features).every(response => Object.entries(response).every(([key, value]) => {
    if (key === 'family') return true;
    if (typeof value !== 'number' || !Number.isFinite(value)) return false;
    if (key === 'preference_sensitivity') return value >= -64 && value <= 64;
    return key.includes('curvature') ? value > 0 : value >= 0;
  })) && [model.resources?.time_value ?? 0, model.resources?.money_value ?? 0].every(value => Number.isFinite(value) && value >= 0) && Object.entries(model.transient).every(([key, value]) => Number.isFinite(value) && value >= 0 && (!key.startsWith('low_') || value <= 64)) && homeostasisValid(model.homeostasis ?? defaultHomeostasis()) && Object.values(model.aftereffects).every(effect => Number.isFinite(effect.sensitivity) && effect.sensitivity >= 0 && Number.isFinite(effect.half_life_hours) && effect.half_life_hours > 0);
}
export function ModelEditor({ personId, initial, ontology, state, horizon, onVersionSaved, onBusyChanged }: { personId: string; initial: ModelVersion; ontology: Feature[]; state: State; horizon: number; onVersionSaved: (version: ModelVersion) => void; onBusyChanged?: (busy: boolean) => void }) {
  const [model, setModel] = useState<Model>(() => ({ ...structuredClone(initial.model), resources: { time_value: 0, money_value: 0, ...initial.model.resources }, homeostasis: structuredClone(initial.model.homeostasis ?? defaultHomeostasis()) }));
  const [preview, setPreview] = useState<Preview>(); const [previewBusy, setPreviewBusy] = useState(false);
  const [previewError, setPreviewError] = useState(''); const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [busy, setBusy] = useState(false);
  const valid = modelValid(model);
  const stateValid = currentStateValid(state);
  const homeostasis = model.homeostasis!;
  useEffect(() => {
    let active = true; setPreview(undefined); setPreviewError('');
    if (!valid || !stateValid || !Number.isFinite(horizon) || horizon < 0) { setPreviewBusy(false); return; }
    setPreviewBusy(true);
    const timer = window.setTimeout(() => {
      api.preview(model, state, horizon).then(value => { if (active) setPreview(value); }).catch(error => { if (active) setPreviewError(errorMessage(error)); }).finally(() => { if (active) setPreviewBusy(false); });
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [model, valid, stateValid, state, horizon]);
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (!valid || busy) return; setBusy(true); onBusyChanged?.(true); setError(''); setNotice('');
    try { const saved = await api.saveModel(personId, model); setNotice(`Saved model version ${saved.version}. Historical evaluations retain their original versions.`); onVersionSaved(saved); }
    catch (error) { setError(errorMessage(error)); } finally { setBusy(false); onBusyChanged?.(false); }
  }
  return <form onSubmit={save}><fieldset disabled={busy}>
    <div className="section-heading"><div><h2>Response parameters <span className="version">v{initial.version}</span></h2><p>Inspect or edit this saved snapshot. Saving creates a new latest version and preserves v{initial.version}.</p></div><button className="primary" type="submit" disabled={!valid || busy}>{busy ? 'Saving…' : 'Save new version'}</button></div>
    {initial.converted_from_legacy && <Notice>This saved version predates the current contract. Dynamic needs receive engineering defaults. Energy uses the new bounded formula with saved strengths retained up to 64. Earlier feature conversions may be approximations: review mental rest, learning versus curiosity, and independent structure and uncertainty. Missing resource values start at zero. Saving creates a new version; the original version and its evaluations remain unchanged.</Notice>}
    {notice && <Notice>{notice}</Notice>}{error && <Notice error>{error}</Notice>}{previewError && <Notice error>Curve preview failed: {previewError}</Notice>}
    <p className="small muted">Response curves are computed by the backend using current state: mental energy {state.mental_energy == null ? 'Unknown' : number(state.mental_energy)}, physical energy {state.physical_energy == null ? 'Unknown' : number(state.physical_energy)}, acute stress {number(state.acute_stress)}. Change state and the {number(horizon)} h horizon in Compare.</p>
    {(!valid || !stateValid) && <Notice error>Correct invalid model or transient-state values to view response curves.</Notice>}
    <div className="model-feature-list">{ontology.map((feature, index) => {
      const response = model.features[feature.key]; if (!response) return null;
      const curve = preview?.features[feature.key];
      return <section className="model-feature" key={feature.key}>
        <div className="model-feature-settings"><div className="feature-editor-title"><span className="index">{String(index + 1).padStart(2, '0')}</span><h3>{feature.display_name}</h3><span className="muted small">{response.family}</span></div>
          <p className="feature-definition">{feature.definition}</p><p className="small muted">{feature.temporal_basis === 'one_time' ? 'One-time outcome · utility per action' : 'Ongoing experience · utility per hour'}</p><code className="formula">{formula[response.family]}</code>
          {(feature.key === 'mental_effort' || feature.key === 'physical_effort') && <p className="small muted">Effort is a separate cost; rest or bodily pleasure can occur at the same time. Energy adjusts effort costs with a bounded positive modifier. Unknown energy leaves the base cost unchanged.</p>}
          <div className="parameter-grid">{Object.entries(response).filter(([key]) => key !== 'family').map(([key, value]) => <NumericControl key={key} name={`${feature.display_name} · ${label(key)}`} value={value as number} min={key === 'preference_sensitivity' ? -64 : 0} max={key === 'preference_sensitivity' ? 64 : undefined} positive={key.includes('curvature')} onChange={value => { setNotice(''); setModel({ ...model, features: { ...model.features, [feature.key]: { ...response, [key]: value } } }); }} />)}</div>
          {response.family === 'reward_overload' && <p className="preferred">Preferred exposure: <strong>{curve ? curve.preferred_exposure == null ? 'Undefined (zero overload)' : number(curve.preferred_exposure) : '—'}</strong> <span className="muted">backend-derived, clamped to [0, 1]</span></p>}
          <FeatureInfo feature={feature} />
        </div>
        <div className="model-chart">{curve ? <Curve points={curve.points} yLabel={feature.temporal_basis === 'one_time' ? 'Utility / action' : 'Utility / hour'} /> : <Empty>{previewBusy ? 'Calculating response…' : 'Response preview unavailable'}</Empty>}</div>
      </section>;
    })}</div>
    <section className="resource-model"><h2>Resource / return</h2><p className="muted">Time value is the expected utility of another use of one hour. Money value is utility per currency unit. Both costs are deducted once from total utility; utility per action-hour excludes time cost.</p><div className="parameter-grid"><NumericControl name="Time value (utility / hour)" value={model.resources?.time_value ?? 0} onChange={value => { setNotice(''); setModel({ ...model, resources: { time_value: value, money_value: model.resources?.money_value ?? 0 } }); }} /><NumericControl name="Money value (utility / currency unit)" value={model.resources?.money_value ?? 0} onChange={value => { setNotice(''); setModel({ ...model, resources: { time_value: model.resources?.time_value ?? 0, money_value: value } }); }} /></div><p className="small muted">Use one consistent currency for all action amounts. Zero disables the corresponding cost.</p><code className="formula">resource cost = time value × duration hours + money value × net money cost</code></section>
    <section className="homeostasis-model"><h2>Current-state need pressure</h2><p className="muted">Each need starts with sensitivity 1 on the shared utility scale, independent of intrinsic feature weights. Satisfaction below the preferred band is deficit; above it is overload. Need pressure depends only on current satisfaction: positive in deficit, zero in the preferred band, and negative in overload. Need utility multiplies this pressure by the associated action-feature value once per action, independently of positive duration. Unknown satisfaction disables that need.</p><code className="formula">D = max(0, (lower − current) / lower) · E = max(0, (current − upper) / (1 − upper)) · pressure = D² − E² · utility = sensitivity × pressure × action-feature value</code>
      <div className="need-parameter-list">{needKeys.map(key => <section key={key} className="need-parameter-editor"><h3>{label(key)}</h3><div className="parameter-grid">{(['lower', 'upper', 'sensitivity'] as const).map(parameter => <NumericControl key={parameter} name={`${label(key)} · ${label(parameter)}`} value={homeostasis.needs[key][parameter]} min={parameter === 'lower' || parameter === 'upper' ? 0.001 : 0} max={parameter === 'lower' || parameter === 'upper' ? 0.999 : parameter === 'sensitivity' ? 64 : 1} onChange={value => { setNotice(''); setModel({ ...model, homeostasis: { ...homeostasis, needs: { ...homeostasis.needs, [key]: { ...homeostasis.needs[key], [parameter]: value } } } }); }} />)}</div>{!(homeostasis.needs[key].lower > 0 && homeostasis.needs[key].lower <= homeostasis.needs[key].upper && homeostasis.needs[key].upper < 1) && <p className="field-error">Use 0 &lt; lower ≤ upper &lt; 1.</p>}</section>)}</div>
      <NumericControl name="Mental stimulation · Mental effort weight" value={homeostasis.mental_effort_weight} min={0} max={1} onChange={value => { setNotice(''); setModel({ ...model, homeostasis: { ...homeostasis, mental_effort_weight: value } }); }} /><p className="small muted">Learning gain weight: {number(1 - homeostasis.mental_effort_weight)}. These complementary weights blend mental effort and learning gain as action scoring inputs for mental stimulation. They do not estimate state changes or change intrinsic feature responses.</p>
    </section>
    <section className="transient-model"><h2>Energy & stress response</h2><p className="muted">Energy response strength is alpha in the bounded effort modifier below. Unknown energy is neutral. Stress parameters keep their existing response behavior.</p><div className="parameter-grid">{Object.entries(model.transient).map(([key, value]) => <NumericControl key={key} name={key === 'low_mental_energy_cognitive_multiplier' ? 'Mental energy response strength (alpha)' : key === 'low_physical_energy_physical_multiplier' ? 'Physical energy response strength (alpha)' : label(key)} value={value} max={key.startsWith('low_') ? 64 : undefined} onChange={value => { setNotice(''); setModel({ ...model, transient: { ...model.transient, [key]: value } }); }} />)}</div><div className="formula-stack"><code>mental effort modifier = clip(1 + alpha · (0.7 − mental energy), 0.5, 2)</code><code>physical effort modifier = clip(1 + alpha · (0.7 − physical energy), 0.5, 2)</code><code>effective overload = base · (1 + overload multiplier · acute stress)</code><code>effective negative sensitivity = base · (1 + negative multiplier · acute stress)</code></div></section>
    <section className="aftereffect-model"><h2>Persistent aftereffects</h2><p className="muted">Sensitivity scales each trigger; half-life sets decay. Curves show the backend's unit-trigger response. Real amplitudes depend on the evaluated action.</p><code className="formula">effect(t) = A · 2^(−t / half_life_hours) · A = sign · sensitivity · trigger</code>
      <div className="aftereffect-editors">{Object.entries(model.aftereffects).map(([name, effect]) => <section className="aftereffect-editor" key={name}><h3>{label(name)} <span className={['accomplishment', 'pride_ego', 'relief', 'inspiration'].includes(name) ? 'positive' : 'negative'}>{['accomplishment', 'pride_ego', 'relief', 'inspiration'].includes(name) ? '+' : '−'}</span></h3><div className="parameter-grid"><NumericControl name={`${label(name)} sensitivity`} value={effect.sensitivity} onChange={value => { setNotice(''); setModel({ ...model, aftereffects: { ...model.aftereffects, [name]: { ...effect, sensitivity: value } } }); }} /><NumericControl name={`${label(name)} half-life (hours)`} value={effect.half_life_hours} positive onChange={value => { setNotice(''); setModel({ ...model, aftereffects: { ...model.aftereffects, [name]: { ...effect, half_life_hours: value } } }); }} /></div>{preview?.aftereffects[name] ? <Curve points={preview.aftereffects[name].points} xLabel="Hours after action" /> : <Empty>{previewBusy ? 'Calculating decay…' : 'Decay preview unavailable'}</Empty>}</section>)}</div>
    </section>
    <div className="form-footer"><span className="muted">Curves and utility values come from the Python engine.</span><button className="primary" type="submit" disabled={!valid || busy}>{busy ? 'Saving…' : 'Save new version'}</button></div>
  </fieldset></form>;
}
function PersonForm({ person, onSaved, onCancel, onBusyChanged, disabled }: { person?: Person; onSaved: (person: Person) => void; onCancel?: () => void; onBusyChanged: (busy: boolean) => void; disabled?: boolean }) {
  const [name, setName] = useState(person?.name ?? '');
  const [description, setDescription] = useState(person?.description ?? '');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (!name.trim() || busy) return;
    setBusy(true); onBusyChanged(true); setError('');
    try { onSaved(person ? await api.updatePerson(person.id, name.trim(), description) : await api.createPerson(name.trim(), description)); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); onBusyChanged(false); }
  }
  return <form onSubmit={save} className="person-form"><fieldset disabled={busy || disabled}>
    <h3>{person ? 'Edit person' : 'Create person'}</h3>
    <div className="person-fields"><label>Name<input required maxLength={200} value={name} onChange={event => setName(event.target.value)} /></label><label>Description (optional)<textarea maxLength={20000} rows={2} value={description} onChange={event => setDescription(event.target.value)} /></label></div>
    {error && <Notice error>{error}</Notice>}
    <div className="person-form-actions"><button type="submit" className="primary" disabled={!name.trim() || busy}>{busy ? 'Saving…' : person ? 'Save person' : 'Create person'}</button>{onCancel && <button type="button" onClick={onCancel}>Cancel</button>}</div>
    <p className="small muted">{person ? 'Name and description changes do not create a model version. Historical evaluations keep their recorded names.' : 'Creates a computational Person Model with engineering placeholder parameters. You can edit them below.'}</p>
  </fieldset></form>;
}

export function PersonModelPage({ persons, personId, onPersonChanged, onPersonCreated, onPersonUpdated, onPersonDeleted, versions, selectedVersion, onVersionChanged, onVersionSaved, loading, error, onRetry, ontology, state, horizon, creationDraft, onCreationDraftChanged }: {
  persons: Person[]; personId: string; onPersonChanged: (id: string) => void; onPersonCreated: (person: Person) => void; onPersonUpdated: (person: Person) => void;
  onPersonDeleted: (id: string) => void;
  versions: ModelVersion[]; selectedVersion?: ModelVersion; onVersionChanged: (id: string) => void; onVersionSaved: (version: ModelVersion) => void;
  loading: boolean; error: string; onRetry: () => void; ontology: Feature[]; state: State; horizon: number;
  creationDraft?: PersonCreationDraft; onCreationDraftChanged?: (draft: PersonCreationDraft | undefined) => void;
}) {
  const [creating, setCreating] = useState(!persons.length || !!creationDraft); const [editingPerson, setEditingPerson] = useState(false);
  const [notice, setNotice] = useState(''); const [personBusy, setPersonBusy] = useState(false); const [modelBusy, setModelBusy] = useState(false);
  const [deleting, setDeleting] = useState(false); const [deleteError, setDeleteError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const person = persons.find(person => person.id === personId); const busy = personBusy || modelBusy || deleting;
  useEffect(() => { setEditingPerson(false); setNotice(''); setDeleteError(''); setConfirmDelete(false); }, [personId]);
  useEffect(() => { if (!persons.length) setCreating(true); }, [persons.length]);
  async function remove() {
    if (!person || busy || !confirmDelete) return;
    setDeleting(true); setDeleteError(''); setNotice('');
    try { await api.deletePerson(person.id); onPersonDeleted(person.id); }
    catch (error) { setDeleteError(errorMessage(error)); }
    finally { setDeleting(false); }
  }
  return <>
    <div className="section-heading"><div><h1>Person Model</h1><p>Create and manage people, inspect saved versions, and edit response parameters.</p></div><button disabled={busy} onClick={() => { setCreating(true); setEditingPerson(false); setConfirmDelete(false); setDeleteError(''); setNotice(''); }}>+ Create person</button></div>
    <section className="person-management">
      <div className="person-selection"><label>Person<select disabled={busy} value={personId} onChange={event => { setCreating(false); setEditingPerson(false); onPersonChanged(event.target.value); }}><option value="" disabled>Select person</option>{persons.map(person => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
        {person && !creating && <button disabled={busy} onClick={() => { setEditingPerson(!editingPerson); setNotice(''); }}>{editingPerson ? 'Close person editor' : 'Edit person'}</button>}
        {person && !creating && <button className="danger" disabled={busy || confirmDelete} onClick={() => { setConfirmDelete(true); setDeleteError(''); setNotice(''); }}>Delete person</button>}
      </div>
      {confirmDelete && person && <div role="group" aria-label="Confirm person deletion" className="person-delete-confirmation"><p>Delete “{person.name}”? This removes the person from Person Model and Compare. Saved evaluations and their snapshots remain in History.</p><div className="person-form-actions"><button className="danger" disabled={busy} onClick={remove}>{deleting ? 'Deleting…' : 'Confirm delete person'}</button><button disabled={busy} onClick={() => { setConfirmDelete(false); setDeleteError(''); }}>Cancel deletion</button></div></div>}
      {deleteError && <Notice error>Could not delete person: {deleteError}</Notice>}
      {creating ? <PersonCreationForm key="create" persons={persons} draft={creationDraft} onDraftChanged={onCreationDraftChanged} onBusyChanged={setPersonBusy} onCancel={persons.length ? () => setCreating(false) : undefined} onSaved={person => { setCreating(false); onPersonCreated(person); }} /> : person && <>
        {editingPerson ? <PersonForm key={person.id} person={person} disabled={modelBusy || deleting} onBusyChanged={setPersonBusy} onCancel={() => setEditingPerson(false)} onSaved={saved => { onPersonUpdated(saved); setEditingPerson(false); setNotice('Person details saved.'); }} /> : <p className="muted">{person.description || 'No description.'}</p>}
        <div className="version-selection"><label>Model version<select disabled={busy || loading || !!error} value={selectedVersion?.id ?? ''} onChange={event => { setNotice(''); onVersionChanged(event.target.value); }}><option value="" disabled>Select version</option>{versions.map((version, index) => <option key={version.id} value={version.id}>v{version.version}{index === 0 ? ' · Latest' : ''} · {new Date(version.created_at).toLocaleString()}</option>)}</select></label><p className="small muted">{selectedVersion ? `Inspecting v${selectedVersion.version}. Compare uses this selected saved version. Parameter edits take effect after saving a new version.` : 'Choose a saved version to inspect its parameters and response curves.'}</p></div>
      </>}
      {notice && <Notice>{notice}</Notice>}
    </section>
    {!creating && person && <>{error && <Notice error>Could not load model versions: {error} <button onClick={onRetry}>Retry models</button></Notice>}{loading && <Notice>Loading model versions…</Notice>}
      {selectedVersion && !loading && !error && selectedVersion.person_id === personId && <fieldset disabled={personBusy || deleting}><ModelEditor key={selectedVersion.id} initial={selectedVersion} personId={personId} ontology={ontology} state={state} horizon={horizon} onBusyChanged={setModelBusy} onVersionSaved={saved => { onVersionSaved(saved); setNotice(`Saved model version ${saved.version}. Previous versions remain available.`); }} /></fieldset>}
    </>}
    {!person && !creating && <Empty>Select or create a person to inspect a model.</Empty>}
  </>;
}
