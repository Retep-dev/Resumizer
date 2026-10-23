import React, { useState } from 'react';
import './preview-chrome.css';

const STATES = [
  { id: 'empty', label: 'Empty' },
  { id: 'loading', label: 'Loading' },
  { id: 'error', label: 'Error' },
  { id: 'ready', label: 'Results' },
];

// Neutral review chrome shared by all three concepts. Not part of any design.
export default function PrototypeBar({ concept, proto }) {
  const [open, setOpen] = useState(false);
  if (window.self !== window.top) return null; // hidden inside gallery thumbnails
  return (
    <div className={`dp-bar ${open ? 'is-open' : ''}`} role="region" aria-label="Design preview controls">
      <button className="dp-bar__toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="dp-bar__dot" aria-hidden="true" />
        Preview {concept}
      </button>
      {open && (
        <div className="dp-bar__panel">
          <p className="dp-bar__note">
            Prototype with sample data. Nothing is uploaded or sent to the Resumizer API.
          </p>
          <div className="dp-bar__group" role="group" aria-label="Show state">
            {STATES.map((s) => (
              <button
                key={s.id}
                className={proto.status === s.id ? 'is-active' : ''}
                aria-pressed={proto.status === s.id}
                onClick={() => {
                  proto.forceState(s.id);
                  if (proto.view === 'landing') proto.setView(s.id === 'ready' ? 'match' : 'upload');
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
          <div className="dp-bar__links">
            <a href="/design-preview">All concepts</a>
            {['a', 'b', 'c']
              .filter((c) => c !== concept.toLowerCase())
              .map((c) => (
                <a key={c} href={`/design-preview/${c}?view=${proto.view}`}>
                  Option {c.toUpperCase()}
                </a>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
