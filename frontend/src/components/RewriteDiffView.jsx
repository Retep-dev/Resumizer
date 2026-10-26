import React from 'react';
import Wipe from './ui/Wipe';
import { copyText, useToast } from './ui/Toast';

const SUMMARY_KEY = 'summary';
export const bulletKey = (ei, bi) => `${ei}:${bi}`;

/** Plain-text export of the chosen rewrites, grouped by role, ready to paste. */
function buildText(report, filter) {
  const parts = [];
  if (report.tailored_summary && filter(SUMMARY_KEY)) parts.push(`SUMMARY\n${report.tailored_summary}`);
  (report.rewritten_experiences || []).forEach((exp, ei) => {
    const lines = (exp.rewritten_bullets || [])
      .map((b, bi) => (filter(bulletKey(ei, bi)) ? `• ${b.rewritten_bullet}` : null))
      .filter(Boolean);
    if (lines.length) parts.push(`${[exp.job_title, exp.company].filter(Boolean).join(' — ')}\n${lines.join('\n')}`);
  });
  return parts.join('\n\n');
}

/** Questions the rewriter wants answered before it adds detail it can't verify. */
function Confirm({ items }) {
  return (
    <div className="rw-confirm">
      <p>Could be stronger — add this only if it’s true:</p>
      <ul>{items.map((q, i) => <li key={i}>{q}</li>)}</ul>
    </div>
  );
}

export default function RewriteDiffView({ rewriteReport, kept, onToggleKeep, stage }) {
  const toast = useToast();
  if (!rewriteReport) return null;
  const experiences = (rewriteReport.rewritten_experiences || []).filter((e) => e.rewritten_bullets?.length);
  const total = experiences.reduce((n, e) => n + e.rewritten_bullets.filter((b) => b.status !== 'kept_original').length, 0) + (rewriteReport.tailored_summary ? 1 : 0);

  if (!experiences.length && !rewriteReport.tailored_summary) {
    return (
      <div className="empty">
        <div className="empty__plate" aria-hidden="true" />
        <h2 className="t-h2">{stage?.status === 'unavailable' ? 'Rewrites weren’t produced' : 'No rewrites came back'}</h2>
        <p>{stage?.status === 'unavailable'
          ? `${stage.message || 'The AI was unavailable.'} Rewrites need the AI, so none were made up. Run the analysis again later.`
          : 'The rewriting step didn’t return any bullets for this resume. Try running the analysis again.'}</p>
      </div>
    );
  }

  const copy = async (text, what) => {
    const ok = await copyText(text);
    toast(ok ? `${what} copied` : 'Couldn’t copy — select the text and copy it manually');
  };

  return (
    <>
      <div className="rw-toolbar" role="toolbar" aria-label="Rewrite actions">
        <span className="rw-toolbar__count" aria-live="polite">{kept.size} of {total} kept</span>
        <span className="rw-toolbar__note">
          {total ? 'Rewrites never add numbers or skills your resume doesn’t show. [Brackets] mark details only you can fill in.' : 'No rewrite was suggested for these bullets. Answer the questions under each one to make them stronger.'}
        </span>
        <div className="rw-toolbar__actions">
          <button type="button" className="btn btn--sm btn--green" disabled={!kept.size} onClick={() => copy(buildText(rewriteReport, (k) => kept.has(k)), `${kept.size} kept ${kept.size === 1 ? 'rewrite' : 'rewrites'}`)}>
            Copy kept
          </button>
          <button type="button" className="btn btn--sm" disabled={!total} onClick={() => copy(buildText(rewriteReport, () => true), 'All rewrites')}>Copy all</button>
        </div>
      </div>

      {rewriteReport.tailored_summary && (
        <section aria-labelledby="rw-summary-title" className={`card rw-summary rw-item ${kept.has(SUMMARY_KEY) ? 'is-kept' : ''}`}>
          <h2 id="rw-summary-title" className="t-h3">Tailored summary</h2>
          <p>{rewriteReport.tailored_summary}</p>
          <div className="rw-actions">
            <button type="button" className="btn btn--quiet btn--sm" onClick={() => copy(rewriteReport.tailored_summary, 'Summary')}>Copy</button>
            <button type="button" className={`btn btn--sm ${kept.has(SUMMARY_KEY) ? 'btn--green' : ''}`} aria-pressed={kept.has(SUMMARY_KEY)} onClick={() => onToggleKeep(SUMMARY_KEY)}>
              {kept.has(SUMMARY_KEY) ? 'Kept' : 'Keep'}
            </button>
          </div>
        </section>
      )}

      {experiences.map((exp, ei) => (
        <section key={ei} className="rw-role" aria-labelledby={`rw-role-${ei}`}>
          <h2 id={`rw-role-${ei}`} className="t-h2">
            {exp.job_title || 'Role'} {exp.company && <span>at {exp.company}</span>}
          </h2>
          {exp.rewritten_bullets.map((b, bi) => {
            const key = bulletKey(ei, bi);
            const on = kept.has(key);
            if (b.status === 'kept_original') {
              return (
                <article key={key} className="card rw-item rw-item--withheld" aria-label={`Original bullet ${bi + 1}, rewrite withheld`}>
                  <p className="rw-original">{b.original_bullet}</p>
                  <p className="rw-note"><span className="sticker sticker--ink-outline">Kept your wording</span> {b.note}</p>
                  {b.needs_confirmation?.length > 0 && <Confirm items={b.needs_confirmation} />}
                </article>
              );
            }
            return (
              <article key={key} className={`card rw-item ${on ? 'is-kept' : ''}`} aria-label={`Rewrite ${bi + 1} for ${exp.job_title || 'this role'}`}>
                <Wipe before={b.original_bullet} after={b.rewritten_bullet} label={`bullet ${bi + 1}`} />
                {b.note && <p className="rw-note rw-note--fill">{b.note}</p>}
                {b.star_action && b.star_result && (
                  <p className="rw-star"><b>Action:</b> {b.star_action} <b>Result:</b> {b.star_result}</p>
                )}
                {b.needs_confirmation?.length > 0 && <Confirm items={b.needs_confirmation} />}
                <div className="rw-meta">
                  <div className="rw-tags">
                    {(b.added_keywords || []).map((k, i) => <span key={i} className="sticker sticker--outline">+ {k}</span>)}
                  </div>
                  <div className="rw-actions">
                    <button type="button" className="btn btn--quiet btn--sm" onClick={() => copy(b.rewritten_bullet, 'Rewrite')}>Copy</button>
                    <button type="button" className={`btn btn--sm ${on ? 'btn--green' : ''}`} aria-pressed={on} onClick={() => onToggleKeep(key)}>
                      {on ? 'Kept' : 'Keep'}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      ))}
    </>
  );
}
