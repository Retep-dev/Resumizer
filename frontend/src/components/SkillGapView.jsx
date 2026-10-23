import React from 'react';

function List({ items, empty }) {
  return items?.length ? <dd>{items.join(', ')}</dd> : <dd className="empty-line">{empty}</dd>;
}

export default function SkillGapView({ skillGap }) {
  if (!skillGap) return null;
  const recs = skillGap.priority_skill_recommendations || [];
  return (
    <>
      <section aria-labelledby="gap-title">
        <h2 id="gap-title" className="t-h2">Skills: got it, get it</h2>
        <div className="gap-grid">
          <div className="card gap-card gap-card--have">
            <h3 className="t-h3">Got it</h3>
            <dl>
              <div><dt>Technical</dt><List items={skillGap.matched_hard_skills} empty="None matched." /></div>
              <div><dt>Soft skills</dt><List items={skillGap.matched_soft_skills} empty="None matched." /></div>
            </dl>
          </div>
          <div className="card gap-card gap-card--need">
            <h3 className="t-h3">Get it</h3>
            <dl>
              <div><dt>Technical</dt><List items={skillGap.missing_hard_skills} empty="Nothing missing." /></div>
              <div><dt>Soft skills</dt><List items={skillGap.missing_soft_skills} empty="Nothing missing." /></div>
            </dl>
          </div>
        </div>
      </section>

      {recs.length > 0 && (
        <section aria-labelledby="recs-title">
          <h2 id="recs-title" className="t-h2">Do these next, in order</h2>
          <ol className="todo">
            {recs.map((r, i) => <li key={i}><span>{r}</span></li>)}
          </ol>
        </section>
      )}
    </>
  );
}
