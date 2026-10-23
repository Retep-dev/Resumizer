import React, { useEffect, useRef, useState } from 'react';
import { ACCEPTED_EXTENSIONS, MAX_FILE_MB } from '../api';
import ErrorNotice from './ErrorNotice';

const MIN_JD_WORDS = 25;

function extOf(name = '') {
  const i = name.lastIndexOf('.');
  return i === -1 ? '' : name.slice(i + 1).toLowerCase();
}

export function validateFile(file) {
  if (!file) return 'Choose your resume file.';
  if (extOf(file.name) === 'doc') return `${file.name} is a legacy Word file. Save it as DOCX or PDF and upload it again.`;
  if (!ACCEPTED_EXTENSIONS.includes(extOf(file.name))) return `${file.name} isn’t a supported format. Use PDF, DOCX, TXT or MD.`;
  if (file.size === 0) return `${file.name} is empty. Choose the file that contains your resume.`;
  if (file.size > MAX_FILE_MB * 1024 * 1024) return `${file.name} is larger than ${MAX_FILE_MB} MB. Export a smaller copy and try again.`;
  return '';
}

export function validateJd(text) {
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  if (!words) return 'Paste the job description you’re applying for.';
  if (words < MIN_JD_WORDS) return `That’s ${words} words. Paste the full posting — at least ${MIN_JD_WORDS} words — so the match is meaningful.`;
  return '';
}

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function FileUploader({ file, onFileChange, jobDescription, onJobDescriptionChange, onAnalyze, serverError }) {
  const [drag, setDrag] = useState(false);
  const [touched, setTouched] = useState(false);
  const input = useRef(null);
  const summaryRef = useRef(null);
  const errorRef = useRef(null);

  const fileError = validateFile(file);
  const jdError = validateJd(jobDescription);
  const showFileError = touched && fileError;
  const showJdError = touched && jdError;
  const words = jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0;

  useEffect(() => {
    if (serverError) errorRef.current?.focus();
  }, [serverError]);

  const pick = (f) => {
    if (!f) return;
    onFileChange(f);
  };

  const submit = (e) => {
    e.preventDefault();
    setTouched(true);
    if (fileError || jdError) {
      requestAnimationFrame(() => summaryRef.current?.focus());
      return;
    }
    onAnalyze();
  };

  return (
    <main id="main" className="page">
      <div className="wrap">
        <div className="page-head">
          <div>
            <h1 className="t-title">Load the press</h1>
            <p className="t-lede">Your resume, and the job you want it scored against.</p>
          </div>
        </div>

        {serverError && <ErrorNotice ref={errorRef} error={serverError} onRetry={onAnalyze} />}

        {touched && (fileError || jdError) && (
          <div ref={summaryRef} tabIndex={-1} className="notice" role="alert" aria-labelledby="form-errors-title">
            <span className="notice__mark" aria-hidden="true">!</span>
            <div>
              <h2 id="form-errors-title">{fileError && jdError ? 'Two things to fix before we can start' : 'One thing to fix before we can start'}</h2>
              <ul style={{ margin: 0, paddingLeft: 20, listStyle: 'disc' }}>
                {fileError && <li><a className="link" href="#resume-file" onClick={(e) => { e.preventDefault(); input.current?.focus(); }}>{fileError}</a></li>}
                {jdError && <li><a className="link" href="#job-description" onClick={(e) => { e.preventDefault(); document.getElementById('job-description')?.focus(); }}>{jdError}</a></li>}
              </ul>
            </div>
          </div>
        )}

        <form onSubmit={submit} noValidate>
          <div className="upload-grid">
            <div>
              <label className="field-label" htmlFor="resume-file">Your resume</label>
              <p className="field-hint" id="resume-file-hint">PDF, DOCX, TXT or MD, up to {MAX_FILE_MB} MB. Text-based files work best.</p>
              <div
                className={`dropzone ${drag ? 'is-drag' : ''} ${file && !fileError ? 'has-file' : ''} ${showFileError ? 'is-invalid' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
              >
                <input
                  ref={input}
                  id="resume-file"
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  className="sr-only"
                  aria-describedby={`resume-file-hint${showFileError ? ' resume-file-error' : ''}`}
                  aria-invalid={!!showFileError}
                  onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ''; }}
                />
                {file ? (
                  <>
                    <div className="file-chip">
                      <span className="file-chip__ext" aria-hidden="true">{extOf(file.name) || '?'}</span>
                      <span>
                        <span className="file-chip__name">{file.name}</span>
                        <br />
                        <span className="file-chip__meta">{formatSize(file.size)}</span>
                      </span>
                    </div>
                    <button type="button" className="link" onClick={() => input.current?.click()}>Choose a different file</button>
                  </>
                ) : (
                  <>
                    <p className="dropzone__big">Drop your resume here</p>
                    <p>or</p>
                    <button type="button" className="btn btn--ink" onClick={() => input.current?.click()}>Choose a file</button>
                  </>
                )}
              </div>
              {showFileError && <p className="field-error" id="resume-file-error">{fileError}</p>}
            </div>

            <div>
              <label className="field-label" htmlFor="job-description">The job posting</label>
              <p className="field-hint" id="jd-hint">Paste the whole posting — responsibilities, requirements and nice-to-haves.</p>
              <div className={`ticket ${showJdError ? 'is-invalid' : ''}`}>
                <textarea
                  id="job-description"
                  value={jobDescription}
                  onChange={(e) => onJobDescriptionChange(e.target.value)}
                  placeholder="Senior Product Analyst&#10;&#10;About the role…"
                  aria-describedby={`jd-hint jd-count${showJdError ? ' jd-error' : ''}`}
                  aria-invalid={!!showJdError}
                  spellCheck="false"
                />
                <div className="ticket__foot">
                  <span id="jd-count">{words ? `${words} words` : 'Nothing pasted yet'}</span>
                  {jobDescription && <button type="button" className="link" style={{ minHeight: 0 }} onClick={() => onJobDescriptionChange('')}>Clear</button>}
                </div>
              </div>
              {showJdError && <p className="field-error" id="jd-error">{jdError}</p>}
            </div>
          </div>

          <div className="upload-actions">
            <button type="submit" className="btn btn--pink btn--lg">Start the analysis</button>
            <p>Usually under a minute. The first run of the day can take longer while the server wakes up.</p>
          </div>
        </form>
      </div>
    </main>
  );
}
