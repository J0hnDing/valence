import { useEffect, useState } from 'react';
import { api } from './api';
import { Empty, Notice, errorMessage, number } from './components';
import type { Evaluation, HistoryEntry } from './types';

export function HistoryPage({ onInspect }: { onInspect: (evaluation: Evaluation) => void }) {
  const [entries, setEntries] = useState<HistoryEntry[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [opening, setOpening] = useState('');
  useEffect(() => { let active = true; api.history().then(value => { if (active) setEntries(value); }).catch(error => { if (active) setError(errorMessage(error)); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, []);
  async function open(id: string) { setOpening(id); setError(''); try { onInspect(await api.evaluation(id)); } catch (error) { setError(errorMessage(error)); } finally { setOpening(''); } }
  return <><div className="section-heading"><div><h1>Evaluation history</h1><p>Exact action, model, state and horizon snapshots remain available after edits.</p></div><span className="muted">{entries.length} saved evaluations</span></div>{error && <Notice error>{error}</Notice>}{loading && <Notice>Loading history…</Notice>}{!loading && !entries.length && !error && <Empty>No saved evaluations. Run a comparison to create the first snapshot.</Empty>}{entries.length > 0 && <div className="table-scroll"><table><thead><tr><th>Timestamp</th><th>Person / model</th><th>Actions</th><th>Horizon</th><th>Top action</th><th>Total utility</th><th /></tr></thead><tbody>{entries.map(entry => <tr key={entry.id}><td>{new Date(entry.created_at).toLocaleString()}</td><td>{entry.person_name} <span className="version">v{entry.model_version}</span></td><td>{entry.action_count}</td><td>{number(entry.horizon_hours)} h</td><td>{entry.top_action_title}</td><td className="mono total">{number(entry.top_total_utility, true)}</td><td><button disabled={!!opening} onClick={() => open(entry.id)}>{opening === entry.id ? 'Opening…' : 'Open trace →'}</button></td></tr>)}</tbody></table></div>}</>;
}
