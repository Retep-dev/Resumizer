import React, { useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { usePrototype, useFonts, usePageColors, useCoach } from '../usePrototype';
import { PIPELINE, SAMPLE_JD, SAMPLE_RESPONSE, COACH_SUGGESTIONS } from '../data';
import PrototypeBar from '../PrototypeBar';
import './atelier.css';

const FONTS =
  'https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..800;1,6..96,400..700&family=Hanken+Grotesk:wght@400;500;600&display=swap';

const SITTINGS = [
  { id: 'match', numeral: 'I', name: 'Measure' },
  { id: 'rewrite', numeral: 'II', name: 'Alter' },
  { id: 'interview', numeral: 'III', name: 'Rehearse' },
  { id: 'coach', numeral: 'IV', name: 'Counsel' },
];

const sample = SAMPLE_RESPONSE.analysis;

function verdict(score) {
  if (score >= 75) return 'Fits well. A few finishing touches.';
  if (score >= 50) return 'Close. A few seams need taking in.';
  return 'Loose in too many places. Worth a recut.';
}

/* ───────────────────────── Shared pieces ───────────────────────── */

function Wordmark({ onClick }) {
  return (
    <button className="at-wordmark" onClick={onClick} aria-label="Resumizer home">
      Resumizer
    </button>
  );
}

// Measuring tape: the signature element of this concept.
function Tape({ value, size = 'lg', label }) {
  const ticks = [];
  for (let i = 0; i <= 100; i++) {
    const major = i % 10 === 0;
    const mid = i % 5 === 0;
    ticks.push(
      <line
        key={i}
        x1={i * 10}
        x2={i * 10}
        y1={0}
        y2={major ? 22 : mid ? 15 : 9}
        className="at-tape__tick"
      />
    );
    if (major && size === 'lg') {
      ticks.push(
        <text key={`t${i}`} x={i * 10} y={36} className="at-tape__num" textAnchor="middle">
          {i}
        </text>
      );
    }
  }
  return (
    <div className={`at-tape at-tape--${size}`} role="img" aria-label={`${label}: ${value} out of 100`}>
      <svg viewBox="-10 0 1020 46" preserveAspectRatio="none" aria-hidden="true">
        <rect x="-10" y="0" width="1020" height="46" className="at-tape__band" />
        <rect x="0" y="0" width={value * 10} height="46" className="at-tape__fill" />
        {ticks}
      </svg>
      <span className="at-tape__marker" style={{ '--at-pos': `${value}%` }} aria-hidden="true" />
    </div>
  );
}

// Tailor's chalk marks on the landing sheet: drawn once on load.
const MARKS = {
  'Built dashboards for the onboarding team.': { kind: 'under', note: '+ retention', d: '0.4s' },
  'Ran A/B tests on the pricing page.': { kind: 'strike', note: 'how many?', d: '1.1s' },
  'Responsible for weekly reporting to leadership.': { kind: 'strike', note: 'show impact', d: '1.8s' },
};
function MarkedLine({ text, kind, note, d }) {
  return (
    <span className={`at-mark at-mark--${kind}`} style={{ '--d': d }}>
      {text}
      <span className="at-mark__note" aria-hidden="true">{note}</span>
    </span>
  );
}

// The candidate's resume rendered as a sheet of paper.
function ResumeSheet({ highlights = [], marks = false, compact = false, replace = {} }) {
  const r = sample.resume_data;
  const hl = (text) => {
    if (!highlights.length) return text;
    const re = new RegExp(`(${highlights.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
    return text.split(re).map((part, i) =>
      highlights.some((h) => h.toLowerCase() === part.toLowerCase()) ? (
        <mark key={i} className="at-chalkmark">{part}</mark>
      ) : (
        part
      )
    );
  };
  return (
    <article className={`at-sheet ${compact ? 'at-sheet--compact' : ''} ${marks ? 'at-sheet--marked' : ''}`} aria-label={`Resume of ${r.full_name}`}>
      <header className="at-sheet__head">
        <h3>{r.full_name}</h3>
        <p>{r.location} &nbsp;/&nbsp; {r.email}</p>
      </header>
      <p className={`at-sheet__summary ${replace.summary ? 'is-altered' : ''}`}>{replace.summary || hl(r.summary)}</p>
      {r.work_experience.map((job) => (
        <section key={job.company} className="at-sheet__job">
          <h4>
            {job.job_title}, {job.company}
            <span>{job.start_date}–{job.end_date}</span>
          </h4>
          <ul>
            {job.bullet_points.map((b) => (
              <li key={b} className={replace[b] ? 'is-altered' : ''}>{replace[b] ? replace[b] : marks && MARKS[b] ? <MarkedLine text={b} {...MARKS[b]} /> : hl(b)}</li>
            ))}
          </ul>
        </section>
      ))}
      <section className="at-sheet__job">
        <h4>Skills</h4>
        <p>{hl([...r.technical_skills, ...r.tools_and_frameworks].join(', '))}</p>
      </section>
    </article>
  );
}

/* ───────────────────────── Landing ───────────────────────── */

function Landing({ go, seeSample }) {
  const alter = sample.rewrite_report.rewritten_experiences[0].rewritten_bullets[1];
  return (
    <div className="at-landing">
      <header className="at-mast at-mast--landing">
        <Wordmark onClick={() => go('landing')} />
        <nav aria-label="Primary">
          <a href="#sittings">How a fitting works</a>
          <button className="at-btn at-btn--ink" onClick={() => go('upload')}>Begin a fitting</button>
        </nav>
      </header>

      <section className="at-hero">
        <div className="at-hero__copy">
          <h1>A resume, cut to fit the&nbsp;job.</h1>
          <p className="at-lede">
            Bring your resume and the posting you want. Resumizer measures how well they fit, alters every line
            that hangs loose, and rehearses you for the interview.
          </p>
          <div className="at-hero__actions">
            <button className="at-btn at-btn--ink at-btn--lg" onClick={() => go('upload')}>Begin a fitting</button>
            <button className="at-link" onClick={seeSample}>See a finished fitting</button>
          </div>
        </div>
        <figure className="at-hero__figure">
          <ResumeSheet marks />
          <div className="at-hero__tape">
            <Tape value={72} size="sm" label="Sample fit" />
            <span>72</span>
          </div>
          <figcaption>Noor’s resume against a Senior Product Analyst posting. Sample.</figcaption>
        </figure>
      </section>

      <section className="at-sittings" id="sittings" aria-labelledby="sittings-h">
        <h2 id="sittings-h">The fitting, in four sittings</h2>
        <ol>
          <li>
            <span className="at-numeral">I</span>
            <div>
              <h3>Measure</h3>
              <p>An ATS score against the posting, broken into keywords, experience and formatting, with every missing term named.</p>
            </div>
          </li>
          <li>
            <span className="at-numeral">II</span>
            <div>
              <h3>Alter</h3>
              <p className="at-before">{alter.original_bullet}</p>
              <p className="at-after">{alter.rewritten_bullet}</p>
            </div>
          </li>
          <li>
            <span className="at-numeral">III</span>
            <div>
              <h3>Rehearse</h3>
              <p>Six questions the interviewer is likely to ask — two behavioural, two technical, two aimed at your gaps — each with a model answer.</p>
            </div>
          </li>
          <li>
            <span className="at-numeral">IV</span>
            <div>
              <h3>Counsel</h3>
              <p>A coach that has read your resume and the posting, for the questions that come after.</p>
            </div>
          </li>
        </ol>
      </section>

      <footer className="at-foot">
        <p>Resumizer reads PDF, DOCX, TXT and Markdown files.</p>
        <button className="at-btn at-btn--ink" onClick={() => go('upload')}>Begin a fitting</button>
      </footer>
    </div>
  );
}

/* ───────────────────────── Workspace views ───────────────────────── */

function Upload({ proto }) {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState('');
  const [drag, setDrag] = useState(false);
  const input = useRef(null);
  const ready = file && jd.trim();
  return (
    <form
      className="at-upload"
      onSubmit={(e) => {
        e.preventDefault();
        if (ready) proto.run(file, jd);
      }}
    >
      <div className="at-upload__intro">
        <h1 className="at-title">Begin a fitting</h1>
        <p className="at-lede">Two things: the resume you have, and the job you want.</p>
      </div>

      <div className="at-upload__grid">
        <div className="at-field">
          <label htmlFor="at-file" className="at-field__label">Your resume</label>
          <div
            className={`at-drop ${drag ? 'is-drag' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }}
          >
            <input
              ref={input}
              id="at-file"
              type="file"
              accept=".pdf,.docx,.doc,.txt,.md"
              className="at-sr"
              onChange={(e) => e.target.files[0] && setFile(e.target.files[0])}
            />
            {file ? (
              <>
                <p className="at-drop__name">{file.name}</p>
                <p className="at-drop__meta">{(file.size / 1024).toFixed(1)} KB</p>
                <button type="button" className="at-link" onClick={() => input.current.click()}>Choose a different file</button>
              </>
            ) : (
              <>
                <p className="at-drop__name">Drop your resume here</p>
                <p className="at-drop__meta">PDF, DOCX, TXT or MD</p>
                <button type="button" className="at-btn at-btn--line" onClick={() => input.current.click()}>Choose a file</button>
              </>
            )}
          </div>
        </div>

        <div className="at-field">
          <div className="at-field__row">
            <label htmlFor="at-jd" className="at-field__label">The job posting</label>
            <button type="button" className="at-link at-link--sm" onClick={() => setJd(SAMPLE_JD)}>Use the sample posting</button>
          </div>
          <textarea
            id="at-jd"
            className="at-lined"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the full posting: responsibilities, requirements, nice-to-haves."
            rows={12}
          />
        </div>
      </div>

      <div className="at-upload__submit">
        <button type="submit" className="at-btn at-btn--ink at-btn--lg" disabled={!ready}>Begin the fitting</button>
        {!ready && <p className="at-hint">{!file ? 'Add your resume to continue.' : 'Paste the job posting to continue.'}</p>}
      </div>
    </form>
  );
}

function Stitching({ proto }) {
  const done = Math.max(0, proto.stepIndex);
  return (
    <section className="at-state" aria-live="polite">
      <h1 className="at-title">Measuring {proto.fileName}</h1>
      <p className="at-lede">This usually takes under two minutes. Stages two and three run their pieces side by side.</p>
      <svg className="at-stitch" viewBox="0 0 1000 40" preserveAspectRatio="none" aria-hidden="true">
        <line x1="0" y1="20" x2="1000" y2="20" className="at-stitch__guide" />
        <line x1="0" y1="20" x2={((done + 0.5) / PIPELINE.length) * 1000} y2="20" className="at-stitch__thread" />
      </svg>
      <ol className="at-stages">
        {[1, 2, 3].map((stage) => (
          <li key={stage}>
            <span className="at-numeral at-numeral--sm">{['I', 'II', 'III'][stage - 1]}</span>
            <ul>
              {PIPELINE.filter((p) => p.stage === stage).map((p) => {
                const i = PIPELINE.indexOf(p);
                const state = i < done ? 'done' : i === done ? 'now' : 'wait';
                return (
                  <li key={p.id} className={`is-${state}`}>
                    {p.label}
                    <span className="at-sr">{state === 'done' ? ' — done' : state === 'now' ? ' — in progress' : ' — waiting'}</span>
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}

function ErrorSlip({ proto }) {
  return (
    <section className="at-state" role="alert">
      <div className="at-slip">
        <h1>{proto.error?.title}</h1>
        <p>{proto.error?.body}</p>
        <button className="at-btn at-btn--ink" onClick={() => { proto.forceState('empty'); proto.setView('upload'); }}>
          Choose another file
        </button>
      </div>
    </section>
  );
}

function EmptyFitting({ proto }) {
  return (
    <section className="at-state at-state--empty">
      <h1 className="at-title">No fitting yet</h1>
      <p className="at-lede">Bring a resume and a job posting, and this page will hold your measurements.</p>
      <button className="at-btn at-btn--ink at-btn--lg" onClick={() => proto.setView('upload')}>Begin a fitting</button>
    </section>
  );
}

function Measure({ data }) {
  const a = data.analysis.ats_score;
  const g = data.analysis.skill_gap;
  const [showAll, setShowAll] = useState(false);
  return (
    <div className="at-measure">
      <div className="at-measure__main">
        <section className="at-score" aria-labelledby="at-score-h">
          <h2 id="at-score-h" className="at-sr">Overall fit</h2>
          <p className="at-score__num">{a.overall_score}<span>/100</span></p>
          <p className="at-score__verdict">{verdict(a.overall_score)}</p>
          <Tape value={a.overall_score} label="Overall ATS match" />
        </section>

        <section className="at-subs" aria-label="Score breakdown">
          {[
            ['Keywords', a.keyword_match_score],
            ['Experience', a.experience_match_score],
            ['Formatting', a.formatting_score],
          ].map(([l, v]) => (
            <div key={l} className="at-sub">
              <p><span>{l}</span><strong>{v}</strong></p>
              <Tape value={v} size="sm" label={l} />
            </div>
          ))}
        </section>

        <p className="at-summary">{a.breakdown_summary}</p>

        <section className="at-kw" aria-labelledby="at-kw-h">
          <h2 id="at-kw-h" className="at-h2">Keywords</h2>
          <div className="at-kw__cols">
            <div>
              <h3>In your resume</h3>
              <ul className="at-words">{a.matched_keywords.map((k) => <li key={k}>{k}</li>)}</ul>
            </div>
            <div>
              <h3>Asked for, not found</h3>
              <ul className="at-words at-words--missing">{a.missing_keywords.map((k) => <li key={k}>{k}</li>)}</ul>
            </div>
          </div>
        </section>

        <section aria-labelledby="at-gap-h">
          <h2 id="at-gap-h" className="at-h2">Skills</h2>
          <table className="at-table">
            <thead>
              <tr><th scope="col"><span className="at-sr">Type</span></th><th scope="col">You have</th><th scope="col">The role wants</th></tr>
            </thead>
            <tbody>
              <tr><th scope="row">Technical</th><td>{g.matched_hard_skills.join(', ')}</td><td className="is-missing">{g.missing_hard_skills.join(', ')}</td></tr>
              <tr><th scope="row">Working style</th><td>{g.matched_soft_skills.join(', ')}</td><td className="is-missing">{g.missing_soft_skills.join(', ')}</td></tr>
            </tbody>
          </table>
        </section>

        <section aria-labelledby="at-first-h">
          <h2 id="at-first-h" className="at-h2">Alter these first</h2>
          <ol className="at-priority">
            {g.priority_skill_recommendations.slice(0, showAll ? undefined : 2).map((r) => <li key={r}>{r}</li>)}
          </ol>
          {!showAll && (
            <button className="at-link" onClick={() => setShowAll(true)}>Show all {g.priority_skill_recommendations.length}</button>
          )}
        </section>
      </div>

      <aside className="at-measure__aside" aria-label="Your resume with matched keywords marked">
        <p className="at-aside-note">Matched keywords are marked in chalk.</p>
        <ResumeSheet highlights={a.matched_keywords} compact />
      </aside>
    </div>
  );
}

function Alter({ data }) {
  const rw = data.analysis.rewrite_report;
  const all = rw.rewritten_experiences.flatMap((e) => e.rewritten_bullets);
  const [accepted, setAccepted] = useState(() => new Set());
  const replace = {};
  all.forEach((b) => { if (accepted.has(b.rewritten_bullet)) replace[b.original_bullet] = b.rewritten_bullet; });
  if (accepted.has('summary')) replace.summary = rw.tailored_summary;
  const [copied, setCopied] = useState(null);
  const toggle = (t) =>
    setAccepted((s) => {
      const n = new Set(s);
      n.has(t) ? n.delete(t) : n.add(t);
      return n;
    });
  const copy = (t) => {
    navigator.clipboard?.writeText(t);
    setCopied(t);
    setTimeout(() => setCopied(null), 1600);
  };
  return (
    <div className="at-alter-layout">
    <div className="at-alter">
      <header className="at-alter__head">
        <h2 className="at-h2">Alterations</h2>
        <p className="at-count" aria-live="polite">{accepted.size} of {all.length + 1} accepted</p>
      </header>

      <section className="at-alter__summary">
        <h3>Summary, retailored</h3>
        <p className="at-after at-after--lg">{rw.tailored_summary}</p>
        <div className="at-alter__actions">
          <button className="at-link" onClick={() => copy(rw.tailored_summary)}>{copied === rw.tailored_summary ? 'Copied' : 'Copy'}</button>
          <button className={`at-btn ${accepted.has('summary') ? 'at-btn--ink' : 'at-btn--line'}`} aria-pressed={accepted.has('summary')} onClick={() => toggle('summary')}>
            {accepted.has('summary') ? 'Accepted' : 'Accept'}
          </button>
        </div>
      </section>

      {rw.rewritten_experiences.map((exp) => (
        <section key={exp.company} className="at-alter__role">
          <h3>{exp.job_title}, {exp.company}</h3>
          <ol>
            {exp.rewritten_bullets.map((b) => {
              const on = accepted.has(b.rewritten_bullet);
              return (
                <li key={b.original_bullet} className={on ? 'is-accepted' : ''}>
                  <p className="at-before">{b.original_bullet}</p>
                  <p className="at-after">{b.rewritten_bullet}</p>
                  <div className="at-alter__meta">
                    <p className="at-margin">
                      {b.added_keywords.map((k) => <span key={k}>+ {k}</span>)}
                    </p>
                    <div className="at-alter__actions">
                      <button className="at-link" onClick={() => copy(b.rewritten_bullet)}>{copied === b.rewritten_bullet ? 'Copied' : 'Copy'}</button>
                      <button className={`at-btn ${on ? 'at-btn--ink' : 'at-btn--line'}`} aria-pressed={on} onClick={() => toggle(b.rewritten_bullet)}>
                        {on ? 'Accepted' : 'Accept'}
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      ))}

      <aside className="at-concept">
        <p><strong>Concept, not yet built:</strong> download the altered resume as a PDF or DOCX. Resumizer currently returns rewrites to copy by hand.</p>
      </aside>
    </div>
    <aside className="at-measure__aside" aria-label="Your resume with accepted alterations">
      <p className="at-aside-note">Your resume with accepted alterations sewn in.</p>
      <ResumeSheet compact replace={replace} />
    </aside>
    </div>
  );
}

const TYPE_NAMES = { behavioral: 'Behavioural', technical: 'Technical', gap_focused: 'About your gaps' };

function Rehearse({ data }) {
  const qs = data.analysis.interview_prep.questions;
  const [filter, setFilter] = useState('all');
  const list = filter === 'all' ? qs : qs.filter((q) => q.question_type === filter);
  const [i, setI] = useState(0);
  const [reveal, setReveal] = useState(0);
  const q = list[Math.min(i, list.length - 1)];
  const goTo = (n) => { setI(n); setReveal(0); };

  if (!qs.length) {
    return (
      <section className="at-state at-state--empty">
        <h2 className="at-title">No questions this time</h2>
        <p className="at-lede">The interview agent didn’t return questions for this fitting. Run the fitting again, or ask for practice questions in Counsel.</p>
      </section>
    );
  }

  return (
    <div className="at-rehearse">
      <div className="at-filter" role="tablist" aria-label="Question type">
        {['all', 'behavioral', 'technical', 'gap_focused'].map((f) => (
          <button key={f} role="tab" aria-selected={filter === f} className={filter === f ? 'is-on' : ''} onClick={() => { setFilter(f); goTo(0); }}>
            {f === 'all' ? 'All six' : TYPE_NAMES[f]}
          </button>
        ))}
      </div>

      <div className="at-rehearse__grid">
        <article className="at-question" aria-live="polite">
          <p className="at-question__count">Question {Math.min(i, list.length - 1) + 1} of {list.length} &nbsp;/&nbsp; {TYPE_NAMES[q.question_type]}</p>
          <h2>{q.question}</h2>
          <p className="at-question__why">{q.context_or_reason}</p>

          {reveal >= 1 && (
            <div className="at-reveal">
              <h3>How to shape your answer</h3>
              <p>{q.star_guide}</p>
            </div>
          )}
          {reveal >= 2 && (
            <div className="at-reveal at-reveal--answer">
              <h3>A model answer</h3>
              <p>{q.sample_answer}</p>
            </div>
          )}
          <div className="at-question__actions">
            {reveal < 2 && (
              <button className="at-btn at-btn--line" onClick={() => setReveal(reveal + 1)}>
                {reveal === 0 ? 'Show how to answer' : 'Show a model answer'}
              </button>
            )}
            <span className="at-spacer" />
            <button className="at-link" disabled={i === 0} onClick={() => goTo(i - 1)}>Previous</button>
            <button className="at-btn at-btn--ink" disabled={i >= list.length - 1} onClick={() => goTo(i + 1)}>Next question</button>
          </div>
        </article>

        <nav className="at-qindex" aria-label="All questions">
          <ol>
            {list.map((qq, n) => (
              <li key={qq.question}>
                <button className={n === i ? 'is-on' : ''} aria-current={n === i} onClick={() => goTo(n)}>{qq.question}</button>
              </li>
            ))}
          </ol>
        </nav>
      </div>
    </div>
  );
}

function Counsel() {
  const coach = useCoach(
    'I’ve read your resume and the Fieldnote posting. Ask me what to fix first, how to handle a gap, or how to answer a question you’re dreading.'
  );
  const [text, setText] = useState('');
  return (
    <div className="at-counsel">
      <div className="at-letters" aria-live="polite">
        {coach.messages.map((m, n) => (
          <div key={n} className={`at-letter at-letter--${m.role}`}>
            <p className="at-letter__from">{m.role === 'user' ? 'You' : 'Your coach'}</p>
            <div className="at-letter__body"><ReactMarkdown>{m.content}</ReactMarkdown></div>
          </div>
        ))}
        {coach.thinking && <p className="at-letter__wait">Your coach is writing…</p>}
      </div>
      <div className="at-suggest">
        {COACH_SUGGESTIONS.map((s) => (
          <button key={s} className="at-link" onClick={() => coach.send(s)}>{s}</button>
        ))}
      </div>
      <form className="at-compose" onSubmit={(e) => { e.preventDefault(); coach.send(text); setText(''); }}>
        <label htmlFor="at-ask" className="at-sr">Ask your coach</label>
        <input id="at-ask" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask your coach anything about this application" />
        <button className="at-btn at-btn--ink" disabled={!text.trim() || coach.thinking}>Send</button>
      </form>
    </div>
  );
}

function Archive({ proto }) {
  const rows = [
    ['Senior Product Analyst', 'Fieldnote', 72, 'Today'],
    ['Product Analyst II', 'Tidewater Books', 64, '12 Oct'],
    ['Growth Analyst', 'Orbita Transit', 58, '30 Sep'],
  ];
  return (
    <div className="at-archive">
      <aside className="at-concept">
        <p><strong>Concept, not yet built:</strong> Resumizer has no accounts or saved history yet. This shows how past fittings could be kept.</p>
      </aside>
      <h2 className="at-h2">Past fittings</h2>
      <ul>
        {rows.map(([role, co, s, d]) => (
          <li key={role}>
            <button onClick={() => proto.setView('match')}>
              <span className="at-archive__role">{role}</span>
              <span className="at-archive__co">{co}</span>
              <span className="at-archive__score">{s}</span>
              <span className="at-archive__date">{d}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ───────────────────────── Shell ───────────────────────── */

export default function AtelierApp() {
  useFonts(FONTS);
  usePageColors('#ECEAF1', '#1A1730', 'Resumizer — Option A, Editorial Atelier');
  const proto = usePrototype();
  const { view, setView, status, data } = proto;

  const seeSample = () => { proto.forceState('ready'); setView('match'); };

  if (view === 'landing') {
    return (
      <div className="at-root">
        <Landing go={setView} seeSample={seeSample} />
        <PrototypeBar concept="A" proto={proto} />
      </div>
    );
  }

  let body;
  const needsData = ['match', 'rewrite', 'interview', 'coach'].includes(view);
  if (view === 'history') body = <Archive proto={proto} />;
  else if (status === 'loading') body = <Stitching proto={proto} />;
  else if (status === 'error') body = <ErrorSlip proto={proto} />;
  else if (view === 'upload') body = <Upload proto={proto} />;
  else if (needsData && !data) body = <EmptyFitting proto={proto} />;
  else if (view === 'match') body = <Measure data={data} />;
  else if (view === 'rewrite') body = <Alter data={data} />;
  else if (view === 'interview') body = <Rehearse data={data} />;
  else if (view === 'coach') body = <Counsel />;

  return (
    <div className="at-root">
      <header className="at-mast">
        <Wordmark onClick={() => setView('landing')} />
        <nav className="at-sittings-nav" aria-label="Fitting">
          {SITTINGS.map((s) => (
            <button
              key={s.id}
              className={view === s.id ? 'is-on' : ''}
              aria-current={view === s.id ? 'page' : undefined}
              onClick={() => setView(s.id)}
            >
              <span className="at-numeral at-numeral--xs" aria-hidden="true">{s.numeral}</span>
              {s.name}
            </button>
          ))}
        </nav>
        <div className="at-mast__end">
          <button className={`at-link ${view === 'history' ? 'is-on' : ''}`} onClick={() => setView('history')}>Past fittings</button>
          <button className="at-btn at-btn--line" onClick={() => { proto.forceState('empty'); setView('upload'); }}>New fitting</button>
        </div>
      </header>

      {data && view !== 'history' && view !== 'upload' && (
        <p className="at-context">
          Fitting for <em>{data.analysis.resume_data.full_name}</em> — Senior Product Analyst, Fieldnote
        </p>
      )}

      <main className="at-main" key={view}>{body}</main>
      <PrototypeBar concept="A" proto={proto} />
    </div>
  );
}
