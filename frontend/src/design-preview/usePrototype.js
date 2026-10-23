import { useCallback, useEffect, useRef, useState } from 'react';
import { PIPELINE, SAMPLE_RESPONSE, coachReply } from './data';

const ACCEPTED = ['pdf', 'docx', 'doc', 'txt', 'md'];

// Mirrors the backend's real failure: "Could not extract readable text from uploaded file."
const SAMPLE_ERROR = {
  title: 'No readable text found in Noor_Castellan_Resume.pdf',
  body: 'Scanned PDFs have no text layer. Export your resume as DOCX or a text-based PDF and upload it again.',
};

// Loads a concept's Google Fonts once, only on the preview route.
export function useFonts(href) {
  useEffect(() => {
    if (document.querySelector(`link[data-dp-font="${href}"]`)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.dataset.dpFont = href;
    document.head.appendChild(link);
  }, [href]);
}

// Overrides the production body colour while a preview is mounted.
export function usePageColors(bg, fg, title) {
  useEffect(() => {
    const { style } = document.body;
    const prev = [style.background, style.color, document.title, document.documentElement.style.background];
    style.background = bg;
    style.color = fg;
    document.documentElement.style.background = bg;
    if (title) document.title = title;
    return () => {
      [style.background, style.color, document.title, document.documentElement.style.background] = prev;
    };
  }, [bg, fg, title]);
}

export function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const fn = () => setReduced(mq.matches);
    mq.addEventListener('change', fn);
    return () => mq.removeEventListener('change', fn);
  }, []);
  return reduced;
}

function readParam(name, fallback) {
  const v = new URLSearchParams(window.location.search).get(name);
  return v || fallback;
}

/**
 * Shared prototype state for every concept. Everything is local:
 * no network calls, no storage, no production data.
 *
 * status: 'empty' | 'loading' | 'error' | 'ready'
 */
export function usePrototype({ defaultView = 'landing' } = {}) {
  const [view, setViewState] = useState(() => readParam('view', defaultView));
  const [status, setStatus] = useState(() => readParam('state', 'ready'));
  const [stepIndex, setStepIndex] = useState(() => {
    const st = readParam('state', 'ready');
    return st === 'loading' ? 2 : st === 'ready' ? PIPELINE.length : -1;
  });
  const [error, setError] = useState(() => (readParam('state', '') === 'error' ? SAMPLE_ERROR : null));
  const [fileName, setFileName] = useState('Noor_Castellan_Resume.pdf');
  const timers = useRef([]);

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };
  useEffect(() => clearTimers, []);

  const setView = useCallback((v) => {
    setViewState(v);
    const url = new URL(window.location.href);
    url.searchParams.set('view', v);
    url.searchParams.delete('state');
    window.history.replaceState(null, '', url);
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  }, []);

  // Simulates the real 3-stage pipeline timing (compressed).
  const run = useCallback(
    (file, jd, { fail = false } = {}) => {
      clearTimers();
      setError(null);
      const name = file?.name || 'Noor_Castellan_Resume.pdf';
      setFileName(name);
      const ext = name.split('.').pop().toLowerCase();
      if (file && !ACCEPTED.includes(ext)) {
        setStatus('error');
        setError({
          title: `${name} isn't a resume format we can read`,
          body: 'Upload a PDF, DOCX, TXT or MD file.',
        });
        return;
      }
      if (!jd || !jd.trim()) {
        setStatus('error');
        setError({ title: 'Add the job description', body: 'Paste the posting so we can score your resume against it.' });
        return;
      }
      setStatus('loading');
      setStepIndex(0);
      const step = 900;
      PIPELINE.forEach((_, i) => {
        timers.current.push(setTimeout(() => setStepIndex(i), i * step));
      });
      timers.current.push(
        setTimeout(() => {
          if (fail) {
            setStatus('error');
            setError({
              title: `No readable text found in ${name}`,
              body: 'Scanned PDFs have no text layer. Export your resume as DOCX or a text-based PDF and upload it again.',
            });
          } else {
            setStatus('ready');
            setStepIndex(PIPELINE.length);
            setView('match');
          }
        }, PIPELINE.length * step + 300)
      );
    },
    [setView]
  );

  // Prototype-only switch used by the review toolbar.
  const forceState = useCallback(
    (s) => {
      clearTimers();
      if (s === 'loading') {
        setStatus('loading');
        setStepIndex(2);
      } else if (s === 'error') {
        setStatus('error');
        setError(SAMPLE_ERROR);
      } else {
        setStatus(s);
        setError(null);
        setStepIndex(s === 'ready' ? PIPELINE.length : -1);
      }
    },
    []
  );

  return {
    view,
    setView,
    status,
    error,
    stepIndex,
    fileName,
    run,
    forceState,
    reset: () => forceState('empty'),
    data: status === 'ready' ? SAMPLE_RESPONSE : null,
  };
}

// Local-only coach conversation.
export function useCoach(initial) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: initial }]);
  const [thinking, setThinking] = useState(false);
  const send = (text) => {
    const t = text.trim();
    if (!t || thinking) return;
    setMessages((m) => [...m, { role: 'user', content: t }]);
    setThinking(true);
    setTimeout(() => {
      setMessages((m) => [...m, { role: 'assistant', content: coachReply(t) }]);
      setThinking(false);
    }, 1100);
  };
  return { messages, thinking, send };
}
