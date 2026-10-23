import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { usePrototype, useFonts, usePageColors, useCoach } from '../usePrototype';
import { PIPELINE, SAMPLE_JD, SAMPLE_RESPONSE, COACH_SUGGESTIONS } from '../data';
import PrototypeBar from '../PrototypeBar';
import './studio.css';

const FONTS = 'https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,300..900&display=swap';
const sample = SAMPLE_RESPONSE.analysis;

const NAV = [
  { id: 'match', label: 'Match report', icon: 'M4 12a8 8 0 1 0 16 0a8 8 0 1 0-16 0M8 12a4 4 0 1 0 8 0a4 4 0 1 0-8 0' },
  { id: 'rewrite', label: 'Rewrites', icon: 'M4 7h10M4 12h16M4 17h8M17 4l3 3-3 3' },
  { id: 'interview', label: 'Interview prep', icon: 'M5 5h14v10H9l-4 4z' },
  { id: 'coach', label: 'Career coach', icon: 'M12 3l2.5 5.5L20 11l-5.5 2.5L12 19l-2.5-5.5L4 11l5.5-2.5z' },
];

function Icon({ d, size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

/* ───────────── The instrument: signature element ───────────── */

function polar(r, deg) {
  const a = ((deg - 90) * Math.PI) / 180;
  return [200 + r * Math.cos(a), 200 + r * Math.sin(a)];
}
function arc(r, from, to) {
  const [x1, y1] = polar(r, from);
  const [x2, y2] = polar(r, to);
  return `M${x1} ${y1} A${r} ${r} 0 ${to - from > 180 ? 1 : 0} 1 ${x2} ${y2}`;
}

const METRICS = [
  { key: 'keyword_match_score', label: 'Keywords', r: 128, cls: 'amber' },
  { key: 'experience_match_score', label: 'Experience', r: 110, cls: 'lilac' },
  { key: 'formatting_score', label: 'Formatting', r: 92, cls: 'mint' },
];

function Instrument({ ats, active, setActive, empty = false }) {
  const kws = [
    ...ats.matched_keywords.map((k) => ({ k, m: true })),
    ...ats.missing_keywords.map((k) => ({ k, m: false })),
  ];
  return (
    <svg className="st-inst" viewBox="0 0 400 400" role="img" aria-label={empty ? 'No score yet' : `ATS match ${ats.overall_score} out of 100`}>
      <circle cx="200" cy="200" r="186" className="st-inst__orbit" />
      <circle cx="200" cy="200" r="158" className="st-inst__orbit st-inst__orbit--solid" />
      {METRICS.map((m, i) => (
        <g key={m.key}>
          <path d={arc(m.r, -135, 135)} className="st-inst__track" />
          {!empty && (
            <path
              d={arc(m.r, -135, -135 + (270 * ats[m.key]) / 100)}
              className={`st-inst__arc st-${m.cls}`}
              style={{ animationDelay: `${0.15 * i}s` }}
              pathLength="100"
            />
          )}
        </g>
      ))}
      {!empty &&
        kws.map(({ k, m }, i) => {
          const [x, y] = polar(m ? 158 : 186, (360 / kws.length) * i + 8);
          const on = active === k;
          return (
            <g key={k} className={`st-inst__kw ${m ? 'is-match' : 'is-miss'} ${on ? 'is-on' : ''}`} onMouseEnter={() => setActive?.(k)} onMouseLeave={() => setActive?.(null)}>
              <circle cx={x} cy={y} r={on ? 9 : 5.5} />
            </g>
          );
        })}
      <text x="200" y="214" textAnchor="middle" className="st-inst__num">{empty ? '—' : ats.overall_score}</text>
      <text x="200" y="250" textAnchor="middle" className="st-inst__label">{empty ? 'Awaiting a resume' : active || 'ATS match'}</text>
    </svg>
  );
}

/* ───────────── Pipeline graph: real architecture ───────────── */

function PipelineGraph({ step = PIPELINE.length, compact = false }) {
  const pos = {
    parse: [80, 100],
    ats: [330, 50],
    gap: [330, 150],
    rewrite: [580, 50],
    interview: [580, 150],
  };
  const edges = [['parse', 'ats'], ['parse', 'gap'], ['ats', 'rewrite'], ['ats', 'interview'], ['gap', 'rewrite'], ['gap', 'interview']];
  const state = (id) => {
    const i = PIPELINE.findIndex((p) => p.id === id);
    const stage = PIPELINE[i].stage;
    const cur = PIPELINE[Math.min(Math.max(step, 0), PIPELINE.length - 1)].stage;
    if (step >= PIPELINE.length) return 'done';
    if (stage < cur) return 'done';
    if (stage === cur) return 'now';
    return 'wait';
  };
  return (
    <svg className={`st-graph ${compact ? 'st-graph--compact' : ''}`} viewBox="0 0 700 200" role="img" aria-label="Analysis pipeline: parse, then score and find gaps in parallel, then rewrite and write interview questions in parallel">
      {edges.map(([a, b]) => {
        const [x1, y1] = pos[a];
        const [x2, y2] = pos[b];
        const s = state(b);
        return <path key={a + b} d={`M${x1 + 70} ${y1} C ${x1 + 130} ${y1}, ${x2 - 130} ${y2}, ${x2 - 70} ${y2}`} className={`st-graph__edge is-${s}`} />;
      })}
      {PIPELINE.map((p) => {
        const [x, y] = pos[p.id];
        const s = state(p.id);
        return (
          <g key={p.id} className={`st-graph__node is-${s}`} transform={`translate(${x - 70} ${y - 22})`}>
            <rect width="140" height="44" rx="22" />
            <text x="70" y="27" textAnchor="middle">{p.agent}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ───────────── Landing ───────────── */

function Landing({ go, seeSample }) {
  const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const lines = [
    ['Product analyst with five years of experience in ', ['SQL', 1], ', ', ['Python', 1], ' and dashboarding.'],
    ['Built ', ['Looker', 1], ' dashboards for the onboarding team.'],
    ['Ran ', ['A/B tests', 1], ' on the pricing page.'],
    ['Helped migrate reports to ', ['dbt', 1], '.'],
    ['Skills: Statistics, BigQuery, Git, Airflow'],
  ];
  return (
    <div className="st-landing">
      <header className="st-topbar">
        <span className="st-wordmark">Resumizer</span>
        <nav aria-label="Primary">
          <a href="#st-how">How it works</a>
          <button className="st-btn st-btn--amber" onClick={() => go('upload')}>Run a match</button>
        </nav>
      </header>

      <section className="st-hero">
        <h1>See your resume the way the screener does.</h1>
        <p>
          Upload your resume and the job you want. In about two minutes you get an ATS match score, every keyword you’re
          missing, rewritten bullets, and the interview questions you’re likely to face.
        </p>
        <div className="st-hero__actions">
          <button className="st-btn st-btn--amber st-btn--lg" onClick={() => go('upload')}>Run a match</button>
          <button className="st-btn st-btn--ghost st-btn--lg" onClick={seeSample}>Open a sample report</button>
        </div>
      </section>

      <section className="st-console" aria-label="Sample scan">
        <div className="st-console__doc">
          <p className="st-console__cap">Resume, scanned against the posting</p>
          <div className={`st-scan ${reduced ? 'is-static' : ''}`}>
            {lines.map((l, i) => (
              <p key={i} style={{ '--i': i }}>
                {l.map((seg, j) => (typeof seg === 'string' ? seg : <mark key={j}>{seg[0]}</mark>))}
              </p>
            ))}
            <span className="st-scan__beam" aria-hidden="true" />
          </div>
        </div>
        <div className="st-console__inst">
          <Instrument ats={sample.ats_score} />
          <ul className="st-legend">
            {METRICS.map((m) => (
              <li key={m.key}><i className={`st-dot st-${m.cls}`} />{m.label}<b>{sample.ats_score[m.key]}</b></li>
            ))}
          </ul>
        </div>
        <div className="st-console__miss">
          <p className="st-console__cap">Asked for, not on your resume</p>
          <ul>
            {sample.ats_score.missing_keywords.map((k, i) => <li key={k} style={{ '--i': i }}>{k}</li>)}
          </ul>
        </div>
      </section>

      <section className="st-how" id="st-how" aria-labelledby="st-how-h">
        <h2 id="st-how-h">Five agents, three passes</h2>
        <p>Your resume is parsed once, then scored and gap-checked side by side, then rewritten and turned into interview questions side by side.</p>
        <PipelineGraph />
      </section>

      <footer className="st-landing__foot">
        <p>PDF, DOCX, TXT or Markdown.</p>
        <button className="st-btn st-btn--amber" onClick={() => go('upload')}>Run a match</button>
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
    <form className="st-upload" onSubmit={(e) => { e.preventDefault(); if (ready) proto.run(file, jd); }}>
      <header className="st-pagehead">
        <h1>New match</h1>
        <p>Your resume and one job description. We’ll score one against the other.</p>
      </header>
      <div className="st-upload__grid">
        <section className="st-panel st-drop-panel">
          <h2 className="st-panel__title"><label htmlFor="st-file">Resume</label></h2>
          <div
            className={`st-drop ${drag ? 'is-drag' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); e.dataTransfer.files[0] && setFile(e.dataTransfer.files[0]); }}
          >
            <input ref={input} id="st-file" type="file" accept=".pdf,.docx,.doc,.txt,.md" className="st-sr" onChange={(e) => e.target.files[0] && setFile(e.target.files[0])} />
            <Instrument ats={sample.ats_score} empty />
            {file ? (
              <div className="st-drop__file">
                <p className="st-drop__name">{file.name}</p>
                <p className="st-muted">{(file.size / 1024).toFixed(1)} KB, ready to analyse</p>
                <button type="button" className="st-textbtn" onClick={() => input.current.click()}>Replace file</button>
              </div>
            ) : (
              <div className="st-drop__file">
                <p className="st-drop__name">Drop your resume</p>
                <p className="st-muted">PDF, DOCX, TXT or MD</p>
                <button type="button" className="st-btn st-btn--ghost" onClick={() => input.current.click()}>Browse files</button>
              </div>
            )}
          </div>
        </section>
        <section className="st-panel">
          <div className="st-panel__row">
            <h2 className="st-panel__title"><label htmlFor="st-jd">Job description</label></h2>
            <button type="button" className="st-textbtn" onClick={() => setJd(SAMPLE_JD)}>Use sample</button>
          </div>
          <textarea id="st-jd" className="st-textarea" rows={14} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the whole posting. Requirements and nice-to-haves both count." />
          <p className="st-muted st-count">{jd.trim() ? `${jd.trim().split(/\s+/).length} words` : 'Nothing pasted yet'}</p>
        </section>
      </div>
      <div className="st-upload__bar">
        <p className="st-muted">{ready ? 'Ready. Analysis takes about two minutes.' : !file ? 'Add a resume to continue.' : 'Paste a job description to continue.'}</p>
        <button className="st-btn st-btn--amber st-btn--lg" disabled={!ready}>Run analysis</button>
      </div>
    </form>
  );
}

function Running({ proto }) {
  const [t, setT] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setT((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const cur = PIPELINE[Math.min(Math.max(proto.stepIndex, 0), PIPELINE.length - 1)];
  return (
    <section className="st-running" aria-live="polite">
      <header className="st-pagehead">
        <h1>Analysing {proto.fileName}</h1>
        <p>Pass {cur.stage} of 3 — {cur.label.toLowerCase()}. <span className="st-mono">{t}s</span></p>
      </header>
      <div className="st-panel st-panel--graph">
        <PipelineGraph step={proto.stepIndex} />
      </div>
      <p className="st-muted">You can leave this tab open; results appear here when all five agents finish.</p>
    </section>
  );
}

function Failure({ proto }) {
  return (
    <section className="st-failure" role="alert">
      <div className="st-panel st-panel--alert">
        <h1>{proto.error?.title}</h1>
        <p>{proto.error?.body}</p>
        <div className="st-row">
          <button className="st-btn st-btn--amber" onClick={() => { proto.forceState('empty'); proto.setView('upload'); }}>Upload another file</button>
        </div>
      </div>
    </section>
  );
}

function Empty({ proto }) {
  return (
    <section className="st-empty">
      <Instrument ats={sample.ats_score} empty />
      <h1>No report yet</h1>
      <p>Run a match to fill this view with your score, gaps and rewrites.</p>
      <button className="st-btn st-btn--amber st-btn--lg" onClick={() => proto.setView('upload')}>New match</button>
    </section>
  );
}

function Match({ data }) {
  const a = data.analysis.ats_score;
  const g = data.analysis.skill_gap;
  const [active, setActive] = useState(null);
  return (
    <div className="st-match">
      <section className="st-panel st-panel--hero">
        <div className="st-hero-inst">
          <Instrument ats={a} active={active} setActive={setActive} />
        </div>
        <div className="st-hero-side">
          <ul className="st-metrics">
            {METRICS.map((m) => (
              <li key={m.key}>
                <span><i className={`st-dot st-${m.cls}`} />{m.label}</span>
                <b>{a[m.key]}</b>
              </li>
            ))}
          </ul>
          <p className="st-summary">{a.breakdown_summary}</p>
        </div>
      </section>

      <section className="st-panel st-fix" aria-labelledby="st-fix-h">
        <h2 id="st-fix-h" className="st-panel__title">Fix first</h2>
        <ol>
          {g.priority_skill_recommendations.map((r) => <li key={r}>{r}</li>)}
        </ol>
      </section>

      <section className="st-panel st-kw" aria-labelledby="st-kw-h">
        <h2 id="st-kw-h" className="st-panel__title">Keywords <span className="st-muted">— point at one to find it on the dial</span></h2>
        <div className="st-kw__cols">
          <div>
            <h3><i className="st-dot st-mint" />Found <span>{a.matched_keywords.length}</span></h3>
            <ul>
              {a.matched_keywords.map((k) => (
                <li key={k}><button className={active === k ? 'is-on' : ''} onMouseEnter={() => setActive(k)} onMouseLeave={() => setActive(null)} onFocus={() => setActive(k)} onBlur={() => setActive(null)}>{k}</button></li>
              ))}
            </ul>
          </div>
          <div>
            <h3><i className="st-dot st-dot--ring" />Missing <span>{a.missing_keywords.length}</span></h3>
            <ul className="is-miss">
              {a.missing_keywords.map((k) => (
                <li key={k}><button className={active === k ? 'is-on' : ''} onMouseEnter={() => setActive(k)} onMouseLeave={() => setActive(null)} onFocus={() => setActive(k)} onBlur={() => setActive(null)}>{k}</button></li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="st-panel st-matrix" aria-labelledby="st-matrix-h">
        <h2 id="st-matrix-h" className="st-panel__title">Skill gaps</h2>
        <div className="st-matrix__grid" role="table" aria-label="Skills you have and skills the role needs">
          <div role="row" className="st-matrix__head">
            <span role="columnheader" />
            <span role="columnheader">On your resume</span>
            <span role="columnheader">Missing</span>
          </div>
          <div role="row">
            <span role="rowheader">Technical</span>
            <span role="cell">{g.matched_hard_skills.map((s) => <em key={s}>{s}</em>)}</span>
            <span role="cell" className="is-miss">{g.missing_hard_skills.map((s) => <em key={s}>{s}</em>)}</span>
          </div>
          <div role="row">
            <span role="rowheader">Soft</span>
            <span role="cell">{g.matched_soft_skills.map((s) => <em key={s}>{s}</em>)}</span>
            <span role="cell" className="is-miss">{g.missing_soft_skills.map((s) => <em key={s}>{s}</em>)}</span>
          </div>
        </div>
      </section>
    </div>
  );
}

function Rewrite({ data }) {
  const rw = data.analysis.rewrite_report;
  const [mode, setMode] = useState('compare');
  const [copied, setCopied] = useState(false);
  const all = [rw.tailored_summary, ...rw.rewritten_experiences.flatMap((e) => e.rewritten_bullets.map((b) => `• ${b.rewritten_bullet}`))].join('\n');
  return (
    <div className="st-rewrite">
      <div className="st-toolbar">
        <div className="st-seg" role="radiogroup" aria-label="View">
          {[['compare', 'Before and after'], ['final', 'Final text']].map(([id, l]) => (
            <button key={id} role="radio" aria-checked={mode === id} className={mode === id ? 'is-on' : ''} onClick={() => setMode(id)}>{l}</button>
          ))}
        </div>
        <button className="st-btn st-btn--ghost" onClick={() => { navigator.clipboard?.writeText(all); setCopied(true); setTimeout(() => setCopied(false), 1600); }}>
          {copied ? 'Copied all rewrites' : 'Copy all rewrites'}
        </button>
      </div>

      <section className="st-panel">
        <h2 className="st-panel__title">Summary</h2>
        <p className="st-rw-summary">{rw.tailored_summary}</p>
      </section>

      {rw.rewritten_experiences.map((exp) => (
        <section key={exp.company} className="st-panel st-role">
          <h2 className="st-panel__title">{exp.job_title} <span className="st-muted">at {exp.company}</span></h2>
          <ul>
            {exp.rewritten_bullets.map((b) => (
              <li key={b.original_bullet} className={`st-rw st-rw--${mode}`}>
                {mode === 'compare' && <p className="st-rw__before">{b.original_bullet}</p>}
                <p className="st-rw__after">{b.rewritten_bullet}</p>
                <div className="st-rw__meta">
                  <span className="st-impact">{b.star_result}</span>
                  {b.added_keywords.map((k) => <span key={k} className="st-tag">+ {k}</span>)}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
      <p className="st-concept"><b>Concept, not yet built:</b> export the rewritten resume as DOCX or PDF.</p>
    </div>
  );
}

const QTYPE = { behavioral: 'Behavioural', technical: 'Technical', gap_focused: 'Gap' };

function Interview({ data }) {
  const qs = data.analysis.interview_prep.questions;
  const [i, setI] = useState(0);
  const [tab, setTab] = useState('why');
  const [secs, setSecs] = useState(120);
  const [running, setRunning] = useState(false);
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setSecs((s) => (s <= 1 ? (setRunning(false), 0) : s - 1)), 1000);
    return () => clearInterval(id);
  }, [running]);
  const pick = (n) => { setI(n); setTab('why'); setSecs(120); setRunning(false); };
  const q = qs[i];
  if (!qs.length) return <section className="st-empty"><h1>No questions returned</h1><p>The interview agent came back empty for this run. Run the analysis again, or ask the career coach for practice questions.</p></section>;
  return (
    <div className="st-interview">
      <nav className="st-panel st-qlist" aria-label="Questions">
        {['behavioral', 'technical', 'gap_focused'].map((t) => (
          <div key={t}>
            <h2>{QTYPE[t]}</h2>
            <ul>
              {qs.map((qq, n) => qq.question_type === t && (
                <li key={n}><button className={n === i ? 'is-on' : ''} aria-current={n === i} onClick={() => pick(n)}>{qq.question}</button></li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <article className="st-panel st-qfocus">
        <p className="st-muted">{QTYPE[q.question_type]} question, {i + 1} of {qs.length}</p>
        <h1>{q.question}</h1>
        <div className="st-timer">
          <span className="st-mono" aria-live="off">{String(Math.floor(secs / 60))}:{String(secs % 60).padStart(2, '0')}</span>
          <button className="st-btn st-btn--ghost" onClick={() => setRunning((r) => !r)}>{running ? 'Pause' : secs === 120 ? 'Practise out loud' : 'Resume'}</button>
          {secs !== 120 && <button className="st-textbtn" onClick={() => { setSecs(120); setRunning(false); }}>Reset</button>}
        </div>
        <div className="st-seg" role="tablist" aria-label="Guidance">
          {[['why', 'Why they ask'], ['star', 'Structure'], ['answer', 'Model answer']].map(([id, l]) => (
            <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? 'is-on' : ''} onClick={() => setTab(id)}>{l}</button>
          ))}
        </div>
        <p className="st-qbody" role="tabpanel">{tab === 'why' ? q.context_or_reason : tab === 'star' ? q.star_guide : q.sample_answer}</p>
        <div className="st-row st-row--end">
          <button className="st-textbtn" disabled={i === 0} onClick={() => pick(i - 1)}>Previous</button>
          <button className="st-btn st-btn--amber" disabled={i === qs.length - 1} onClick={() => pick(i + 1)}>Next question</button>
        </div>
      </article>
    </div>
  );
}

function Coach() {
  const c = useCoach('I’ve indexed your resume and the Fieldnote posting. Ask about priorities, gaps, or how to phrase something.');
  const [text, setText] = useState('');
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }); }, [c.messages, c.thinking]);
  return (
    <div className="st-panel st-coach">
      <div className="st-coach__log" aria-live="polite">
        {c.messages.map((m, n) => (
          <div key={n} className={`st-msg st-msg--${m.role}`}>
            <ReactMarkdown>{m.content}</ReactMarkdown>
          </div>
        ))}
        {c.thinking && <div className="st-msg st-msg--assistant st-msg--wait" aria-label="Coach is replying"><span /><span /><span /></div>}
        <div ref={end} />
      </div>
      <div className="st-coach__suggest">
        {COACH_SUGGESTIONS.map((s) => <button key={s} className="st-chip" onClick={() => c.send(s)}>{s}</button>)}
      </div>
      <form className="st-coach__form" onSubmit={(e) => { e.preventDefault(); c.send(text); setText(''); }}>
        <label htmlFor="st-ask" className="st-sr">Message the coach</label>
        <input id="st-ask" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about this application" />
        <button className="st-btn st-btn--amber" disabled={!text.trim() || c.thinking}>Send</button>
      </form>
    </div>
  );
}

function History({ proto }) {
  const rows = [
    ['Senior Product Analyst', 'Fieldnote', 72, 'Today'],
    ['Product Analyst II', 'Tidewater Books', 64, '12 Oct'],
    ['Growth Analyst', 'Orbita Transit', 58, '30 Sep'],
  ];
  return (
    <div className="st-history">
      <p className="st-concept"><b>Concept, not yet built:</b> Resumizer has no accounts or saved reports today. This is how a history could look.</p>
      <div className="st-panel">
        <table className="st-table">
          <thead><tr><th scope="col">Role</th><th scope="col">Company</th><th scope="col">Match</th><th scope="col">Run</th></tr></thead>
          <tbody>
            {rows.map(([r, c, s, d]) => (
              <tr key={r}>
                <td><button className="st-textbtn" onClick={() => proto.setView('match')}>{r}</button></td><td>{c}</td>
                <td><span className="st-bar"><i style={{ width: `${s}%` }} /></span>{s}</td><td className="st-muted">{d}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ───────────── Shell ───────────── */

export default function StudioApp() {
  useFonts(FONTS);
  usePageColors('#120E1C', '#EDE8F5', 'Resumizer — Option B, Career Intelligence Studio');
  const proto = usePrototype();
  const { view, setView, status, data } = proto;
  const seeSample = () => { proto.forceState('ready'); setView('match'); };

  if (view === 'landing') {
    return (
      <div className="st-root">
        <Landing go={setView} seeSample={seeSample} />
        <PrototypeBar concept="B" proto={proto} />
      </div>
    );
  }

  const needsData = ['match', 'rewrite', 'interview', 'coach'].includes(view);
  let body;
  if (view === 'history') body = <History proto={proto} />;
  else if (status === 'loading') body = <Running proto={proto} />;
  else if (status === 'error') body = <Failure proto={proto} />;
  else if (view === 'upload') body = <Upload proto={proto} />;
  else if (needsData && !data) body = <Empty proto={proto} />;
  else if (view === 'match') body = <Match data={data} />;
  else if (view === 'rewrite') body = <Rewrite data={data} />;
  else if (view === 'interview') body = <Interview data={data} />;
  else if (view === 'coach') body = <Coach />;

  const title = NAV.find((n) => n.id === view)?.label;

  return (
    <div className="st-root st-shell">
      <aside className="st-rail" aria-label="Workspace">
        <button className="st-wordmark" onClick={() => setView('landing')}>Resumizer</button>
        <button className="st-btn st-btn--amber st-rail__new" onClick={() => { proto.forceState('empty'); setView('upload'); }}>New match</button>
        <nav>
          {NAV.map((n) => (
            <button key={n.id} className={view === n.id ? 'is-on' : ''} aria-current={view === n.id ? 'page' : undefined} onClick={() => setView(n.id)}>
              <Icon d={n.icon} /> <span>{n.label}</span>
            </button>
          ))}
          <button className={`st-rail__hist ${view === 'history' ? 'is-on' : ''}`} onClick={() => setView('history')}>
            <Icon d="M12 7v5l3 2M4 12a8 8 0 1 0 2.3-5.7M4 4v4h4" /> <span>History</span>
          </button>
        </nav>
        {data && (
          <div className="st-rail__ctx">
            <p>{data.analysis.resume_data.full_name}</p>
            <p className="st-muted">Senior Product Analyst, Fieldnote</p>
          </div>
        )}
      </aside>
      <header className="st-mobilebar">
        <button className="st-wordmark" onClick={() => setView('landing')}>Resumizer</button>
        <button className="st-btn st-btn--amber" onClick={() => { proto.forceState('empty'); setView('upload'); }}>New match</button>
      </header>
      <main className="st-main" key={view + status}>
        {title && data && status === 'ready' && (
          <header className="st-pagehead st-pagehead--report">
            <h1>{title}</h1>
            <p>{data.analysis.resume_data.full_name} for Senior Product Analyst at Fieldnote</p>
          </header>
        )}
        {view === 'history' && <header className="st-pagehead"><h1>History</h1></header>}
        {body}
      </main>
      <PrototypeBar concept="B" proto={proto} />
    </div>
  );
}
