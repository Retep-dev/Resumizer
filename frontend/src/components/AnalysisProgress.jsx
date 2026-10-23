import React, { useEffect, useRef, useState } from 'react';

// The backend runs this pipeline in one request and doesn't report progress,
// so this screen describes the order of work and shows elapsed time rather
// than inventing per-step completion.
const STEPS = [
  ['Read', 'Your resume is parsed into roles, bullets and skills.'],
  ['Match', 'ATS scoring and the skill-gap check run side by side.'],
  ['Remix', 'Bullet rewrites and interview questions are written side by side.'],
];

function hint(seconds) {
  if (seconds < 20) return 'Analysis has started.';
  if (seconds < 60) return 'Still working. If the server was asleep, waking it adds up to a minute.';
  if (seconds < 150) return 'Taking longer than usual — the AI service may be busy. You can keep waiting.';
  return 'This is unusually slow. The request gives up at five minutes, and you can cancel and retry at any time.';
}

export default function AnalysisProgress({ fileName, onCancel }) {
  const [seconds, setSeconds] = useState(0);
  const headingRef = useRef(null);
  useEffect(() => {
    headingRef.current?.focus();
    const start = Date.now();
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);
  const mm = Math.floor(seconds / 60);
  const ss = String(seconds % 60).padStart(2, '0');

  return (
    <main id="main" className="page">
      <div className="wrap press">
        <div className="poster" aria-hidden="true">
          <span className="poster__a" />
          <span className="poster__b" />
          <span className="poster__c" />
        </div>
        <div>
          <h1 ref={headingRef} tabIndex={-1} className="t-title">Analysing your resume</h1>
          <p className="t-lede" style={{ marginTop: 10 }}>
            {fileName} <span className="press__timer" aria-hidden="true">· {mm}:{ss}</span>
          </p>
          <ol className="press__steps" aria-label="What happens during the analysis">
            {STEPS.map(([title, body]) => (
              <li key={title}><span><b>{title}</b><span>{body}</span></span></li>
            ))}
          </ol>
          <p className="press__hint" role="status" aria-live="polite">{hint(seconds)}</p>
          <button type="button" className="btn" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </main>
  );
}
