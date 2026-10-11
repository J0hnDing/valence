import { useState } from 'react';
import { FeatureInfo, formula, number } from './components';
import type { Feature } from './types';

export function ReferencePage({ ontology }: { ontology: Feature[] }) {
  const [query, setQuery] = useState('');
  return <><div className="section-heading"><div><h1>Feature reference</h1><p>The canonical {ontology.length}-dimensional input contract, supplied by /api/ontology.</p></div><input aria-label="Search feature reference" placeholder="Find a feature" value={query} onChange={event => setQuery(event.target.value)} /></div>
    <p className="reference-intro">Encode the action's effect or intensity, using the feature's anchors. The Person Model determines the utility response. The caller supplies real-world context, preferences, goal importance and provenance; Valence does not infer them from text. The ontology is experimental.</p>
    <nav className="reference-index" aria-label="Feature index">{ontology.map((feature, index) => <a key={feature.key} href={`#feature-${feature.key}`}>{String(index + 1).padStart(2, '0')} {feature.display_name}</a>)}</nav>
    {ontology.filter(feature => `${feature.key} ${feature.display_name} ${feature.definition}`.toLowerCase().includes(query.toLowerCase())).map(feature => <article className="reference-feature" id={`feature-${feature.key}`} key={feature.key}><div className="feature-editor-title"><h2>{feature.display_name}</h2><code>{feature.key}</code></div><FeatureInfo feature={feature} expanded /><div className="reference-columns"><div><h3>What belongs</h3><ul>{feature.belongs.map(text => <li key={text}>{text}</li>)}</ul></div><div><h3>What does not belong</h3><ul>{feature.excludes.map(text => <li key={text}>{text}</li>)}</ul></div><div><h3>Example values</h3><ul>{feature.examples.map(example => <li key={`${example.value}-${example.description}`}><code>{number(example.value)}</code> {example.description}</li>)}</ul></div></div><div className="reference-response"><span>{feature.response_family}</span><code>{formula[feature.response_family]}</code></div></article>)}
  </>;
}
