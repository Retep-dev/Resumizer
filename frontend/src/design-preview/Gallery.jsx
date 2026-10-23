import React, { useEffect, useRef } from 'react';
import { useFonts, usePageColors } from './usePrototype';
import './gallery.css';

const CONCEPTS = [
  {
    id: 'a',
    name: 'Editorial Atelier',
    idea: 'Your resume is tailored like a garment. A fitting in four sittings: Measure, Alter, Rehearse, Counsel.',
    signature: 'The ATS score as a measuring tape; rewrites marked up in tailor’s chalk.',
    type: 'Bodoni Moda with Hanken Grotesk',
    palette: ['#ECEAF1', '#1A1730', '#2D3FCF', '#E7C548', '#9E2D47'],
  },
  {
    id: 'b',
    name: 'Career Intelligence Studio',
    idea: 'A screening room. See your resume the way an applicant tracking system reads it.',
    signature: 'A radial match instrument with a keyword constellation, and a live graph of the real five-agent pipeline.',
    type: 'Archivo, from normal to expanded widths',
    palette: ['#120E1C', '#1B1528', '#FFB547', '#A996FF', '#6FE3B4', '#FF7A6B'],
  },
  {
    id: 'c',
    name: 'Creative Career Lab',
    idea: 'A risograph print studio. Your resume goes through the press and comes out remixed.',
    signature: 'Headline letters that stretch toward your pointer, interview flashcards, and a before/after wipe on every bullet.',
    type: 'Anybody (variable width) with Atkinson Hyperlegible',
    palette: ['#EEF0FF', '#1D1B4C', '#FF4FA3', '#FFE14D', '#2F5BFF', '#007F5F'],
  },
];

const SCREENS = [
  ['landing', 'Landing'],
  ['upload', 'Upload'],
  ['match', 'Score'],
  ['rewrite', 'Rewrites'],
  ['interview', 'Interview'],
  ['coach', 'Coach'],
  ['history', 'History (concept)'],
];

const STATES = [
  ['upload&state=empty', 'Empty'],
  ['upload&state=loading', 'Loading'],
  ['upload&state=error', 'Error'],
];

const ROWS = [
  ['Feeling', 'Calm, literary, premium', 'Focused, cinematic, analytical', 'Loud, playful, youthful'],
  ['Best at', 'Reading and editing long rewrites', 'Making the score and gaps legible at a glance', 'Making practice feel like a game'],
  ['Navigation', 'Four numbered sittings across the top', 'Persistent side rail; bottom tabs on phones', 'Coloured folder tabs'],
  ['Score', 'Measuring tape, 0–100', 'Three-ring dial with keyword dots', 'Halftone numerals and ink strips'],
  ['Interview prep', 'One question at a time, reveal in steps', 'Question list with a practice timer', 'Flip-card deck with got-it tallies'],
  ['Risk', 'Serif-heavy screens can feel slow for data', 'Dark UI is the most familiar of the three', 'Bold style may not suit senior candidates'],
];

// Live, scaled-down render of a concept's landing page.
function Thumb({ c }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    const ro = new ResizeObserver(([e]) => el.style.setProperty('--s', e.contentRect.width / 1440));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <a ref={ref} className="gl-thumb" href={`/design-preview/${c.id}`} aria-label={`Open option ${c.id.toUpperCase()}, ${c.name}`}>
      <iframe title={`Option ${c.id.toUpperCase()} preview`} src={`/design-preview/${c.id}?view=landing`} loading="lazy" tabIndex={-1} aria-hidden="true" />
    </a>
  );
}

export default function Gallery() {
  useFonts('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;700;800&display=swap');
  usePageColors('#F3F3F5', '#141419', 'Resumizer — design directions');

  return (
    <div className="gl-root">
      <header className="gl-head">
        <p className="gl-brand">Resumizer</p>
        <h1>Three directions for the redesign</h1>
        <p className="gl-lede">
          Each one is a working prototype of the whole product: landing page, upload, score, rewrites, interview prep,
          coach, and the loading, empty and error states. They use sample data for a fictional candidate and never call
          the live API.
        </p>
      </header>

      <main className="gl-grid">
        {CONCEPTS.map((c) => (
          <article key={c.id} className="gl-card">
            <Thumb c={c} />
            <div className="gl-body">
              <p className="gl-letter">Option {c.id.toUpperCase()}</p>
              <h2><a href={`/design-preview/${c.id}`}>{c.name}</a></h2>
              <p>{c.idea}</p>
              <dl>
                <dt>Signature</dt><dd>{c.signature}</dd>
                <dt>Type</dt><dd>{c.type}</dd>
              </dl>
              <ul className="gl-swatches" aria-label="Palette">
                {c.palette.map((p) => <li key={p} style={{ background: p }} title={p} />)}
              </ul>
              <nav className="gl-screens" aria-label={`Option ${c.id.toUpperCase()} screens`}>
                {SCREENS.map(([v, l]) => <a key={v} href={`/design-preview/${c.id}?view=${v}`}>{l}</a>)}
              </nav>
              <nav className="gl-screens gl-screens--states" aria-label={`Option ${c.id.toUpperCase()} states`}>
                {STATES.map(([v, l]) => <a key={v} href={`/design-preview/${c.id}?view=${v}`}>{l}</a>)}
              </nav>
            </div>
          </article>
        ))}
      </main>

      <section className="gl-compare" aria-labelledby="gl-compare-h">
        <h2 id="gl-compare-h">Side by side</h2>
        <div className="gl-tablewrap">
          <table>
            <thead>
              <tr><th scope="col"><span className="gl-sr">Aspect</span></th><th scope="col">A. Atelier</th><th scope="col">B. Studio</th><th scope="col">C. Lab</th></tr>
            </thead>
            <tbody>
              {ROWS.map(([k, ...v]) => (
                <tr key={k}><th scope="row">{k}</th>{v.map((x, i) => <td key={i}>{x}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="gl-notes">
        <div>
          <h2>Real today vs. concept</h2>
          <p>
            Upload, ATS scoring, skill gaps, STAR rewrites, interview questions and the coach chat all exist in Resumizer
            now, and every prototype screen for them uses the exact response shape of the API. Saved history and
            downloading a rewritten resume do not exist yet; those screens are labelled as concepts.
          </p>
        </div>
        <div>
          <h2>How to review</h2>
          <p>
            Open an option and use the small “Preview” button in the bottom-left corner to switch between empty,
            loading, error and results states, or jump to another option on the same screen.
          </p>
        </div>
      </section>
    </div>
  );
}
