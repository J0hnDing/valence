import { useEffect, useState } from 'react';
import { api } from './api';
import { ActionsPage } from './Actions';
import { ComparePage } from './Compare';
import { EvaluationPage } from './Evaluation';
import { HistoryPage } from './History';
import { PersonModelPage } from './PersonModel';
import type { PersonCreationDraft } from './PersonCreation';
import { ReferencePage } from './Reference';
import { Notice, errorMessage, today } from './components';
import type { Action, Evaluation, Feature, ModelVersion, Person, State } from './types';

type Page = 'Compare' | 'Actions' | 'Person Model' | 'Feature Reference' | 'History' | 'Evaluation';
const pages: Page[] = ['Compare', 'Actions', 'Person Model', 'Feature Reference', 'History'];
export function App() {
  const [creationDraft, setCreationDraft] = useState<PersonCreationDraft>();
  const [page, setPage] = useState<Page>('Compare');
  const [ontology, setOntology] = useState<Feature[]>([]); const [persons, setPersons] = useState<Person[]>([]); const [actions, setActions] = useState<Action[]>([]);
  const [personId, setPersonId] = useState(''); const [state, setState] = useState<State>({ mental_energy: null, physical_energy: null, need_satisfaction: {}, acute_stress: 0, date: today(), notes: '' }); const [horizon, setHorizon] = useState(168);
  const [evaluation, setEvaluation] = useState<Evaluation>(); const [actionId, setActionId] = useState<string>();
  const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [attempt, setAttempt] = useState(0);
  const [stateLoading, setStateLoading] = useState(false); const [stateError, setStateError] = useState(''); const [stateAttempt, setStateAttempt] = useState(0);
  const [versionData, setVersionData] = useState<{ personId: string; versions: ModelVersion[] }>({ personId: '', versions: [] });
  const [versionSelection, setVersionSelection] = useState<{ personId: string; id: string }>({ personId: '', id: '' });
  const [modelLoading, setModelLoading] = useState(false); const [modelError, setModelError] = useState(''); const [modelAttempt, setModelAttempt] = useState(0);
  const versions = versionData.personId === personId ? versionData.versions : [];
  const selectedVersion = versions.find(version => version.id === (versionSelection.personId === personId ? versionSelection.id : ''));
  useEffect(() => {
    let active = true; setLoading(true); setError('');
    Promise.all([api.ontology(), api.persons(), api.actions()]).then(([specification, people, library]) => { if (active) { setOntology(specification.features); setPersons(people); setActions(library); setPersonId(people[0]?.id ?? ''); } }).catch(error => { if (active) setError(errorMessage(error)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);
  useEffect(() => {
    let active = true;
    setStateError('');
    if (!personId) { setStateLoading(false); return; }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(state.date)) { setStateLoading(false); setStateError('Choose a valid state date.'); return; }
    setStateLoading(true);
    api.state(personId, state.date).then(loaded => { if (active) setState(loaded); }).catch(error => { if (active) setStateError(errorMessage(error)); }).finally(() => { if (active) setStateLoading(false); });
    return () => { active = false; };
  }, [personId, state.date, stateAttempt]);
  useEffect(() => {
    let active = true; setModelError('');
    setVersionData({ personId, versions: [] }); setVersionSelection({ personId, id: '' });
    if (!personId) { setModelLoading(false); return; }
    setModelLoading(true);
    api.modelVersions(personId).then(values => {
      if (active) { setVersionData({ personId, versions: values }); setVersionSelection({ personId, id: values[0]?.id ?? '' }); }
    }).catch(error => { if (active) setModelError(errorMessage(error)); }).finally(() => { if (active) setModelLoading(false); });
    return () => { active = false; };
  }, [personId, modelAttempt]);
  function inspect(evaluation: Evaluation, actionId?: string) { setEvaluation(evaluation); setActionId(actionId); setPage('Evaluation'); }
  function personChanged(id: string) { setPersonId(id); setState(previous => ({ mental_energy: null, physical_energy: null, need_satisfaction: {}, acute_stress: 0, date: previous.date, notes: '' })); }
  function personCreated(person: Person) { setPersons(previous => [...previous, person]); personChanged(person.id); }
  function personUpdated(person: Person) { setPersons(previous => previous.map(item => item.id === person.id ? person : item)); }
  function personDeleted(id: string) { setPersons(previous => previous.filter(person => person.id !== id)); }
  useEffect(() => {
    if (personId && !persons.some(person => person.id === personId)) personChanged(persons[0]?.id ?? '');
  }, [persons, personId]);
  function versionChanged(id: string) { setVersionSelection({ personId, id }); }
  function versionSaved(saved: ModelVersion) {
    setVersionData(previous => previous.personId === saved.person_id ? { ...previous, versions: [saved, ...previous.versions.filter(item => item.id !== saved.id)] } : previous);
    setVersionSelection({ personId: saved.person_id, id: saved.id });
  }
  function actionsChanged(action?: Action, deletedId?: string) { setActions(previous => action ? previous.some(item => item.id === action.id) ? previous.map(item => item.id === action.id ? action : item) : [...previous, action] : previous.filter(item => item.id !== deletedId)); }
  return <div className="app-shell"><header className="app-header"><a className="brand" href="#" onClick={event => { event.preventDefault(); setPage('Compare'); }}><span className="brand-mark">V</span><strong>Valence</strong><span>Deterministic utility engine</span></a><div className="environment"><span className="status-dot" />LOCAL <span className="muted">/</span> v1</div></header>
    <nav className="main-nav" aria-label="Main pages">{pages.map(name => <button key={name} className={page === name ? 'active' : ''} aria-current={page === name ? 'page' : undefined} onClick={() => setPage(name)}>{name}</button>)}{evaluation && <button className={page === 'Evaluation' ? 'active' : ''} aria-current={page === 'Evaluation' ? 'page' : undefined} onClick={() => setPage('Evaluation')}>Evaluation detail</button>}</nav>
    <main>{loading ? <Notice>Connecting to the local engine…</Notice> : error ? <div className="connection-error"><Notice error>Unable to load Valence: {error}</Notice><p>Start the backend at 127.0.0.1:8010, then reconnect.</p><button onClick={() => setAttempt(attempt + 1)}>Retry connection</button></div> : <>
      {page === 'Compare' && <ComparePage persons={persons} personId={personId} onPersonChanged={personChanged} onManagePerson={() => setPage('Person Model')} versions={versions} selectedVersion={selectedVersion} onVersionChanged={versionChanged} modelLoading={modelLoading} modelError={modelError} onModelRetry={() => setModelAttempt(value => value + 1)} actions={actions} state={state} onStateChanged={setState} stateLoading={stateLoading} stateError={stateError} onStateRetry={() => setStateAttempt(value => value + 1)} horizon={horizon} onHorizonChanged={setHorizon} onInspect={inspect} />}
      {page === 'Actions' && <ActionsPage actions={actions} ontology={ontology} onChanged={actionsChanged} />}
      {page === 'Person Model' && <PersonModelPage persons={persons} personId={personId} onPersonChanged={personChanged} onPersonCreated={personCreated} onPersonUpdated={personUpdated} onPersonDeleted={personDeleted} versions={versions} selectedVersion={selectedVersion} onVersionChanged={versionChanged} onVersionSaved={versionSaved} loading={modelLoading} error={modelError} onRetry={() => setModelAttempt(value => value + 1)} ontology={ontology} state={state} horizon={horizon} creationDraft={creationDraft} onCreationDraftChanged={setCreationDraft} />}
      {page === 'Feature Reference' && <ReferencePage ontology={ontology} />}
      {page === 'History' && <HistoryPage onInspect={inspect} />}
      {page === 'Evaluation' && evaluation && <EvaluationPage key={`${evaluation.id}-${actionId ?? ''}`} evaluation={evaluation} ontology={ontology} initialActionId={actionId} />}
    </>}</main>
    <footer className="app-footer"><span>Deterministic · Interpretable · No learning</span><span>Caller-encoded features · Arbitrary utility units · Experimental ontology</span></footer>
  </div>;
}
