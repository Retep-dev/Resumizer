import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { usePrototype, useFonts, usePageColors, useCoach, useReducedMotion } from '../usePrototype';
import { PIPELINE, SAMPLE_JD, SAMPLE_RESPONSE, COACH_SUGGESTIONS } from '../data';
import PrototypeBar from '../PrototypeBar';
import './lab.css';

const FONTS =
  'https://fonts.googleapis.com/css2?family=Anybody:ital,wdth,wght@0,50..150,300..900;1,50..150,300..900&family=Atkinson+Hyperlegible:wght@400;700&display=swap';
const sample = SAMPLE_RESPONSE.analysis;

const TABS = [
  { id: 'match', label: 'Score' },
  { id: 'rewrite', label: 'Remix' },
  { id: 'interview', label: 'Flashcards' },
  { id: 'coach', label: 'Coach' },
];

/* ───────────── Stretchy type: signature interaction ───────────── */

function StretchType({ text, as: Tag = 'h1', className = '' }) {
  const ref = useRef(null);
  const reduced = useReducedMotion();
  const [x, setX] = useState(null);
  useEffect(() => {
    if (reduced) return;
    const el = ref.current?.closest('[data-stretch-zone]') || ref.current;
    const move = (e) => setX(e.clientX);
    const leave = () => setX(null);
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerleave', leave);
    return () => { el.removeEventListener('pointermove', move); el.removeEventListener('pointerleave', leave); };
  }, [reduced]);

  const letters = useRef([]);
  const widthFor = (i) => {
    if (x == null || !letters.current[i]) return 100;
    const r = letters.current[i].getBoundingClientRect();
    const d = Math.abs(r.left + r.width / 2 - x);
    return Math.round(70 + 80 * Math.max(0, 1 - d / 260));
  };
  let n = 0;
  return (
    <Tag ref={ref} className={`lb-stretch ${className}`} aria-label={text}>
      {text.split(' ').map((word, w) => (
        <React.Fragment key={w}>
        {w > 0 && ' '}
        <span className="lb-stretch__word" aria-hidden="true">
          {word.split('').map((ch) => {
            const i = n++;
            return (
              <span key={i} ref={(el) => (letters.current[i] = el)} style={{ fontVariationSettings: `'wdth' ${widthFor(i)}, 'wght' 860` }}>
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

function Sticker({ children, tone = 'yellow', tilt = 0, className = '', as: Tag = 'span', ...rest }) {
  return (
    <Tag className={`lb-sticker lb-sticker--${tone} ${className}`} style={{ '--tilt': `${tilt}deg` }} {...rest}>
      {children}
    </Tag>
  );
}

// Before/after wipe for one bullet.
function Wipe({ before, after, label }) {
  const [p, setP] = useState(100);
  return (
    <div className="lb-wipe">
      <div className="lb-wipe__stage" style={{ '--p': `${p}%` }}>
        <p className="lb-wipe__before" aria-hidden={p > 50}>{before}</p>
        <p className="lb-wipe__after" aria-hidden={p <= 50}>{after}</p>
        <span className="lb-wipe__handle" aria-hidden="true" />
      </div>
      <div className="lb-wipe__ctrl">
        <button onClick={() => setP(0)} className={p === 0 ? 'is-on' : ''}>Before</button>
        <input type="range" min="0" max="100" value={p} onChange={(e) => setP(+e.target.value)} aria-label={`Compare original and rewrite${label ? ` for ${label}` : ''}`} />
        <button onClick={() => setP(100)} className={p === 100 ? 'is-on' : ''}>After</button>
      </div>
    </div>
  );
}

/* ───────────── Landing ───────────── */

function Landing({ go, seeSample }) {
  const b = sample.rewrite_report.rewritten_experiences[0].rewritten_bullets[0];
  return (
    <div className="lb-landing">
      <header className="lb-nav">
        <button className="lb-wordmark" onClick={() => go('landing')}>Resumizer</button>
        <button className="lb-btn lb-btn--ink" onClick={() => go('upload')}>Start a remix</button>
      </header>

      <section className="lb-hero" data-stretch-zone>
        <StretchType text="Remix your resume for the job you want." />
        <div className="lb-hero__row">
          <p className="lb-hero__lede">
            Drop in your resume and a job posting. Get a match score, rewritten bullets, flashcards for the interview,
            and a coach who has read both.
          </p>
          <div className="lb-hero__cta">
            <button className="lb-btn lb-btn--blue lb-btn--lg" onClick={() => go('upload')}>Start a remix</button>
            <button className="lb-btn lb-btn--line lb-btn--lg" onClick={seeSample}>Peek at a finished one</button>
          </div>
        </div>
        <div className="lb-hero__stickers" aria-hidden="true">
          <Sticker tone="yellow" tilt={-8} className="lb-sticker--score"><b>72</b><span>match</span></Sticker>
          <Sticker tone="pink" tilt={6}>+ Experimentation platform</Sticker>
          <Sticker tone="blue" tilt={-3}>6 flashcards ready</Sticker>
        </div>
      </section>

      <section className="lb-passes" aria-labelledby="lb-passes-h">
        <h2 id="lb-passes-h">Three passes through the press</h2>
        <div className="lb-overprint" aria-hidden="true">
          <span className="lb-ink lb-ink--pink" />
          <span className="lb-ink lb-ink--yellow" />
          <span className="lb-ink lb-ink--blue" />
        </div>
        <ol>
          <li><span className="lb-pass lb-pass--pink">1</span><h3>Read</h3><p>Your resume is parsed into roles, bullets and skills.</p></li>
          <li><span className="lb-pass lb-pass--yellow">2</span><h3>Match</h3><p>Scored against the posting, with every missing keyword and skill named.</p></li>
          <li><span className="lb-pass lb-pass--blue">3</span><h3>Remix</h3><p>Bullets rewritten with numbers, plus six interview questions to practise.</p></li>
        </ol>
      </section>

      <section className="lb-demo" aria-labelledby="lb-demo-h">
        <h2 id="lb-demo-h">Drag to see a bullet get remixed</h2>
        <Wipe before={b.original_bullet} after={b.rewritten_bullet} label="sample bullet" />
      </section>

      <footer className="lb-foot">
        <StretchType as="p" text="Your turn." className="lb-foot__big" />
        <button className="lb-btn lb-btn--blue lb-btn--lg" onClick={() => go('upload')}>Start a remix</button>
        <p className="lb-foot__small">Reads PDF, DOCX, TXT and Markdown.</p>
      </footer>
    </div>
  );
}

/* ───────────── Workspace views ───────────── */

function Upload({ proto }) {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState('');
  const [drag, setDrag] = useState(false);
  const input = useRef(null);
  const ready = file && jd.trim();
  return (
    <form className="lb-upload" onSubmit={(e) => { e.preventDefault(); if (ready) proto.run(file, jd); }}>
      <h1 className="lb-h1">Load the press</h1>
      <div className="lb-upload__grid">
        <div
          className={`lb-bed ${drag ? 'is-drag' : ''} ${file ? 'has-file' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); e.dataTransfer.files[0] && setFile(e.dataTransfer.files[0]); }}
        >
          <label htmlFor="lb-file" className="lb-bed__label">Your resume</label>
          <input ref={input} id="lb-file" type="file" accept=".pdf,.docx,.doc,.txt,.md" className="lb-sr" onChange={(e) => e.target.files[0] && setFile(e.target.files[0])} />
          {file ? (
            <>
              <Sticker tone="yellow" tilt={-4} className="lb-bed__file">{file.name}</Sticker>
              <button type="button" className="lb-textbtn" onClick={() => input.current.click()}>Swap file</button>
            </>
          ) : (
            <>
              <p className="lb-bed__big">Drop it on the bed</p>
              <p>PDF, DOCX, TXT or MD</p>
              <button type="button" className="lb-btn lb-btn--ink" onClick={() => input.current.click()}>Choose a file</button>
            </>
          )}
        </div>
        <div className="lb-ticket">
          <div className="lb-ticket__head">
            <label htmlFor="lb-jd">The job posting</label>
            <button type="button" className="lb-textbtn" onClick={() => setJd(SAMPLE_JD)}>Paste a sample</button>
          </div>
          <textarea id="lb-jd" rows={12} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the whole thing. The more of it, the better the match." />
        </div>
      </div>
      <div className="lb-upload__go">
        <button className="lb-btn lb-btn--pink lb-btn--lg" disabled={!ready}>Start the print run</button>
        {!ready && <span>{!file ? 'Needs a resume.' : 'Needs a job posting.'}</span>}
      </div>
    </form>
  );
}

function Press({ proto }) {
  const s = Math.max(0, proto.stepIndex);
  const stage = PIPELINE[Math.min(s, PIPELINE.length - 1)].stage;
  return (
    <section className="lb-press" aria-live="polite">
      <div className={`lb-poster lb-poster--s${stage}`} aria-hidden="true">
        <span className="lb-poster__a" />
        <span className="lb-poster__b" />
        <span className="lb-poster__c">72</span>
      </div>
      <div>
        <h1 className="lb-h1">Printing…</h1>
        <p className="lb-lede">Pass {stage} of 3. About two minutes for a full run.</p>
        <ul className="lb-checks">
          {PIPELINE.map((p, i) => (
            <li key={p.id} className={i < s ? 'is-done' : i === s ? 'is-now' : ''}>
              {p.label}
              <span className="lb-sr">{i < s ? ', done' : i === s ? ', in progress' : ', waiting'}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Misprint({ proto }) {
  return (
    <section className="lb-misprint" role="alert">
      <p className="lb-misprint__word" aria-hidden="true">Misprint</p>
      <h1 className="lb-h2">{proto.error?.title}</h1>
      <p className="lb-lede">{proto.error?.body}</p>
      <button className="lb-btn lb-btn--ink lb-btn--lg" onClick={() => { proto.forceState('empty'); proto.setView('upload'); }}>Load another file</button>
    </section>
  );
}

function Empty({ proto }) {
  return (
    <section className="lb-empty">
      <div className="lb-empty__plate" aria-hidden="true" />
      <h1 className="lb-h1">Nothing on the press yet</h1>
      <p className="lb-lede">Load a resume and a job posting to print your first remix.</p>
      <button className="lb-btn lb-btn--blue lb-btn--lg" onClick={() => proto.setView('upload')}>Load the press</button>
    </section>
  );
}

function Score({ data }) {
  const a = data.analysis.ats_score;
  const g = data.analysis.skill_gap;
  const verdict = a.overall_score >= 75 ? 'Strong match.' : a.overall_score >= 50 ? 'Good bones. Needs a remix.' : 'Big gaps. Remix before you apply.';
  return (
    <div className="lb-score">
      <section className="lb-score__hero">
        <p className="lb-bignum" aria-label={`Match score ${a.overall_score} out of 100`}>
          <span aria-hidden="true">{a.overall_score}</span>
        </p>
        <div className="lb-score__side">
          <p className="lb-verdict">{verdict}</p>
          <p>{a.breakdown_summary}</p>
          <ul className="lb-strips">
            {[['Keywords', a.keyword_match_score, 'pink'], ['Experience', a.experience_match_score, 'blue'], ['Formatting', a.formatting_score, 'green']].map(([l, v, t]) => (
              <li key={l}>
                <span>{l}</span>
                <span className={`lb-strip lb-strip--${t}`}><i style={{ width: `${v}%` }} /></span>
                <b>{v}</b>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="lb-board" aria-labelledby="lb-kw-h">
        <h2 id="lb-kw-h" className="lb-h2">Keyword stickers</h2>
        <div className="lb-board__cols">
          <div>
            <h3>Already on your resume</h3>
            <ul>{a.matched_keywords.map((k, i) => <li key={k}><Sticker tone="yellow" tilt={(i % 3) - 1.5}>{k}</Sticker></li>)}</ul>
          </div>
          <div>
            <h3>Wanted, missing</h3>
            <ul>{a.missing_keywords.map((k, i) => <li key={k}><Sticker tone="pinkline" tilt={((i + 1) % 3) - 1.5}>{k}</Sticker></li>)}</ul>
          </div>
        </div>
      </section>

      <section className="lb-gaps" aria-labelledby="lb-gap-h">
        <h2 id="lb-gap-h" className="lb-h2">Skills: got it, get it</h2>
        <div className="lb-gaps__grid">
          <div className="lb-card lb-card--got">
            <h3>Got it</h3>
            <p>{[...g.matched_hard_skills, ...g.matched_soft_skills].join(', ')}</p>
          </div>
          <div className="lb-card lb-card--get">
            <h3>Get it</h3>
            <p>{[...g.missing_hard_skills, ...g.missing_soft_skills].join(', ')}</p>
          </div>
        </div>
      </section>

      <section aria-labelledby="lb-todo-h">
        <h2 id="lb-todo-h" className="lb-h2">Do these next, in order</h2>
        <ol className="lb-todo">
          {g.priority_skill_recommendations.map((r) => <li key={r}>{r}</li>)}
        </ol>
      </section>
    </div>
  );
}

function Remix({ data }) {
  const rw = data.analysis.rewrite_report;
  const [kept, setKept] = useState(() => new Set());
  const [copied, setCopied] = useState(null);
  const total = rw.rewritten_experiences.reduce((n, e) => n + e.rewritten_bullets.length, 0);
  const copy = (t) => { navigator.clipboard?.writeText(t); setCopied(t); setTimeout(() => setCopied(null), 1500); };
  return (
    <div className="lb-remix">
      <div className="lb-remix__top">
        <h1 className="lb-h1">Remix</h1>
        <Sticker tone="blue" tilt={2} aria-live="polite">{kept.size} of {total} kept</Sticker>
      </div>
      <section className="lb-card lb-card--summary">
        <h2>New summary</h2>
        <p>{rw.tailored_summary}</p>
        <button className="lb-textbtn" onClick={() => copy(rw.tailored_summary)}>{copied === rw.tailored_summary ? 'Copied' : 'Copy summary'}</button>
      </section>
      {rw.rewritten_experiences.map((exp) => (
        <section key={exp.company} className="lb-remix__role">
          <h2 className="lb-h2">{exp.job_title} <span>at {exp.company}</span></h2>
          {exp.rewritten_bullets.map((b) => {
            const on = kept.has(b.rewritten_bullet);
            return (
              <article key={b.original_bullet} className={`lb-card lb-remix__item ${on ? 'is-kept' : ''}`}>
                <Wipe before={b.original_bullet} after={b.rewritten_bullet} label={b.star_action} />
                <div className="lb-remix__meta">
                  <div className="lb-remix__tags">
                    <Sticker tone="yellow" tilt={-2}>{b.star_result}</Sticker>
                    {b.added_keywords.map((k) => <Sticker key={k} tone="pinkline">+ {k}</Sticker>)}
                  </div>
                  <div className="lb-remix__actions">
                    <button className="lb-textbtn" onClick={() => copy(b.rewritten_bullet)}>{copied === b.rewritten_bullet ? 'Copied' : 'Copy'}</button>
                    <button className={`lb-btn ${on ? 'lb-btn--green' : 'lb-btn--line'}`} aria-pressed={on} onClick={() => setKept((s) => { const n = new Set(s); n.has(b.rewritten_bullet) ? n.delete(b.rewritten_bullet) : n.add(b.rewritten_bullet); return n; })}>
                      {on ? 'Kept' : 'Keep this'}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      ))}
      <p className="lb-concept"><b>Concept, not yet built:</b> print the kept bullets straight into a downloadable resume.</p>
    </div>
  );
}

const QT = { behavioral: 'Behavioural', technical: 'Technical', gap_focused: 'Gap' };

function Flashcards({ data }) {
  const all = data.analysis.interview_prep.questions;
  const [filter, setFilter] = useState('all');
  const deck = filter === 'all' ? all : all.filter((q) => q.question_type === filter);
  const [i, setI] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [marks, setMarks] = useState({});
  const q = deck[Math.min(i, deck.length - 1)];
  const go = (n) => { setI(n); setFlipped(false); };
  const mark = (v) => { setMarks((m) => ({ ...m, [q.question]: v })); if (i < deck.length - 1) go(i + 1); };
  const got = Object.values(marks).filter((v) => v === 'got').length;
  const again = Object.values(marks).filter((v) => v === 'again').length;

  if (!all.length) return <Empty proto={{ setView: () => {} }} />;
  return (
    <div className="lb-flash">
      <div className="lb-flash__top">
        <h1 className="lb-h1">Flashcards</h1>
        <div className="lb-filters" role="group" aria-label="Filter by question type">
          {['all', 'behavioral', 'technical', 'gap_focused'].map((f) => (
            <button key={f} aria-pressed={filter === f} className={filter === f ? 'is-on' : ''} onClick={() => { setFilter(f); go(0); }}>
              {f === 'all' ? 'All' : QT[f]}
            </button>
          ))}
        </div>
      </div>

      <div className="lb-tally" aria-live="polite">
        <Sticker tone="green" tilt={-2}>Got it: {got}</Sticker>
        <Sticker tone="pinkline" tilt={2}>Again: {again}</Sticker>
        <span>Card {Math.min(i, deck.length - 1) + 1} of {deck.length}</span>
      </div>

      <div className="lb-deck">
        <span className="lb-deck__under" aria-hidden="true" />
        <span className="lb-deck__under lb-deck__under--2" aria-hidden="true" />
        <button className={`lb-flashcard ${flipped ? 'is-flipped' : ''}`} onClick={() => setFlipped((f) => !f)} aria-pressed={flipped}>
          <span className="lb-flashcard__face lb-flashcard__front">
            <span className={`lb-qtype lb-qtype--${q.question_type}`}>{QT[q.question_type]}</span>
            <span className="lb-flashcard__q">{q.question}</span>
            <span className="lb-flashcard__hint">Tap to flip</span>
          </span>
          <span className="lb-flashcard__face lb-flashcard__back">
            <span className="lb-flashcard__label">Shape it like this</span>
            <span className="lb-flashcard__star">{q.star_guide}</span>
            <span className="lb-flashcard__label">Sounds like this</span>
            <span className="lb-flashcard__ans">{q.sample_answer}</span>
          </span>
        </button>
      </div>

      <div className="lb-flash__ctrl">
        <button className="lb-textbtn" disabled={i === 0} onClick={() => go(i - 1)}>Back</button>
        <button className="lb-btn lb-btn--line" onClick={() => mark('again')}>Practise again</button>
        <button className="lb-btn lb-btn--green" onClick={() => mark('got')}>Got it</button>
      </div>
      <p className="lb-why"><b>Why they’ll ask:</b> {q.context_or_reason}</p>
    </div>
  );
}

function Coach() {
  const c = useCoach('Hi Noor. I’ve read your resume and the Fieldnote posting. What do you want to work on?');
  const [text, setText] = useState('');
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }); }, [c.messages, c.thinking]);
  return (
    <div className="lb-coach">
      <h1 className="lb-h1">Coach</h1>
      <div className="lb-coach__log" aria-live="polite">
        {c.messages.map((m, n) => (
          <div key={n} className={`lb-slip lb-slip--${m.role}`} style={{ '--tilt': `${n % 2 ? 0.8 : -0.8}deg` }}>
            <ReactMarkdown>{m.content}</ReactMarkdown>
          </div>
        ))}
        {c.thinking && <div className="lb-slip lb-slip--assistant lb-slip--wait">Inking a reply…</div>}
        <div ref={end} />
      </div>
      <div className="lb-coach__suggest">
        {COACH_SUGGESTIONS.map((s, i) => (
          <Sticker key={s} as="button" tone={['yellow', 'pinkline', 'blueline'][i]} tilt={i - 1} onClick={() => c.send(s)}>{s}</Sticker>
        ))}
      </div>
      <form className="lb-coach__form" onSubmit={(e) => { e.preventDefault(); c.send(text); setText(''); }}>
        <label htmlFor="lb-ask" className="lb-sr">Ask the coach</label>
        <input id="lb-ask" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask anything about this application" />
        <button className="lb-btn lb-btn--blue" disabled={!text.trim() || c.thinking}>Send</button>
      </form>
    </div>
  );
}

function Archive({ proto }) {
  const rows = [['Senior Product Analyst', 'Fieldnote', 72, 'pink'], ['Product Analyst II', 'Tidewater Books', 64, 'yellow'], ['Growth Analyst', 'Orbita Transit', 58, 'blue']];
  return (
    <div className="lb-archive">
      <h1 className="lb-h1">Past prints</h1>
      <p className="lb-concept"><b>Concept, not yet built:</b> Resumizer doesn’t save runs or have accounts yet. This is how a shelf of past remixes could look.</p>
      <ul>
        {rows.map(([r, c, s, t], i) => (
          <li key={r}>
            <button className={`lb-print lb-print--${t}`} style={{ '--tilt': `${(i - 1) * 2}deg` }} onClick={() => proto.setView('match')}>
              <b>{s}</b><span>{r}</span><span>{c}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ───────────── Shell ───────────── */

export default function LabApp() {
  useFonts(FONTS);
  usePageColors('#EEF0FF', '#1D1B4C', 'Resumizer — Option C, Creative Career Lab');
  const proto = usePrototype();
  const { view, setView, status, data } = proto;
  const seeSample = () => { proto.forceState('ready'); setView('match'); };

  if (view === 'landing') {
    return (
      <div className="lb-root">
        <Landing go={setView} seeSample={seeSample} />
        <PrototypeBar concept="C" proto={proto} />
      </div>
    );
  }

  const needsData = ['match', 'rewrite', 'interview', 'coach'].includes(view);
  let body;
  if (view === 'history') body = <Archive proto={proto} />;
  else if (status === 'loading') body = <Press proto={proto} />;
  else if (status === 'error') body = <Misprint proto={proto} />;
  else if (view === 'upload') body = <Upload proto={proto} />;
  else if (needsData && !data) body = <Empty proto={proto} />;
  else if (view === 'match') body = <Score data={data} />;
  else if (view === 'rewrite') body = <Remix data={data} />;
  else if (view === 'interview') body = <Flashcards data={data} />;
  else if (view === 'coach') body = <Coach />;

  return (
    <div className="lb-root">
      <header className="lb-appbar">
        <button className="lb-wordmark" onClick={() => setView('landing')}>Resumizer</button>
        <nav className="lb-tabs" aria-label="Workspace">
          {TABS.map((t, i) => (
            <button key={t.id} className={`lb-tab lb-tab--${i} ${view === t.id ? 'is-on' : ''}`} aria-current={view === t.id ? 'page' : undefined} onClick={() => setView(t.id)}>
              {t.label}
            </button>
          ))}
          <button className={`lb-tab lb-tab--arch ${view === 'history' ? 'is-on' : ''}`} onClick={() => setView('history')}>Past prints</button>
        </nav>
        <button className="lb-btn lb-btn--ink lb-appbar__new" onClick={() => { proto.forceState('empty'); setView('upload'); }}>New remix</button>
      </header>
      <main className="lb-main" key={view + status}>{body}</main>
      <PrototypeBar concept="C" proto={proto} />
    </div>
  );
}
