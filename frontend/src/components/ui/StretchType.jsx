import React, { useEffect, useRef, useState } from 'react';
import { useFinePointer, useReducedMotion } from '../../hooks/useReducedMotion';

/**
 * Display type whose letters widen toward the pointer (variable 'wdth' axis).
 * Screen readers get the plain text via aria-label. Static for touch devices
 * and when reduced motion is requested.
 */
export default function StretchType({ text, as: Tag = 'h1', className = '', id }) {
  const ref = useRef(null);
  const letters = useRef([]);
  const reduced = useReducedMotion();
  const fine = useFinePointer();
  const [widths, setWidths] = useState(null);

  useEffect(() => {
    if (reduced || !fine) return undefined;
    const zone = ref.current?.closest('[data-stretch-zone]') || ref.current;
    if (!zone) return undefined;
    let frame = 0;
    let x = null;
    const update = () => {
      frame = 0;
      if (x == null) return setWidths(null);
      setWidths(
        letters.current.map((el) => {
          if (!el) return 100;
          const r = el.getBoundingClientRect();
          const d = Math.abs(r.left + r.width / 2 - x);
          return Math.round(84 + 56 * Math.max(0, 1 - d / 280));
        })
      );
    };
    const move = (e) => { x = e.clientX; if (!frame) frame = requestAnimationFrame(update); };
    const leave = () => { x = null; if (!frame) frame = requestAnimationFrame(update); };
    zone.addEventListener('pointermove', move);
    zone.addEventListener('pointerleave', leave);
    return () => {
      zone.removeEventListener('pointermove', move);
      zone.removeEventListener('pointerleave', leave);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [reduced, fine]);

  let n = 0;
  return (
    <Tag ref={ref} id={id} className={`stretch ${className}`} aria-label={text}>
      {text.split(' ').map((word, w) => (
        <React.Fragment key={w}>
          {w > 0 && ' '}
          <span className="stretch__word" aria-hidden="true">
            {[...word].map((ch) => {
              const i = n++;
              return (
                <span
                  key={i}
                  ref={(el) => { letters.current[i] = el; }}
                  className="stretch__ch"
                  style={widths ? { '--w': widths[i] } : undefined}
                >
                  {ch}
                </span>
              );
            })}
          </span>
        </React.Fragment>
      ))}
    </Tag>
  );
}
