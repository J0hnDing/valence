import { useEffect, useRef, useState } from 'react';
import { api } from './api';
import { errorMessage, label, Notice, number } from './components';
import type { InitializationPreview, InitializationQuiz, Model, ModelVersion, Person, PersonInitialization } from './types';

export interface PersonCreationDraft {
  name: string; description: string; method: PersonInitialization['method']; sourceId: string; sourceVersionId: string;
  rawAnswers: Record<string, string>; step: number; quizVersion?: '3' | '4' | '5';
}

function ParameterSummary({ model }: { model: Model }) {
  const groups = [
    ...Object.entries(model.features).map(([key, response]) => ({ name: label(key), values: Object.entries(response).filter(([key]) => key !== 'family') })),
    { name: 'Resource / return', values: Object.entries(model.resources ?? { time_value: 0, money_value: 0 }) },
    { name: 'Daily-state responses', values: Object.entries(model.transient) },
    ...Object.entries(model.aftereffects).map(([key, effect]) => ({ name: `${label(key)} aftereffect`, values: Object.entries(effect) })),
  ];
  return <details className="quiz-parameters"><summary>Inspect initial model parameters</summary><div className="table-scroll"><table><thead><tr><th>Response</th><th>Parameter</th><th>Value</th></tr></thead><tbody>{groups.flatMap(group => group.values.map(([key, value]) => <tr key={`${group.name}.${key}`}><td>{group.name}</td><td>{label(key)}</td><td>{number(value as number)}</td></tr>))}</tbody></table></div></details>;
}

export function PersonCreationForm({ persons, onSaved, onCancel, onBusyChanged, draft, onDraftChanged }: {
  persons: Person[]; onSaved: (person: Person) => void; onCancel?: () => void; onBusyChanged: (busy: boolean) => void;
  draft?: PersonCreationDraft; onDraftChanged?: (draft: PersonCreationDraft | undefined) => void;
}) {
  const [name, setName] = useState(draft?.name ?? ''); const [description, setDescription] = useState(draft?.description ?? '');
  const [method, setMethod] = useState<PersonInitialization['method']>(draft?.method ?? 'default');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [sourceId, setSourceId] = useState(draft?.sourceId && persons.some(person => person.id === draft.sourceId) ? draft.sourceId : persons[0]?.id ?? '');
  const [sourceData, setSourceData] = useState<{ id: string; versions: ModelVersion[] }>({ id: '', versions: [] });
  const [sourceVersionId, setSourceVersionId] = useState(draft?.sourceVersionId ?? ''); const preferredSourceVersion = useRef(draft?.sourceVersionId ?? ''); const [sourceBusy, setSourceBusy] = useState(false);
  const [sourceError, setSourceError] = useState(''); const [sourceAttempt, setSourceAttempt] = useState(0);
  const [quiz, setQuiz] = useState<InitializationQuiz>(); const [quizError, setQuizError] = useState('');
  const [quizBusy, setQuizBusy] = useState(false); const [quizAttempt, setQuizAttempt] = useState(0);
  const [rawAnswers, setRawAnswers] = useState<Record<string, string>>(draft?.rawAnswers ?? {}); const [step, setStep] = useState(draft?.step ?? 0);
  const [result, setResult] = useState<InitializationPreview>(); const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewError, setReviewError] = useState(''); const reviewRequest = useRef(0);
  const [draftNotice, setDraftNotice] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const questions = quiz?.questions ?? [];
  const valid = questions.every(question => !rawAnswers[question.id] || quiz?.options.some(option => String(option.value) === rawAnswers[question.id]));
  const reviewing = !!quiz && step === questions.length;
  const sourceVersion = sourceData.id === sourceId ? sourceData.versions.find(version => version.id === sourceVersionId && version.person_id === sourceId) : undefined;
  const ready = method === 'default' || (method === 'copy' && !!sourceVersion && !sourceBusy && !sourceError) || (method === 'quiz' && reviewing && !!result && !reviewBusy && valid);

  useEffect(() => { onDraftChanged?.({ name, description, method, sourceId, sourceVersionId, rawAnswers, step, quizVersion: quiz?.version ?? draft?.quizVersion }); }, [name, description, method, sourceId, sourceVersionId, rawAnswers, step, quiz?.version, draft?.quizVersion, onDraftChanged]);

  useEffect(() => {
    if (method !== 'copy' || !sourceId) return;
    let active = true; setSourceBusy(true); setSourceError(''); setSourceData({ id: sourceId, versions: [] }); setSourceVersionId('');
    api.modelVersions(sourceId).then(versions => {
      if (active) { const selected = versions.find(version => version.id === preferredSourceVersion.current) ?? versions[0]; setSourceData({ id: sourceId, versions }); setSourceVersionId(selected?.id ?? ''); preferredSourceVersion.current = selected?.id ?? ''; }
    }).catch(error => { if (active) setSourceError(errorMessage(error)); }).finally(() => { if (active) setSourceBusy(false); });
    return () => { active = false; };
  }, [method, sourceId, sourceAttempt]);
  useEffect(() => {
    if (method !== 'quiz' || quiz) return;
    let active = true; setQuizBusy(true); setQuizError('');
    api.initializationQuiz().then(value => {
      if (!active) return;
      setQuiz(value);
      const ids = new Set(value.questions.map(question => question.id));
      if ((draft?.quizVersion && draft.quizVersion !== value.version) || Object.keys(rawAnswers).some(id => !ids.has(id))) { setRawAnswers({}); setStep(0); setDraftNotice('The questionnaire has changed. Start with the new questions below.'); }
      else setStep(previous => Math.min(previous, value.questions.length));
    }).catch(error => { if (active) setQuizError(errorMessage(error)); }).finally(() => { if (active) setQuizBusy(false); });
    return () => { active = false; };
  }, [method, quiz, quizAttempt]);
  useEffect(() => { if (method === 'quiz' && quiz) heading.current?.focus(); }, [method, step, quiz]);
  useEffect(() => () => { reviewRequest.current += 1; }, []);

  function answers(raw = rawAnswers) {
    return Object.fromEntries(questions.map(question => [question.id, raw[question.id]?.trim() ? Number(raw[question.id]) : null]));
  }
  function changeStep(next: number) {
    reviewRequest.current += 1; setReviewBusy(false); setStep(next); setResult(undefined); setReviewError(''); setError('');
  }
  async function review(raw = rawAnswers) {
    if (!quiz || !questions.every(question => !raw[question.id] || quiz.options.some(option => String(option.value) === raw[question.id])) || reviewBusy) return;
    const request = ++reviewRequest.current; setStep(questions.length); setReviewBusy(true); setReviewError(''); setResult(undefined); setError('');
    try { const value = await api.initializationPreview(quiz.version, answers(raw)); if (request === reviewRequest.current) setResult(value); }
    catch (error) { if (request === reviewRequest.current) setReviewError(errorMessage(error)); }
    finally { if (request === reviewRequest.current) setReviewBusy(false); }
  }
  function respond(value: string) {
    const question = questions[step]; if (!question || reviewBusy || busy) return;
    const next = { ...rawAnswers, [question.id]: value }; setRawAnswers(next); setDraftNotice('');
    if (step === questions.length - 1) void review(next); else changeStep(step + 1);
  }
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (!name.trim() || !ready || busy) return;
    setBusy(true); onBusyChanged(true); setError('');
    try {
      const initialization: PersonInitialization | undefined = method === 'copy' && sourceVersion ? { method: 'copy', person_id: sourceId, model_version_id: sourceVersion.id }
        : method === 'quiz' && quiz ? { method: 'quiz', version: quiz.version, answers: answers() } : undefined;
      const created = initialization ? await api.createPerson(name.trim(), description, initialization) : await api.createPerson(name.trim(), description);
      onDraftChanged?.(undefined); onSaved(created);
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); onBusyChanged(false); }
  }
  const question = questions[step];
  const submitActions = <div className="person-form-actions"><button type="submit" className="primary" disabled={!name.trim() || !ready || busy}>{busy ? 'Creating…' : 'Create person'}</button>{onCancel && <button type="button" onClick={() => { onDraftChanged?.(undefined); onCancel(); }}>Cancel</button>}</div>;
  return <form onSubmit={save} className="person-form"><fieldset disabled={busy}>
    {(method !== 'quiz' || !quiz || reviewing) && <><h3>Create person</h3>
    <div className="person-fields"><label>Name<input required maxLength={200} value={name} onChange={event => setName(event.target.value)} /></label><label>Description (optional)<textarea maxLength={20000} rows={2} value={description} onChange={event => setDescription(event.target.value)} /></label></div></>}
    {(method !== 'quiz' || !quiz || reviewing) && <fieldset className="creation-methods"><legend>Initialize model</legend>{[
      { value: 'default', title: 'Default', detail: 'Start with editable engineering placeholders.' },
      { value: 'copy', title: 'Copy a saved version', detail: 'Use an exact snapshot from an existing person.' },
      { value: 'quiz', title: 'Personality quiz', detail: 'Answer everyday questions about what suits this person.' },
    ].map(option => <label key={option.value} className={method === option.value ? 'creation-method selected' : 'creation-method'}><input type="radio" name="initialization" value={option.value} checked={method === option.value} disabled={option.value === 'copy' && !persons.length} onChange={() => { reviewRequest.current += 1; setReviewBusy(false); setMethod(option.value as PersonInitialization['method']); setError(''); }} /><span><strong>{option.title}</strong><small>{option.detail}</small></span></label>)}</fieldset>}
    {method === 'default' && <p className="small muted">Defaults are starting values. Edit the model after creation to reflect this person.</p>}
    {method === 'copy' && <section className="copy-initialization">
      <div className="person-fields"><label>Source person<select value={sourceId} onChange={event => { setSourceId(event.target.value); setSourceVersionId(''); preferredSourceVersion.current = ''; setError(''); }}>{persons.map(person => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
        <label>Source model version<select value={sourceVersion?.id ?? ''} disabled={sourceBusy || !!sourceError} onChange={event => { setSourceVersionId(event.target.value); preferredSourceVersion.current = event.target.value; setError(''); }}><option value="" disabled>Select a saved version</option>{sourceData.id === sourceId && sourceData.versions.map((version, index) => <option key={version.id} value={version.id}>v{version.version}{index === 0 ? ' · Latest' : ''} · {new Date(version.created_at).toLocaleString()}</option>)}</select></label></div>
      {sourceBusy && <Notice>Loading source versions…</Notice>}{sourceError && <Notice error>Could not load source versions: {sourceError} <button type="button" onClick={() => setSourceAttempt(value => value + 1)}>Retry source versions</button></Notice>}
      {sourceVersion?.converted_from_legacy && <Notice>This source version predates the current contract. Its feature parameters are preserved and missing fields use defaults, including zero resource values. The original saved version stays unchanged.</Notice>}
      {!sourceBusy && !sourceError && !sourceVersion && <p className="muted">Choose an available source version before creating the person.</p>}
      {sourceVersion && <><p className="small muted">All parameters from v{sourceVersion.version} will become this person’s version 1. Each person can then be edited independently.</p><ParameterSummary model={sourceVersion.model} /></>}
    </section>}
    {method === 'quiz' && <section className="initialization-quiz" aria-label="Person initialization quiz">
      {quizBusy && <Notice>Loading your questions…</Notice>}{quizError && <Notice error>Could not load quiz: {quizError} <button type="button" onClick={() => setQuizAttempt(value => value + 1)}>Retry quiz</button></Notice>}
      {quiz && <>
        {question && <>
          <div className="quiz-progress"><span aria-live="polite">{questions.length - step} {questions.length - step === 1 ? 'question' : 'questions'} remaining</span><progress aria-label="Quiz progress" max={questions.length} value={step} /></div>
          {draftNotice && <Notice>{draftNotice}</Notice>}
          <p className="quiz-intro">{quiz.instructions.join(' ')}</p>
          <div className="quiz-card"><h2 ref={heading} tabIndex={-1}>{question.prompt}</h2><p className="quiz-example">{question.example}</p>
            <div className="quiz-scale" role="group" aria-label="Your answer">{quiz.options.map(option => <button type="button" key={`${question.id}.${option.value}`} aria-pressed={rawAnswers[question.id] === String(option.value)} onClick={() => respond(String(option.value))}>{option.label}</button>)}</div>
            <p className="small muted">Choose an answer to continue. There are no right or wrong answers.</p>
          </div>
          <div className="quiz-step-actions"><button type="button" disabled={step === 0} onClick={() => changeStep(step - 1)}>Back</button><button type="button" onClick={() => respond('')}>Skip</button><button type="button" className="text-button" onClick={() => { reviewRequest.current += 1; setReviewBusy(false); setMethod('default'); }}>Change creation method</button>{onCancel && <button type="button" onClick={() => { onDraftChanged?.(undefined); onCancel(); }}>Cancel</button>}</div>
        </>}
        {reviewing && <>
          <h2 ref={heading} tabIndex={-1}>Your starting model</h2>
          {reviewBusy && <Notice>Putting your answers together…</Notice>}{reviewError && <Notice error>Could not prepare your model: {reviewError} <button type="button" onClick={() => review()}>Try again</button></Notice>}
          {result && <>
            <p>Based on {result.answered} of {result.total} answers. You can keep refining this model as you use it.</p>
            <div className="quiz-insights">{result.insights.map(insight => <article key={insight.label}><h3>{insight.label}</h3><p>{insight.description}</p></article>)}</div>
            {result.warnings.length > 0 && <Notice>{result.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</Notice>}
            <details className="quiz-technical"><summary>How your answers become a model</summary><p>Answers can contribute to several related preferences. The model numbers are starting estimates. Response-curve shapes keep their default assumptions.</p>
              {result.defaulted.length > 0 && <details className="quiz-defaults"><summary>Values kept at their defaults ({result.defaulted.length})</summary><ul>{result.defaulted.map(path => <li key={path}>{path.split('.').map(label).join(' · ')}</li>)}</ul></details>}<ParameterSummary model={result.model} />
            </details>
          </>}
          {error && <Notice error>{error}</Notice>}{submitActions}
          <button type="button" className="text-button" onClick={() => changeStep(Math.max(0, questions.length - 1))}>Back to questions</button>
          <details className="quiz-answer-review"><summary>Review your answers</summary>{questions.map((question, index) => <div key={question.id}><div><p>{question.prompt}</p><span className="muted">{quiz.options.find(option => String(option.value) === rawAnswers[question.id])?.label ?? 'Skipped'}</span></div><button type="button" aria-label={`Edit answer ${index + 1}`} onClick={() => changeStep(index)}>Edit</button></div>)}</details>
        </>}
      </>}
    </section>}
    {method !== 'quiz' ? <>{error && <Notice error>{error}</Notice>}{submitActions}</> : null}
    {(method !== 'quiz' || reviewing) && <p className="small muted">Creation saves the initial model as version 1. You can inspect its curves and save refinements as new versions.</p>}
  </fieldset></form>;
}
