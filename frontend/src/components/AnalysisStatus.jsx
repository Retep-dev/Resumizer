import React from 'react';

const STAGE_LABEL = {
  parse: 'Reading your resume',
  job: 'Reading the job posting',
  scoring: 'Scoring',
  rewrite: 'Rewrites',
  interview: 'Interview questions',
};

const STATUS_LABEL = {
  ai: 'AI',
  rule_based: 'Rule-based',
  unavailable: 'Not produced',
  failed: 'Failed',
};

function StageList({ stages }) {
  return (
    <ul className="stage-list">
      {Object.entries(STAGE_LABEL).map(([key, label]) => {
        const s = stages?.[key];
        if (!s) return null;
        const detail = key === 'scoring' ? 'Calculated in code from published criteria' : s.message || (s.model ? `Model: ${s.model}` : '');
        return (
          <li key={key} className={`stage stage--${s.status}`}>
            <span className="stage__name">{label}</span>
            <span className="stage__status">{STATUS_LABEL[s.status] || s.status}</span>
            {detail && <span className="stage__detail">{detail}</span>}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Tells the user how this analysis was produced. Older servers don't send
 * `status`, so nothing is shown for them.
 */
export default function AnalysisStatus({ analysis }) {
  const { status, stages, warnings = [] } = analysis || {};
  if (!status) return null;

  if (status === 'complete') {
    return (
      <details className="status-line">
        <summary>
          <span className="sticker sticker--green">AI analysis complete</span>
          <span className="status-line__more">How this was produced</span>
        </summary>
        <StageList stages={stages} />
        {warnings.length > 0 && <ul className="status-warnings">{warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
      </details>
    );
  }

  const unavailable = status === 'unavailable';
  return (
    <section className={`status-notice ${unavailable ? 'status-notice--down' : 'status-notice--partial'}`} aria-labelledby="status-title">
      <h2 id="status-title">
        {unavailable ? 'The AI was unavailable, so this is a limited, rule-based analysis' : 'Part of this analysis didn’t use the AI'}
      </h2>
      <p>
        {unavailable
          ? 'Keyword matches, skill gaps and the score below come straight from the text of your resume and the posting. Rewrites and sample answers need the AI, so they were left out rather than guessed. Try again later for the full analysis.'
          : 'Anything marked rule-based below was produced from the text of your resume and the posting without the AI. Nothing was invented to fill the gaps.'}
      </p>
      <StageList stages={stages} />
      {warnings.length > 0 && (
        <details>
          <summary>{warnings.length} note{warnings.length === 1 ? '' : 's'} about this analysis</summary>
          <ul className="status-warnings">{warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </details>
      )}
    </section>
  );
}
