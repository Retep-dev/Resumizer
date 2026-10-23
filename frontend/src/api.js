import axios from 'axios';

const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_URL;
// In production (e.g. Vercel), fallback directly to the live Render backend URL
const defaultUrl = import.meta.env.DEV ? '' : 'https://resumizer-1stb.onrender.com';
const rawUrl = envUrl || defaultUrl;

const API_BASE_URL = rawUrl.replace(/\/+$/, '');

console.log('[Resumizer API] Connected to backend URL:', API_BASE_URL || '(Local Proxy)');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes timeout for cloud deployment & cold starts
});

export default api;

export const ACCEPTED_EXTENSIONS = ['pdf', 'docx', 'txt', 'md'];
export const MAX_FILE_MB = 10;

/** POST /api/v1/analyze — runs the multi-agent pipeline. Returns { session_id, analysis }. */
export async function analyzeResume(file, jobDescription, { signal } = {}) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('job_description', jobDescription);
  const response = await api.post('/api/v1/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    signal,
  });
  return response.data;
}

/**
 * POST /api/v1/chat — career coach grounded in the analysis.
 * The analysis and job description are sent along so the coach still works if
 * the server restarted and lost its copy of the session.
 */
export async function askCoach(sessionId, message, chatHistory, { analysis, jobDescription } = {}) {
  const response = await api.post('/api/v1/chat', {
    session_id: sessionId,
    message,
    chat_history: chatHistory,
    analysis,
    job_description: jobDescription,
  });
  return response.data.reply;
}

/** Backend errors are { detail: { code, message } } (older servers send a string). */
export function errorInfo(err) {
  const d = err?.response?.data?.detail;
  if (d && typeof d === 'object' && !Array.isArray(d)) return { code: d.code || '', message: d.message || '' };
  return { code: '', message: detailText(err) };
}

export function isCancel(err) {
  return axios.isCancel(err) || err?.code === 'ERR_CANCELED';
}

function detailText(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
  if (detail) return JSON.stringify(detail);
  return '';
}

/**
 * Turns an axios error from the analyze endpoint into a message a person can act on.
 * Returns { title, body, detail } — detail is the raw server text, shown on request.
 */
export function describeAnalyzeError(err) {
  const { code, message } = errorInfo(err);
  const detail = message;
  const status = err?.response?.status;

  if (code === 'ai_unavailable') {
    return {
      title: 'The AI analysis is unavailable right now',
      body: message,
      detail: err?.response?.data?.detail?.provider?.message || '',
    };
  }
  if (code === 'parsing_failed') {
    return { title: 'We couldn’t read your resume', body: message, detail: '' };
  }
  if (code === 'validation_failed') {
    return { title: 'Something needs fixing before we can analyse this', body: message, detail: '' };
  }

  if (err?.code === 'ECONNABORTED' || /timeout/i.test(err?.message || '')) {
    return {
      title: 'The analysis took longer than five minutes',
      body: 'The server may be under heavy load. Try again — a second run is usually faster because the server is already awake.',
      detail,
    };
  }
  if (!err?.response) {
    return {
      title: 'Couldn’t reach the analysis server',
      body: 'Check your internet connection and try again. If it keeps happening, the server may be restarting.',
      detail: err?.message || '',
    };
  }
  if (/readable text/i.test(detail)) {
    return {
      title: 'We couldn’t read any text in that file',
      body: 'Scanned or image-only PDFs have no text layer. Export your resume as a DOCX or a text-based PDF and upload it again.',
      detail,
    };
  }
  if (/NVIDIA_API_KEY/i.test(detail)) {
    return {
      title: 'The analysis service isn’t configured',
      body: 'The server is missing its AI provider key, so no analysis can run right now. This needs fixing on the server, not in your resume.',
      detail,
    };
  }
  if (/job description/i.test(detail)) {
    return { title: 'Add the job description', body: 'Paste the posting you are applying for so your resume can be scored against it.', detail };
  }
  if (status === 422) {
    return { title: 'Something was missing from the upload', body: 'Choose your resume file and paste the job description, then try again.', detail };
  }
  if (status >= 500) {
    return {
      title: 'The analysis failed on the server',
      body: 'One of the analysis steps hit an error. Your file and job description are still here — try again in a moment.',
      detail,
    };
  }
  return { title: 'The analysis didn’t complete', body: 'Try again in a moment.', detail };
}
