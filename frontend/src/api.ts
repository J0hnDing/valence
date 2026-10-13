import type { Action, ActionInput, Evaluation, Feature, HistoryEntry, InitializationPreview, InitializationQuiz, Model, ModelVersion, Person, PersonInitialization, Preview, State } from './types';

async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, { method, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const error = await response.json();
      if (typeof error.detail === 'string') message = error.detail;
      else if (Array.isArray(error.detail)) message = error.detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.join('.') ?? ''}: ${item.msg ?? 'Invalid value'}`).join('; ');
    } catch { /* Keep the HTTP status when there is no JSON error. */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function exportModelVersion(personId: string, versionId: string): Promise<void> {
  const response = await fetch(`/api/persons/${encodeURIComponent(personId)}/model-versions/${encodeURIComponent(versionId)}/export`);
  if (!response.ok) {
    let message = `Export failed (${response.status})`;
    try { const error = await response.json(); if (typeof error.detail === 'string') message = error.detail; }
    catch { /* Keep the HTTP status when there is no JSON error. */ }
    throw new Error(message);
  }
  const filename = response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1];
  if (!filename?.endsWith('.valence.json')) throw new Error('Export response is missing its version-specific filename.');
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url; link.download = filename;
  document.body.append(link);
  link.click(); link.remove();
  // Keep the object URL alive until the browser starts the download.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const api = {
  ontology: () => request<{ features: Feature[] }>('/ontology'),
  persons: () => request<Person[]>('/persons'),
  createPerson: (name: string, description: string, initialization?: PersonInitialization) => request<Person>('/persons', 'POST', { name, description: description || null, ...(initialization ? { initialization } : {}) }),
  initializationQuiz: () => request<InitializationQuiz>('/person-initialization-quiz'),
  initializationPreview: (version: '5', answers: Record<string, number | null>) => request<InitializationPreview>('/person-initialization-quiz/preview', 'POST', { version, answers }),
  updatePerson: (id: string, name: string, description: string) => request<Person>(`/persons/${encodeURIComponent(id)}`, 'PUT', { name, description: description || null }),
  deletePerson: (id: string) => request<void>(`/persons/${encodeURIComponent(id)}`, 'DELETE'),
  model: (id: string) => request<ModelVersion>(`/persons/${encodeURIComponent(id)}/model`),
  modelVersions: (id: string) => request<ModelVersion[]>(`/persons/${encodeURIComponent(id)}/model-versions`),
  exportModelVersion,
  saveModel: (id: string, model: Model) => request<ModelVersion>(`/persons/${encodeURIComponent(id)}/model`, 'PUT', model),
  state: (id: string, date: string) => request<State>(`/daily-state?person_id=${encodeURIComponent(id)}&date=${date}`),
  saveState: (person_id: string, state: State) => request<State>('/daily-state', 'PUT', { person_id, state }),
  actions: () => request<Action[]>('/actions'),
  saveAction: (action: ActionInput, id?: string) => request<Action>(id ? `/actions/${encodeURIComponent(id)}` : '/actions', id ? 'PUT' : 'POST', action),
  deleteAction: (id: string) => request<void>(`/actions/${encodeURIComponent(id)}`, 'DELETE'),
  evaluate: (person_id: string, action_ids: string[], state: State, horizon_hours: number, model_version_id: string) => request<Evaluation>('/evaluations', 'POST', { person_id, action_ids, state, horizon_hours, model_version_id }),
  history: () => request<HistoryEntry[]>('/evaluations'),
  evaluation: (id: string) => request<Evaluation>(`/evaluations/${encodeURIComponent(id)}`),
  preview: (model: Model, state: State, horizon_hours: number) => request<Preview>('/model-preview', 'POST', { model, state, horizon_hours }),
};
