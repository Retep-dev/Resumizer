import React from 'react';

export function pct(v) {
  const n = Number(v);
  return Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : null;
}

function verdict(score) {
  if (score == null) return 'Score unavailable';
  if (score >= 75) return 'Strong match.';
  if (score >= 50) return 'Good bones. Needs a remix.';
  return 'Big gaps to close before you apply.';
}

function scoreInk(score) {
  if (score == null) return 'var(--rule)';
  if (score >= 75) return 'var(--green)';
  if (score >= 50) return 'var(--blue)';
  return 'var(--pink)';
}

const METERS = [
  ['keyword_match_score', 'Keywords'],
  ['experience_match_score', 'Experience'],
  ['formatting_score', 'Formatting'],
];

export default function ATSScoreCard({ atsScore }) {
  if (!atsScore) return null;
  const overall = pct(atsScore.overall_score);
  const matched = atsScore.matched_keywords || [];
  const missing = atsScore.missing_keywords || [];

  return (
    <>
      <section className="score-hero" aria-labelledby="score-title">
        <h2 id="score-title" className="sr-only">ATS match score</h2>
        <p className="score-num" style={{ '--score-ink': scoreInk(overall) }}>
          <span aria-hidden="true">{overall ?? '—'}</span>
          <small>{overall != null ? 'ATS match, out of 100' : 'No overall score returned'}</small>
          <span className="sr-only">{overall != null ? `ATS match score: ${overall} out of 100` : ''}</span>
        </p>
        <div className="score-side">
          <p className="verdict">{verdict(overall)}</p>
          {atsScore.breakdown_summary && <p>{atsScore.breakdown_summary}</p>}
          <ul className="meters" aria-label="Score breakdown">
            {METERS.map(([key, label]) => {
              const v = pct(atsScore[key]);
              return (
                <li key={key} className="meter">
                  <span className="meter__label">{label}</span>
                  <span className="meter__track" aria-hidden="true"><span className="meter__fill" style={{ '--v': `${v ?? 0}%` }} /></span>
                  <span className="meter__val t-num">{v ?? '—'}</span>
                  <span className="sr-only">{v != null ? `${label}: ${v} out of 100` : `${label}: not available`}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      <section aria-labelledby="kw-title">
        <h2 id="kw-title" className="t-h2">Keywords from the posting</h2>
        <div className="kw-cols">
          <div>
            <h3 className="t-h3">On your resume <span className="sticker sticker--ink-outline">{matched.length}</span></h3>
            {matched.length ? (
              <ul className="kw-list">
                {matched.map((k, i) => <li key={`${k}-${i}`}><span className="sticker sticker--yellow" style={{ '--tilt': `${(i % 3) - 1}deg` }}>{k}</span></li>)}
              </ul>
            ) : <p className="empty-line">None of the posting’s keywords were found.</p>}
          </div>
          <div>
            <h3 className="t-h3">Missing <span className="sticker sticker--ink-outline">{missing.length}</span></h3>
            {missing.length ? (
              <ul className="kw-list">
                {missing.map((k, i) => <li key={`${k}-${i}`}><span className="sticker sticker--outline" style={{ '--tilt': `${((i + 1) % 3) - 1}deg` }}>{k}</span></li>)}
              </ul>
            ) : <p className="empty-line">No missing keywords — nice.</p>}
          </div>
        </div>
      </section>
    </>
  );
}
