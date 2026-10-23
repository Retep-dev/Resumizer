import React from 'react';
import StretchType from './ui/StretchType';
import Wipe from './ui/Wipe';

// Illustrative copy only — shown as a labelled example of what a rewrite looks like.
const EXAMPLE = {
  before: 'Ran A/B tests on the pricing page.',
  after: 'Designed and analysed 14 pricing-page A/B tests; the winning annual-plan layout raised paid conversion 6.2% at 95% confidence.',
};

const FEATURES = [
  { title: 'ATS match score', body: 'A score out of 100 against the posting, split into keywords, experience and formatting.' },
  { title: 'Rewritten bullets', body: 'Your experience rewritten with the STAR method, with numbers and the posting’s keywords worked in.' },
  { title: 'Interview prep', body: 'Six likely questions — behavioural, technical and gap-focused — each with a model answer.' },
  { title: 'Career coach', body: 'Ask follow-up questions. The coach answers using your resume and the job description.' },
];

function jumpTo(e, id) {
  e.preventDefault();
  const el = document.getElementById(id);
  el?.scrollIntoView();
  el?.focus({ preventScroll: true });
}

export default function Landing({ onStart }) {
  return (
    <main id="main">
      <section className="hero halftone" data-stretch-zone aria-labelledby="hero-title">
        <div className="wrap hero__grid">
          <div>
            <StretchType id="hero-title" className="t-display" text="Remix your resume for the job you want." />
            <p className="t-lede">
              Upload your resume and paste a job posting. Resumizer scores the match, names the skills you’re missing,
              rewrites your bullets and preps you for the interview.
            </p>
            <div className="hero__actions">
              <button type="button" className="btn btn--primary btn--lg" onClick={onStart}>Analyze my resume</button>
              <a className="btn btn--lg" href="#how" onClick={(e) => jumpTo(e, 'how')}>How it works</a>
            </div>
            <p className="hero__formats">PDF, DOCX, TXT or Markdown. No account needed.</p>
          </div>
          <div className="press-art" aria-hidden="true">
            <span className="press-art__ink press-art__ink--pink" />
            <div className="press-art__sheet">
              <span className="press-art__line press-art__line--title" />
              <span className="press-art__line" style={{ width: '80%' }} />
              <span className="press-art__line press-art__line--hit" style={{ width: '92%' }} />
              <span className="press-art__line" style={{ width: '70%' }} />
              <span className="press-art__line press-art__line--miss" style={{ width: '60%' }} />
              <span className="press-art__line press-art__line--hit" style={{ width: '84%' }} />
              <span className="press-art__line" style={{ width: '76%' }} />
              <span className="press-art__line" style={{ width: '50%' }} />
            </div>
            <span className="press-art__ink press-art__ink--blue" />
            <div className="press-art__stamp"><b>ATS</b><span>match</span></div>
          </div>
        </div>
      </section>

      <section className="features" aria-labelledby="features-title">
        <div className="wrap">
          <div className="features__head">
            <h2 id="features-title" className="t-display">Everything you need for one application</h2>
            <p>One upload gives you four tools, all tuned to the specific job you’re going for.</p>
          </div>
          <div className="features__grid">
            {FEATURES.map((f) => (
              <article key={f.title} className="feature">
                <span className="feature__ink" aria-hidden="true" />
                <h3 className="t-h3">{f.title}</h3>
                <p>{f.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="how" id="how" aria-labelledby="how-title" tabIndex={-1}>
        <div className="wrap how__grid">
          <div>
            <h2 id="how-title" className="t-title">Three passes through the press</h2>
            <ol className="passes" style={{ marginTop: 28 }}>
              <li className="pass">
                <span className="pass__n" aria-hidden="true">1</span>
                <div><h3 className="t-h3">Read</h3><p>Your resume is parsed into roles, bullets, skills and education.</p></div>
              </li>
              <li className="pass">
                <span className="pass__n" aria-hidden="true">2</span>
                <div><h3 className="t-h3">Match</h3><p>It’s scored against the posting while missing skills are found, side by side.</p></div>
              </li>
              <li className="pass">
                <span className="pass__n" aria-hidden="true">3</span>
                <div><h3 className="t-h3">Remix</h3><p>Bullets are rewritten and interview questions written, again side by side.</p></div>
              </li>
            </ol>
            <p className="privacy-note">
              Your resume is sent to Resumizer’s server for analysis and indexed for your session so the coach can
              answer questions about it.
            </p>
          </div>
          <div>
            <span className="example-label">Example rewrite — drag or use the buttons to compare</span>
            <Wipe before={EXAMPLE.before} after={EXAMPLE.after} label="the example bullet" />
          </div>
        </div>
      </section>

      <section className="cta-band" data-stretch-zone aria-label="Get started">
        <div className="wrap cta-band__inner">
          <StretchType as="p" className="t-display" text="Your turn." />
          <button type="button" className="btn btn--primary btn--lg" onClick={onStart}>Analyze my resume</button>
        </div>
      </section>
    </main>
  );
}
