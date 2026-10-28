import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { askCoach, errorInfo } from '../api';

const GREETING =
  'I’ve read your resume and the job description you pasted. Ask me what to fix first, how to handle a gap, or how to answer a question you’re dreading.';

function suggestionsFor(analysis) {
  const missing = analysis?.ats_score?.missing_keywords || analysis?.skill_gap?.missing_hard_skills || [];
  const out = ['What should I fix first on my resume?'];
  if (missing[0]) out.push(`How do I address the missing “${missing[0]}” honestly?`);
  out.push('Draft a short cover note for this role.');
  return out;
}

function coachError(err) {
  const { code, message } = errorInfo(err);
  const text = message || err?.message || '';
  if (!err?.response) return { msg: 'Couldn’t reach the coach. Check your connection and try again.', text };
  if (code === 'session_expired') return { msg: 'This session has expired, so the coach can’t see your resume any more. Run the analysis again to keep chatting.', text: '', final: true };
  if (code === 'ai_unavailable') return { msg: 'The coach is unavailable right now because the AI service isn’t responding. No answer was made up — try again later.', text };
  return { msg: 'The coach couldn’t answer just now.', text };
}

export default function CareerCoachChat({ sessionId, analysis, jobDescription }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: GREETING }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(null); // { message, error }
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const suggestions = useMemo(() => suggestionsFor(analysis), [analysis]);
  const asked = messages.some((m) => m.role === 'user');

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messages, loading, failed]);

  const send = async (text, base = messages) => {
    const userMsg = text.trim();
    if (!userMsg || loading || !sessionId) return;
    const next = [...base, { role: 'user', content: userMsg }];
    setMessages(next);
    setFailed(null);
    setLoading(true);
    try {
      // Same contract as before: history excludes the greeting and the new message.
      const { reply, check } = await askCoach(sessionId, userMsg, next.slice(1, -1), { analysis, jobDescription });
      setMessages((prev) => [...prev, { role: 'assistant', content: reply, check }]);
    } catch (err) {
      setFailed({ message: userMsg, base, error: coachError(err) });
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    const t = input;
    setInput('');
    send(t);
    inputRef.current?.focus();
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) onSubmit(e);
  };

  return (
    <div className="coach">
      <div className="coach__log" role="log" aria-live="polite" aria-label="Conversation with your career coach">
        {messages.map((m, n) => (
          <div key={n} className={`slip slip--${m.role}`}>
            <span className="slip__who">{m.role === 'user' ? 'You' : 'Coach'}</span>
            {m.role === 'user' ? <p>{m.content}</p> : <ReactMarkdown>{m.content}</ReactMarkdown>}
            {m.check === 'corrected' && <p className="slip__check">Checked against your resume: a suggestion that went beyond it was corrected.</p>}
            {m.check === 'uncertain' && <p className="slip__check slip__check--warn">Parts of this answer couldn’t be verified against your resume, so they were removed or marked.</p>}
          </div>
        ))}
        {loading && (
          <div className="slip slip--assistant slip--wait" aria-label="The coach is writing a reply">
            <i /><i /><i />
          </div>
        )}
        {failed && (
          <div className="slip slip--error" role="alert">
            <span className="slip__who">Coach</span>
            <p>{failed.error.msg}</p>
            {!failed.error.final && <button type="button" className="link" onClick={() => send(failed.message, failed.base)}>Try again</button>}
            {failed.error.text && (
              <details style={{ marginTop: 8, fontSize: 14 }}>
                <summary style={{ cursor: 'pointer', fontWeight: 700 }}>Technical details</summary>
                <code style={{ display: 'block', whiteSpace: 'pre-wrap', marginTop: 6 }}>{failed.error.text}</code>
              </details>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {!asked && (
        <div className="coach__suggest" aria-label="Suggested questions">
          {suggestions.map((s) => (
            <button key={s} type="button" disabled={loading} onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      <form className="coach__form" onSubmit={onSubmit}>
        <label htmlFor="coach-input" className="sr-only">Message your career coach</label>
        <textarea
          id="coach-input"
          ref={inputRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about this application"
        />
        <button type="submit" className="btn btn--primary btn--sm" disabled={!input.trim() || loading}>Send</button>
      </form>
      <p className="coach__note">Enter to send, Shift + Enter for a new line. Answers are AI-generated — check facts before you use them.</p>
    </div>
  );
}
