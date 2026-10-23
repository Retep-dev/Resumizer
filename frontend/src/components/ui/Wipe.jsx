import React, { useId, useState } from 'react';

/**
 * Before/after comparison for one resume line. The rewrite wipes over the
 * original; Before/After buttons and a range slider (keyboard accessible)
 * control it. Defaults to showing the rewrite.
 */
export default function Wipe({ before, after, label = 'this bullet' }) {
  const [p, setP] = useState(100);
  const [dragging, setDragging] = useState(false);
  const id = useId();
  const showingAfter = p > 50;
  return (
    <div className={`wipe ${dragging ? 'is-dragging' : ''}`}>
      <div className="wipe__stage" style={{ '--p': `${p}%` }}>
        <p className="wipe__layer wipe__layer--before" aria-hidden={showingAfter}>
          <span className="wipe__tag">Original</span>
          {before}
        </p>
        <p className="wipe__layer wipe__layer--after" aria-hidden={!showingAfter}>
          <span className="wipe__tag">Rewrite</span>
          {after}
        </p>
        <span className="wipe__handle" aria-hidden="true" />
      </div>
      <div className="wipe__ctrl">
        <button type="button" aria-pressed={p === 0} onClick={() => setP(0)}>Original</button>
        <input
          id={id}
          type="range"
          min="0"
          max="100"
          value={p}
          aria-label={`Compare original and rewrite for ${label}`}
          aria-valuetext={showingAfter ? 'Showing rewrite' : 'Showing original'}
          onChange={(e) => setP(+e.target.value)}
          onPointerDown={() => setDragging(true)}
          onPointerUp={() => setDragging(false)}
        />
        <button type="button" aria-pressed={p === 100} onClick={() => setP(100)}>Rewrite</button>
      </div>
    </div>
  );
}
