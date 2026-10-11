import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { App } from '../App';
import { PersonCreationForm } from '../PersonCreation';
import type { InitializationPreview, InitializationQuiz, Model, ModelVersion, Person } from '../types';
import fixtures from './fixtures.json';

const model = fixtures.model as Model;
const person: Person = { id: 'one', name: 'Ada', created_at: '2026-10-07T12:00:00Z', updated_at: '2026-10-07T12:00:00Z' };
const other: Person = { ...person, id: 'two', name: 'Lin' };
const version: ModelVersion = { id: 'v1', person_id: person.id, version: 1, model, created_at: person.created_at };
const quiz: InitializationQuiz = {
  version: '5', instructions: ['Think about what usually suits you.'],
  options: [{ label: 'Strongly disagree', value: 1 }, { label: 'Disagree', value: 2 }, { label: 'Neither agree nor disagree', value: 3 }, { label: 'Agree', value: 4 }, { label: 'Strongly agree', value: 5 }],
  questions: [
    { id: 'explore_ideas', prompt: 'You enjoy finding out how things work.', example: 'For example, looking up why a familiar object works the way it does.' },
    { id: 'plan_ahead', prompt: 'You feel better when you have a plan.', example: 'For example, deciding what to do before a busy day.' },
    { id: 'recover_quickly', prompt: 'You move on quickly after a disappointment.', example: 'For example, enjoying the rest of a day after a plan falls through.' },
  ],
};
const result: InitializationPreview = { model, warnings: ['Skipped answers keep starting assumptions.'], defaulted: ['aftereffects.fatigue.sensitivity'], answered: 2, total: 3, insights: [{ label: 'Curiosity', description: 'You tend to enjoy exploring unfamiliar ideas.' }] };

function setup(people: Person[] = [person]) {
  const onSaved = vi.fn(); const onCancel = vi.fn();
  render(<PersonCreationForm persons={people} onSaved={onSaved} onCancel={onCancel} onBusyChanged={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'New person' } });
  return { onSaved, onCancel };
}

describe('person initialization choices', () => {
  it('keeps default creation compatible and disables copying when no source exists', async () => {
    const create = vi.spyOn(api, 'createPerson').mockResolvedValue(person);
    const { onSaved } = setup([]);
    expect(screen.getByRole('radio', { name: /Copy a saved version/ })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Create person' }));
    await waitFor(() => expect(create).toHaveBeenCalledWith('New person', ''));
    expect(onSaved).toHaveBeenCalledWith(person);
  });

  it('copies the selected older version directly at creation without saving a second version', async () => {
    const latest = { ...version, id: 'v2', version: 2 };
    vi.spyOn(api, 'modelVersions').mockResolvedValue([latest, version]);
    const create = vi.spyOn(api, 'createPerson').mockResolvedValue(person);
    const save = vi.spyOn(api, 'saveModel');
    setup(); fireEvent.click(screen.getByRole('radio', { name: /Copy a saved version/ }));
    await waitFor(() => expect(screen.getByLabelText('Source model version')).toHaveValue(latest.id));
    fireEvent.change(screen.getByLabelText('Source model version'), { target: { value: version.id } });
    fireEvent.click(screen.getByRole('button', { name: 'Create person' }));
    await waitFor(() => expect(create).toHaveBeenCalledWith('New person', '', { method: 'copy', person_id: person.id, model_version_id: version.id }));
    expect(save).not.toHaveBeenCalled();
  });

  it('ignores delayed source responses after changing the source person', async () => {
    let resolveFirst!: (versions: ModelVersion[]) => void; let resolveSecond!: (versions: ModelVersion[]) => void;
    vi.spyOn(api, 'modelVersions').mockImplementation(id => new Promise(resolve => { if (id === person.id) resolveFirst = resolve; else resolveSecond = resolve; }));
    setup([person, other]); fireEvent.click(screen.getByRole('radio', { name: /Copy a saved version/ }));
    await waitFor(() => expect(resolveFirst).toBeDefined());
    fireEvent.change(screen.getByLabelText('Source person'), { target: { value: other.id } });
    expect(screen.getByRole('button', { name: 'Create person' })).toBeDisabled();
    await waitFor(() => expect(resolveSecond).toBeDefined());
    await act(async () => resolveSecond([{ ...version, id: 'other-v1', person_id: other.id }]));
    await act(async () => resolveFirst([version]));
    expect(screen.getByLabelText('Source model version')).toHaveValue('other-v1');
    expect(screen.queryByRole('option', { name: /^v1/ })).toHaveValue('other-v1');
  });

  it('offers retry for source failures and leaves creation disabled until loaded', async () => {
    const load = vi.spyOn(api, 'modelVersions').mockRejectedValueOnce(new Error('Source unavailable')).mockResolvedValue([version]);
    setup(); fireEvent.click(screen.getByRole('radio', { name: /Copy a saved version/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Source unavailable');
    expect(screen.getByRole('button', { name: 'Create person' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Retry source versions' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Create person' })).toBeEnabled());
    expect(load).toHaveBeenCalledTimes(2);
  });

  it('starts a single readable questionnaire and auto-advances agreement choices', async () => {
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    const create = vi.spyOn(api, 'createPerson');
    setup(); fireEvent.click(screen.getByRole('radio', { name: /Personality quiz/ }));
    expect(await screen.findByRole('heading', { name: quiz.questions[0].prompt })).toHaveFocus();
    expect(screen.getByText(quiz.questions[0].example)).toBeVisible();
    expect(screen.getByText('3 questions remaining')).toBeVisible();
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Go to section')).not.toBeInTheDocument();
    expect(screen.queryByText(/utility units|Section 1/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create person' })).not.toBeInTheDocument();
    for (const option of quiz.options) expect(screen.getByRole('button', { name: option.label })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Strongly agree' }));
    expect(screen.getByRole('heading', { name: quiz.questions[1].prompt })).toHaveFocus();
    expect(screen.getByText('2 questions remaining')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(screen.getByRole('button', { name: 'Strongly agree' })).toHaveAttribute('aria-pressed', 'true');
    expect(create).not.toHaveBeenCalled();
  });

  it('uses agreement, neutral and skipped answers in the reviewed atomic creation request', async () => {
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    const preview = vi.spyOn(api, 'initializationPreview').mockResolvedValue(result);
    const create = vi.spyOn(api, 'createPerson').mockResolvedValue(person);
    const { onSaved } = setup(); fireEvent.click(screen.getByRole('radio', { name: /Personality quiz/ }));
    await screen.findByRole('heading', { name: quiz.questions[0].prompt });
    fireEvent.click(screen.getByRole('button', { name: 'Strongly agree' }));
    fireEvent.click(screen.getByRole('button', { name: 'Neither agree nor disagree' }));
    fireEvent.click(screen.getByRole('button', { name: 'Skip' }));
    await screen.findByText('Based on 2 of 3 answers. You can keep refining this model as you use it.');
    const answers = { explore_ideas: 5, plan_ahead: 3, recover_quickly: null };
    expect(preview).toHaveBeenCalledWith('5', answers);
    expect(screen.getByText(result.insights[0].description)).toBeVisible();
    expect(screen.getByLabelText('Name')).toHaveValue('New person');
    expect(create).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Create person' }));
    await waitFor(() => expect(create).toHaveBeenCalledWith('New person', '', { method: 'quiz', version: '5', answers }));
    expect(onSaved).toHaveBeenCalledWith(person);
  });

  it('can revise an earlier answer and includes the last selected choice in the new preview', async () => {
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    const preview = vi.spyOn(api, 'initializationPreview').mockResolvedValue(result);
    setup(); fireEvent.click(screen.getByRole('radio', { name: /Personality quiz/ }));
    await screen.findByRole('heading', { name: quiz.questions[0].prompt });
    for (let i = 0; i < 3; i++) fireEvent.click(screen.getByRole('button', { name: 'Agree' }));
    await screen.findByRole('heading', { name: 'Your starting model' });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Create person' })).toBeEnabled());
    fireEvent.click(screen.getByText('Review your answers'));
    fireEvent.click(screen.getByRole('button', { name: 'Edit answer 1' }));
    expect(screen.queryByRole('button', { name: 'Create person' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Disagree' }));
    fireEvent.click(screen.getByRole('button', { name: 'Agree' }));
    fireEvent.click(screen.getByRole('button', { name: 'Strongly disagree' }));
    await waitFor(() => expect(preview).toHaveBeenLastCalledWith('5', { explore_ideas: 2, plan_ahead: 4, recover_quickly: 1 }));
  });

  it('ignores a delayed preview after returning to the questionnaire', async () => {
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    let resolvePreview!: (value: InitializationPreview) => void;
    vi.spyOn(api, 'initializationPreview').mockImplementation(() => new Promise(resolve => { resolvePreview = resolve; }));
    setup(); fireEvent.click(screen.getByRole('radio', { name: /Personality quiz/ }));
    await screen.findByRole('heading', { name: quiz.questions[0].prompt });
    for (let i = 0; i < 3; i++) fireEvent.click(screen.getByRole('button', { name: 'Skip' }));
    await waitFor(() => expect(resolvePreview).toBeDefined());
    fireEvent.click(screen.getByRole('button', { name: 'Back to questions' }));
    await act(async () => resolvePreview(result));
    expect(screen.getByRole('heading', { name: quiz.questions[2].prompt })).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Create person' })).not.toBeInTheDocument();
    expect(screen.queryByText(result.insights[0].description)).not.toBeInTheDocument();
  });

  it('retries loading and analysis failures without losing chosen answers', async () => {
    vi.spyOn(api, 'initializationQuiz').mockRejectedValueOnce(new Error('Quiz unavailable')).mockResolvedValue(quiz);
    const preview = vi.spyOn(api, 'initializationPreview').mockRejectedValueOnce(new Error('Analysis unavailable')).mockResolvedValue(result);
    setup(); fireEvent.click(screen.getByRole('radio', { name: /Personality quiz/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'Retry quiz' }));
    await screen.findByRole('heading', { name: quiz.questions[0].prompt });
    fireEvent.click(screen.getByRole('button', { name: 'Agree' }));
    fireEvent.click(screen.getByRole('button', { name: 'Skip' }));
    fireEvent.click(screen.getByRole('button', { name: 'Disagree' }));
    await screen.findByRole('button', { name: 'Try again' });
    expect(screen.getByRole('button', { name: 'Create person' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Create person' })).toBeEnabled());
    expect(preview).toHaveBeenLastCalledWith('5', { explore_ideas: 4, plan_ahead: null, recover_quickly: 2 });
  });

  it('permits all skips without pretending they were neutral answers', async () => {
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    const preview = vi.spyOn(api, 'initializationPreview').mockResolvedValue({ ...result, answered: 0 });
    setup(); fireEvent.click(screen.getByRole('radio', { name: /Personality quiz/ }));
    await screen.findByRole('heading', { name: quiz.questions[0].prompt });
    for (let i = 0; i < 3; i++) fireEvent.click(screen.getByRole('button', { name: 'Skip' }));
    await waitFor(() => expect(preview).toHaveBeenCalledWith('5', { explore_ideas: null, plan_ahead: null, recover_quickly: null }));
  });

  it('preserves questionnaire position, answers and metadata across page navigation', async () => {
    vi.spyOn(api, 'ontology').mockResolvedValue({ features: fixtures.ontology as import('../types').Feature[] });
    vi.spyOn(api, 'persons').mockResolvedValue([]); vi.spyOn(api, 'actions').mockResolvedValue([]);
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Manage person & model →' }));
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Draft person' } });
    fireEvent.click(screen.getByRole('radio', { name: /Personality quiz/ }));
    await screen.findByRole('heading', { name: quiz.questions[0].prompt });
    fireEvent.click(screen.getByRole('button', { name: 'Agree' }));
    fireEvent.click(screen.getByRole('button', { name: /^Compare$/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Manage person & model →' }));
    expect(await screen.findByRole('heading', { name: quiz.questions[1].prompt })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(screen.getByRole('button', { name: 'Agree' })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'Change creation method' }));
    expect(screen.getByLabelText('Name')).toHaveValue('Draft person');
  });

  it('rejects an obsolete calibration draft and starts the new questionnaire cleanly', async () => {
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    render(<PersonCreationForm persons={[person]} draft={{ name: 'Draft', description: '', method: 'quiz', sourceId: person.id, sourceVersionId: '', rawAnswers: { 'feature.old.response.strong': '8' }, step: 25 }} onSaved={vi.fn()} onBusyChanged={vi.fn()} />);
    expect(await screen.findByRole('heading', { name: quiz.questions[0].prompt })).toBeVisible();
    expect(screen.getByText('The questionnaire has changed. Start with the new questions below.')).toBeVisible();
    expect(screen.getByText('3 questions remaining')).toBeVisible();
  });
  it('resets an older quiz version even when its question IDs still exist', async () => {
    vi.spyOn(api, 'initializationQuiz').mockResolvedValue(quiz);
    render(<PersonCreationForm persons={[person]} draft={{ name: 'Draft', description: '', method: 'quiz', sourceId: person.id, sourceVersionId: '', rawAnswers: { explore_ideas: '4' }, step: 1, quizVersion: '4' }} onSaved={vi.fn()} onBusyChanged={vi.fn()} />);
    expect(await screen.findByRole('heading', { name: quiz.questions[0].prompt })).toBeVisible();
    expect(screen.getByText('The questionnaire has changed. Start with the new questions below.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Agree' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('keeps failed creation retryable and cancellation never creates a person', async () => {
    const create = vi.spyOn(api, 'createPerson').mockRejectedValueOnce(new Error('Creation unavailable')).mockResolvedValue(person);
    const { onCancel, onSaved } = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledOnce(); expect(create).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Create person' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Creation unavailable');
    expect(onSaved).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Create person' }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(person));
  });
});

