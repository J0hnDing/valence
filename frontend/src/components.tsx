import { useId } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Feature, Family } from './types';

export const label = (text: string) => text.replaceAll('_', ' ').replace(/^./, (first) => first.toUpperCase());
export const roundNumber = (value: number) => Number.isFinite(value) ? Number(value.toLocaleString('en-US', { maximumFractionDigits: 3, useGrouping: false })) : value;
export const number = (value: number | null | undefined, signed = false) => {
  if (value == null) return '—';
  const rounded = roundNumber(value);
  return `${signed && rounded > 0 ? '+' : ''}${(rounded === 0 ? 0 : rounded).toLocaleString(undefined, { maximumFractionDigits: 3 })}`;
};
export const displayJson = (value: unknown, space?: number) => JSON.stringify(value, (_, entry) => typeof entry === 'number' ? roundNumber(entry) : entry, space);
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'An unexpected error occurred';
export const today = () => { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; };
export const formula: Record<Family, string> = {
  asymmetric_signed: 'x ≥ 0: s₊ · x^c₊   |   x < 0: −s₋ · (−x)^c₋',
  cost: '−cost_sensitivity · x^curvature',
  signed_effort: 'x ≥ 0: −effort_sensitivity · x^effort_curvature   |   x < 0: pleasure_sensitivity · (−x)^pleasure_curvature',
  order_preference: 'preference_sensitivity · x',
  reward: 'reward_sensitivity · x^curvature',
  reward_overload: 'reward_sensitivity · x − overload_sensitivity · x²',
};

export function NumericControl({ name, value, onChange, min = 0, max, positive = false, slider = false, optional = false, step = 0.001 }: {
  name: string; value: number; onChange: (value: number) => void; min?: number | null; max?: number; positive?: boolean; slider?: boolean; optional?: boolean; step?: number | 'any';
}) {
  const id = useId();
  const valid = (optional && Number.isNaN(value)) || (Number.isFinite(value) && (min == null || value >= min) && (!positive || value > 0) && (max === undefined || value <= max));
  const explanation = !Number.isFinite(value) ? 'Enter a finite number.' : positive && value <= 0 ? 'Must be greater than zero.' : max === undefined ? `Must be at least ${number(min)}.` : `Use a value from ${number(min)} to ${number(max)}.`;
  return <div className={`numeric-control ${valid ? '' : 'invalid'}`}>
    <label htmlFor={id}>{name}</label>
    <div className="numeric-inputs">
      {slider && <input aria-label={`${name} slider`} type="range" min={min ?? undefined} max={max} step={step} value={Number.isFinite(value) ? roundNumber(value) : min ?? 0} onChange={event => onChange(roundNumber(Number(event.target.value)))} />}
      <input id={id} type="number" min={positive ? undefined : min ?? undefined} max={max} step={step} value={Number.isFinite(value) ? roundNumber(value) : ''} aria-invalid={!valid} aria-describedby={!valid ? `${id}-error` : undefined} onChange={event => onChange(event.target.value === '' ? NaN : roundNumber(Number(event.target.value)))} />
    </div>
    {!valid && <span id={`${id}-error`} className="field-error">{explanation}</span>}
  </div>;
}

export function FeatureInfo({ feature, expanded = false }: { feature: Feature; expanded?: boolean }) {
  return <details className="feature-info" open={expanded || undefined}>
    <summary>Definition & anchors <span className="muted">[{number(feature.minimum)}, {number(feature.maximum)}] · {feature.response_family}</span></summary>
    <p>{feature.definition}</p>
    <p className="small muted">{feature.temporal_basis === 'one_time' ? 'One-time outcome: valued once per action, regardless of duration.' : 'Ongoing experience: utility per hour, multiplied by exposure duration (the whole action by default).'}</p>
    <div className="anchors">{feature.anchors.map(anchor => <span key={anchor.value}><b>{number(anchor.value, true)}</b> {anchor.description}</span>)}</div>
    <p className="muted">{feature.distinction}</p>
  </details>;
}

export function Curve({ points, xLabel = 'Feature value', yLabel = 'Utility / hour' }: { points: { x: number; y: number }[]; xLabel?: string; yLabel?: string }) {
  return <div className="curve" role="img" aria-label={`${yLabel} by ${xLabel}; calculated by backend`}>
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={points} margin={{ top: 10, right: 12, bottom: 24, left: 4 }}>
        <CartesianGrid stroke="#2a3035" strokeDasharray="3 3" />
        <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} tick={{ fill: '#919da5', fontSize: 10 }} tickFormatter={value => number(value)} label={{ value: xLabel, position: 'bottom', fill: '#919da5', fontSize: 10 }} />
        <YAxis width={44} tick={{ fill: '#919da5', fontSize: 10 }} tickFormatter={value => number(value)} />
        <Tooltip formatter={(value) => [number(typeof value === 'number' ? value : Number(value)), yLabel]} labelFormatter={value => `${xLabel}: ${number(Number(value))}`} contentStyle={{ background: '#181d21', border: '1px solid #3a444b', fontSize: 12 }} />
        <Line dataKey="y" type="linear" stroke="#85cbb5" strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  </div>;
}
export function Notice({ children, error = false }: { children: React.ReactNode; error?: boolean }) {
  return <div className={error ? 'notice error' : 'notice'} role={error ? 'alert' : 'status'}>{children}</div>;
}
export function Empty({ children }: { children: React.ReactNode }) { return <p className="empty">{children}</p>; }
