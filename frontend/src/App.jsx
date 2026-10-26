import React, { useCallback, useEffect, useRef, useState } from 'react';
import { analyzeResume, describeAnalyzeError, isCancel } from './api';
import { useHashRoute } from './hooks/useHashRoute';
import { ToastProvider } from './components/ui/Toast';
import Navbar from './components/Navbar';
import Landing from './components/Landing';
import FileUploader from './components/FileUploader';
import AnalysisProgress from './components/AnalysisProgress';
import ATSScoreCard from './components/ATSScoreCard';
import SkillGapView from './components/SkillGapView';
import RewriteDiffView from './components/RewriteDiffView';
import InterviewPrep from './components/InterviewPrep';
import CareerCoachChat from './components/CareerCoachChat';
import AnalysisStatus from './components/AnalysisStatus';

const TAB_IDS = ['score', 'rewrite', 'interview', 'coach'];

function countRewrites(report) {
  // Matches the "kept" total on the Rewrites tab: every bullet plus the summary.
  const bullets = (report?.rewritten_experiences || []).reduce((n, e) => n + (e.rewritten_bullets || []).filter((b) => b.status !== 'kept_original').length, 0);
  return bullets + (report?.tailored_summary ? 1 : 0);
}

export default function App() {
  const [route, navigate] = useHashRoute();
  const [analysisData, setAnalysisData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [analyzedFor, setAnalyzedFor] = useState(null); // { fileName, jd } of the current results
  const [kept, setKept] = useState(() => new Set());
  const abortRef = useRef(null);

  const hasResults = !!analysisData;
  const activeTab = route.startsWith('results/') && TAB_IDS.includes(route.slice(8)) ? route.slice(8) : 'score';

  // Results only live in memory — keep the URL honest about what can be shown.
  useEffect(() => {
    if (route.startsWith('results') && !hasResults) navigate('analyze', { replace: true });
  }, [route, hasResults, navigate]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [route.split('/')[0]]); // eslint-disable-line react-hooks/exhaustive-deps

  // Warn before closing the tab, because results aren't saved anywhere.
  useEffect(() => {
    if (!hasResults && !isLoading) return undefined;
    const onBeforeUnload = (e) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [hasResults, isLoading]);

  const handleAnalyze = useCallback(async () => {
    if (!file || !jobDescription.trim() || isLoading) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError(null);
    navigate('analyze', { replace: route === 'analyze' });
    try {
      const data = await analyzeResume(file, jobDescription, { signal: controller.signal });
      setAnalysisData(data);
      setAnalyzedFor({ fileName: file.name, jd: jobDescription });
      setKept(new Set());
      navigate('results/score');
    } catch (err) {
      if (!isCancel(err)) setError(describeAnalyzeError(err));
    } finally {
      abortRef.current = null;
      setIsLoading(false);
    }
  }, [file, jobDescription, isLoading, navigate, route]);

  const handleCancel = () => abortRef.current?.abort();

  const handleReset = () => {
    setAnalysisData(null);
    setAnalyzedFor(null);
    setError(null);
    setKept(new Set());
    navigate('analyze');
  };

  const toggleKeep = (key) =>
    setKept((s) => {
      const n = new Set(s);
      n.has(key) ? n.delete(key) : n.add(key);
      return n;
    });

  const goHome = (anchor) => {
    navigate('');
    if (anchor) requestAnimationFrame(() => {
      const el = document.getElementById(anchor);
      el?.scrollIntoView();
      el?.focus({ preventScroll: true });
    });
  };

  const analysis = analysisData?.analysis;
  const tabs = analysis
    ? [
        { id: 'score', label: 'Score & gaps', short: 'Score', className: 'tab--score' },
        { id: 'rewrite', label: 'Rewrites', count: countRewrites(analysis.rewrite_report), className: 'tab--rewrite' },
        { id: 'interview', label: 'Interview prep', short: 'Interview', count: (analysis.interview_prep?.questions || analysis.interview_prep?.interview_questions || []).length, className: 'tab--interview' },
        { id: 'coach', label: 'Coach', className: 'tab--coach' },
      ]
    : [];

  const onResults = hasResults && route.startsWith('results');
  let view;
  if (isLoading) {
    view = <AnalysisProgress fileName={file?.name} onCancel={handleCancel} />;
  } else if (onResults) {
    const name = analysis.resume_data?.full_name?.trim();
    view = (
      <main id="main">
        <div className="wrap">
          <div className="results-head">
            <div>
              <h1>{name && name.toLowerCase() !== 'candidate' ? `${name}’s analysis` : 'Your analysis'}</h1>
              <p className="results-head__meta">From {analyzedFor?.fileName}. Results aren’t saved — copy anything you want to keep.</p>
            </div>
            {analyzedFor?.jd && (
              <details className="jd-peek">
                <summary>Show the job description</summary>
                <p>{analyzedFor.jd}</p>
              </details>
            )}
          </div>
          <AnalysisStatus analysis={analysis} />
          {TAB_IDS.map((id) => (
            <div key={id} id={`panel-${id}`} role="tabpanel" aria-labelledby={`tab-${id}`} hidden={activeTab !== id} className={activeTab === id ? 'panel' : undefined}>
              {id === 'score' && (
                <>
                  <ATSScoreCard atsScore={analysis.ats_score} />
                  <SkillGapView skillGap={analysis.skill_gap} />
                </>
              )}
              {id === 'rewrite' && <RewriteDiffView rewriteReport={analysis.rewrite_report} kept={kept} onToggleKeep={toggleKeep} stage={analysis.stages?.rewrite} />}
              {id === 'interview' && <InterviewPrep interviewPrep={analysis.interview_prep} stage={analysis.stages?.interview} />}
              {id === 'coach' && <CareerCoachChat sessionId={analysisData.session_id} analysis={analysis} jobDescription={analyzedFor?.jd} />}
            </div>
          ))}
        </div>
      </main>
    );
  } else if (route === 'analyze') {
    view = (
      <FileUploader
        file={file}
        onFileChange={(f) => { setFile(f); setError(null); }}
        jobDescription={jobDescription}
        onJobDescriptionChange={setJobDescription}
        onAnalyze={handleAnalyze}
        serverError={error}
      />
    );
  } else {
    view = <Landing onStart={() => navigate(hasResults ? 'results/score' : 'analyze')} />;
  }

  return (
    <ToastProvider>
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); const m = document.getElementById('main'); m?.setAttribute('tabindex', '-1'); m?.focus(); }}>Skip to content</a>
      <Navbar
        onHome={goHome}
        onStart={() => navigate('analyze')}
        onReset={handleReset}
        hasResults={hasResults}
        busy={isLoading}
        showTabs={onResults && !isLoading}
        tabs={tabs}
        activeTab={activeTab}
        onTab={(id) => navigate(`results/${id}`, { replace: true })}
      />
      {hasResults && !onResults && !isLoading && (
        <div className="wrap" style={{ paddingTop: 12 }}>
          <button type="button" className="link" onClick={() => navigate('results/score')}>Back to your results</button>
        </div>
      )}
      {view}
      {!onResults && !isLoading && (
        <footer className="site-footer">
          <div className="wrap">Resumizer — AI resume analysis. Scores and rewrites are AI-generated; review them before you apply.</div>
        </footer>
      )}
    </ToastProvider>
  );
}
