import React, { useMemo, useState } from 'react';

const TYPE_LABEL = { behavioral: 'Behavioural', technical: 'Technical', gap_focused: 'About your gaps' };
const typeOf = (t) => (TYPE_LABEL[t] ? t : 'other');
const labelOf = (t) => TYPE_LABEL[t] || 'General';

export default function InterviewPrep({ interviewPrep, stage }) {
  const all = useMemo(() => interviewPrep?.questions || interviewPrep?.interview_questions || [], [interviewPrep]);
  const types = useMemo(() => [...new Set(all.map((q) => typeOf(q.question_type)))], [all]);
  const [mode, setMode] = useState('cards');
  const [filter, setFilter] = useState('all');
  const [i, setI] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [marks, setMarks] = useState({});

  if (!all.length) {
    return (
      <div className="empty">
        <div className="empty__plate" aria-hidden="true" />
        <h2 className="t-h2">No interview questions this time</h2>
        <p>The interview-prep step didn’t return questions for this analysis. Run the analysis again, or ask the coach for practice questions.</p>
      </div>
    );
  }

  const deck = filter === 'all' ? all : all.filter((q) => typeOf(q.question_type) === filter);
  const idx = Math.min(i, deck.length - 1);
  const q = deck[idx];
  const qKey = all.indexOf(q);
  const go = (n) => { setI(n); setFlipped(false); };
  const mark = (v) => { setMarks((m) => ({ ...m, [qKey]: v })); if (idx < deck.length - 1) go(idx + 1); };
  const got = Object.values(marks).filter((v) => v === 'got').length;
  const again = Object.values(marks).filter((v) => v === 'again').length;

  return (
    <>
      {stage?.status === 'rule_based' && (
        <p className="iv-template-note">
          <span className="sticker sticker--ink-outline">Template questions</span> The AI was unavailable, so these questions come from the posting’s requirements and have no sample answers.
        </p>
      )}
      <div className="iv-top">
        <div className="seg" role="group" aria-label="View">
          <button type="button" aria-pressed={mode === 'cards'} onClick={() => setMode('cards')}>Flashcards</button>
          <button type="button" aria-pressed={mode === 'list'} onClick={() => setMode('list')}>All questions</button>
        </div>
        {types.length > 1 && (
          <div className="seg" role="group" aria-label="Filter by question type">
            <button type="button" aria-pressed={filter === 'all'} onClick={() => { setFilter('all'); go(0); }}>All {all.length}</button>
            {types.map((t) => (
              <button key={t} type="button" aria-pressed={filter === t} onClick={() => { setFilter(t); go(0); }}>{labelOf(t)}</button>
            ))}
          </div>
        )}
      </div>

      {mode === 'cards' ? (
        <>
          <div className="iv-tally">
            <span className="sticker sticker--green">Got it: {got}</span>
            <span className="sticker sticker--outline">Practise again: {again}</span>
            <span className="iv-tally__pos" aria-live="polite">Card {idx + 1} of {deck.length}</span>
          </div>
          <div className="deck">
            <span className="deck__under" aria-hidden="true" />
            <span className="deck__under deck__under--2" aria-hidden="true" />
            <button type="button" className={`flashcard ${flipped ? 'is-flipped' : ''}`} aria-pressed={flipped} onClick={() => setFlipped((f) => !f)}>
              <span className="flashcard__face flashcard__front" aria-hidden={flipped}>
                <span className={`qtype qtype--${typeOf(q.question_type)}`}>{labelOf(q.question_type)}</span>
                <span className="flashcard__q">{q.question}</span>
                {q.context_or_reason && <span className="flashcard__why">Why they’ll ask: {q.context_or_reason}</span>}
                <span className="flashcard__hint">Answer out loud, then select the card to see a model answer.</span>
              </span>
              <span className="flashcard__face flashcard__back" aria-hidden={!flipped}>
                {q.star_guide && (<><span className="flashcard__label">How to structure it</span><span className="flashcard__star">{q.star_guide}</span></>)}
                {q.sample_answer
                  ? (<><span className="flashcard__label">A strong answer, built from your resume</span><span className="flashcard__answer">{q.sample_answer}</span><span className="flashcard__star">Replace anything in [brackets] with your real details.</span></>)
                  : (<span className="flashcard__star">No sample answer for this one — answer it with a real example from your own experience.</span>)}
              </span>
            </button>
          </div>
          <div className="iv-ctrl">
            <button type="button" className="link" disabled={idx === 0} onClick={() => go(idx - 1)}>Previous card</button>
            <button type="button" className="btn" onClick={() => mark('again')}>Practise again</button>
            <button type="button" className="btn btn--green" onClick={() => mark('got')}>Got it</button>
          </div>
        </>
      ) : (
        <ol className="iv-list">
          {deck.map((qq, n) => (
            <li key={n}>
              <details>
                <summary>
                  <span className={`qtype qtype--${typeOf(qq.question_type)}`}>{labelOf(qq.question_type)}</span>
                  <span className="flashcard__q">{qq.question}</span>
                </summary>
                <div className="iv-list__body">
                  {qq.context_or_reason && (<><h4>Why they’ll ask</h4><p>{qq.context_or_reason}</p></>)}
                  {qq.star_guide && (<><h4>How to structure it</h4><p>{qq.star_guide}</p></>)}
                  {qq.sample_answer ? (<><h4>A strong answer, built from your resume</h4><p>{qq.sample_answer}</p></>) : <p className="empty-line">No sample answer — use a real example from your experience.</p>}
                </div>
              </details>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
