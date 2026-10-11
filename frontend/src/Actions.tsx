import { useState } from 'react';
import { api } from './api';
import { Empty, FeatureInfo, Notice, NumericControl, errorMessage, number } from './components';
import type { Action, ActionInput, Feature } from './types';

export function actionValid(action: ActionInput, ontology: Feature[]) {
  return action.title.trim().length > 0 && Number.isFinite(action.duration_minutes) && action.duration_minutes >= 0 && Number.isFinite(action.net_money_cost) && ontology.length > 0 && ontology.every(feature => Number.isFinite(action.features[feature.key]) && action.features[feature.key] >= feature.minimum && action.features[feature.key] <= feature.maximum) && Object.entries(action.feature_duration_minutes ?? {}).every(([key, minutes]) => ontology.some(feature => feature.key === key && feature.temporal_basis === 'rate') && Number.isFinite(minutes) && minutes >= 0 && minutes <= action.duration_minutes);
}
export function ActionEditor({ ontology, action, onSaved }: { ontology: Feature[]; action?: Action; onSaved: (action: Action) => void }) {
  const [draft, setDraft] = useState<ActionInput>(() => action ? { title: action.title, duration_minutes: action.duration_minutes, net_money_cost: action.net_money_cost ?? 0, features: { ...action.features }, feature_notes: { ...action.feature_notes }, feature_duration_minutes: { ...action.feature_duration_minutes } } : { title: '', duration_minutes: 60, net_money_cost: NaN, features: Object.fromEntries(ontology.map(feature => [feature.key, 0])), feature_notes: {}, feature_duration_minutes: {} });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const valid = actionValid(draft, ontology);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setBusy(true); setError('');
    try { onSaved(await api.saveAction({ ...draft, title: draft.title.trim() }, action?.id)); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <form onSubmit={save} className="action-editor"><fieldset disabled={busy}>
    <div className="section-heading"><div><h2>{action ? 'Edit action' : 'Encode an action'}</h2><p>Enter the caller-defined vector. Notes provide provenance and never affect utility.</p></div><button className="primary" type="submit" disabled={!valid || busy}>{busy ? 'Saving…' : action ? 'Save action' : 'Create action'}</button></div>
    {action?.converted_from_legacy && <Notice>This saved action predates the current contract. Converted feature inputs are approximations: review mental rest, learning versus curiosity, and independent structure and uncertainty. A missing money amount starts at zero. The stored action changes when you save it here.</Notice>}
    {error && <Notice error>{error}</Notice>}
    <div className="action-meta"><label>Title<input required maxLength={200} value={draft.title} onChange={event => setDraft({ ...draft, title: event.target.value })} placeholder="Action title" /></label><NumericControl name="Duration (minutes)" value={draft.duration_minutes} onChange={value => setDraft({ ...draft, duration_minutes: value })} /></div>
    <div className="action-resources"><NumericControl name="Net money cost (currency units)" min={null} value={draft.net_money_cost} onChange={value => setDraft({ ...draft, net_money_cost: value })} /><p className="small muted">Required, including 0. Positive means spending; negative means income. Enter the whole-action amount using the same currency as the Person Model.</p></div>
    <p className="small muted">For ongoing features, exposure duration can be shorter than the action. Leave it blank to use the whole action; enter 0 for no exposure. One-time outcomes count once.</p>
    <div className="feature-editor-list">
      {ontology.map((feature, index) => <section key={feature.key} className="feature-editor">
        <div className="feature-editor-title"><span className="index">{String(index + 1).padStart(2, '0')}</span><h3>{feature.display_name}</h3><code>{feature.key}</code></div>
        <NumericControl name={`${feature.display_name} value`} min={feature.minimum} max={feature.maximum} slider value={draft.features[feature.key]} onChange={value => setDraft({ ...draft, features: { ...draft.features, [feature.key]: value } })} />
        <FeatureInfo feature={feature} />
        {feature.temporal_basis === 'rate' && <div className="feature-exposure"><NumericControl name={`${feature.display_name} · Exposure duration (minutes)`} optional max={Number.isFinite(draft.duration_minutes) ? draft.duration_minutes : 0} value={draft.feature_duration_minutes?.[feature.key] ?? NaN} onChange={value => {
          const durations = { ...draft.feature_duration_minutes };
          if (Number.isNaN(value)) delete durations[feature.key]; else durations[feature.key] = value;
          setDraft({ ...draft, feature_duration_minutes: durations });
        }} /><span className="small muted">Blank: whole action ({number(draft.duration_minutes)} min)</span></div>}
        <label className="feature-note">Caller note<input value={draft.feature_notes?.[feature.key] ?? ''} placeholder="Optional encoding rationale or source" onChange={event => setDraft({ ...draft, feature_notes: { ...draft.feature_notes, [feature.key]: event.target.value } })} /></label>
      </section>)}
    </div>
    <div className="form-footer"><span className="muted">{ontology.length} required feature values · Zero duration is allowed.</span><button className="primary" type="submit" disabled={!valid || busy}>{busy ? 'Saving…' : 'Save action'}</button></div>
  </fieldset></form>;
}

export function ActionsPage({ actions, ontology, onChanged }: { actions: Action[]; ontology: Feature[]; onChanged: (action?: Action, deletedId?: string) => void }) {
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [query, setQuery] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const selected = actions.find(action => action.id === selectedId);
  async function remove() {
    if (!selected || !window.confirm(`Delete “${selected.title}”? Historical evaluations retain their saved action values.`)) return;
    setBusy(true); setError('');
    try { await api.deleteAction(selected.id); onChanged(undefined, selected.id); setSelectedId(undefined); setNotice('Action deleted. Historical snapshots are preserved.'); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <div className="library-layout">
    <aside className="library"><div className="section-heading"><h2>Actions <span className="muted">{actions.length}</span></h2><button onClick={() => { setSelectedId(undefined); setNotice(''); }}>+ New</button></div>
      <input aria-label="Search actions" value={query} onChange={event => setQuery(event.target.value)} placeholder="Filter action library" />
      <div className="library-items">{actions.filter(action => action.title.toLowerCase().includes(query.toLowerCase())).map(action => <button className={selectedId === action.id ? 'library-item selected' : 'library-item'} key={action.id} onClick={() => { setSelectedId(action.id); setNotice(''); }}><strong>{action.title}</strong><span>{number(action.duration_minutes)} min · {Object.keys(action.features).length} features</span></button>)}</div>
      {!actions.length && <Empty>Create an action to begin.</Empty>}
      {selected && <button className="danger delete-action" disabled={busy} onClick={remove}>{busy ? 'Deleting…' : 'Delete selected action'}</button>}
    </aside>
    <div>{notice && <Notice>{notice}</Notice>}{error && <Notice error>{error}</Notice>}<ActionEditor key={selected?.id ?? 'new'} ontology={ontology} action={selected} onSaved={saved => { onChanged(saved); setSelectedId(saved.id); setNotice('Action saved.'); }} /></div>
  </div>;
}
