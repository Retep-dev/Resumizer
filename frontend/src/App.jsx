import React, { useState } from 'react';
import api from './api';
import Navbar from './components/Navbar';
import FileUploader from './components/FileUploader';
import ATSScoreCard from './components/ATSScoreCard';
import SkillGapView from './components/SkillGapView';
import RewriteDiffView from './components/RewriteDiffView';
import InterviewPrep from './components/InterviewPrep';
import CareerCoachChat from './components/CareerCoachChat';
import { Award, FileEdit, HelpCircle, MessageSquare } from 'lucide-react';

const tabs = [
  { id: 'overview', label: 'ATS & Gaps', icon: Award },
  { id: 'rewrite', label: 'STAR Rewriter', icon: FileEdit },
  { id: 'interview', label: 'Interview Prep', icon: HelpCircle },
  { id: 'chat', label: 'AI Career Coach', icon: MessageSquare },
];

export default function App() {
  const [analysisData, setAnalysisData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const handleAnalyze = async (file, jobDescription) => {
    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_description', jobDescription);

    try {
      const response = await api.post('/api/v1/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setAnalysisData(response.data);
      setActiveTab('overview');
    } catch (err) {
      const detail = err.response?.data?.detail;
      let msg = 'An error occurred while analyzing the resume. Please check backend logs.';
      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map(d => d.msg || JSON.stringify(d)).join(', ');
      } else if (detail) {
        msg = JSON.stringify(detail);
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setAnalysisData(null);
    setError(null);
    setActiveTab('overview');
  };

  return (
    <div className="min-h-screen bg-navy-950 text-slate-200 flex flex-col font-sans antialiased overflow-x-hidden">
      <Navbar onReset={analysisData ? handleReset : null} />

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-8 space-y-6 sm:space-y-8">
        {!analysisData ? (
          <FileUploader
            onAnalyze={handleAnalyze}
            isLoading={isLoading}
            error={error}
          />
        ) : (
          <div className="space-y-6 sm:space-y-8 w-full animate-fade-in">
            {/* Analysis Header Banner */}
            <div className="surface-card p-4 sm:p-6 flex flex-col lg:flex-row items-center justify-between gap-4">
              <div className="text-center lg:text-left w-full lg:w-auto">
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-100 font-display">
                  Analysis Complete for{' '}
                  <span className="gradient-text-teal">
                    {analysisData.analysis.resume_data.full_name || 'Candidate'}
                  </span>
                </h2>
                <p className="text-xs text-slate-500 font-semibold mt-1 truncate max-w-xs sm:max-w-md mx-auto lg:mx-0">
                  Session ID:{' '}
                  <code className="text-teal-400 font-mono text-[11px]">{analysisData.session_id}</code>
                </p>
              </div>

              {/* Segmented Tab Navigation */}
              <div className="w-full lg:w-auto overflow-x-auto pb-1 lg:pb-0 scrollbar-none">
                <div className="flex items-center gap-1 p-1 rounded-xl bg-navy-900 border border-white/[0.06] min-w-max">
                  {tabs.map((tab) => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center space-x-1.5 sm:space-x-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all duration-200 ${
                          isActive
                            ? 'bg-surface-raised text-teal-400 shadow-card border border-white/[0.08]'
                            : 'text-slate-500 hover:text-slate-300 hover:bg-white/[0.03]'
                        }`}
                      >
                        <Icon className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${isActive ? 'text-teal-400' : ''}`} />
                        <span>{tab.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Tab Views */}
            <div className="animate-fade-in">
              {activeTab === 'overview' && (
                <div className="space-y-6 sm:space-y-8 w-full">
                  <ATSScoreCard atsScore={analysisData.analysis.ats_score} />
                  <SkillGapView skillGap={analysisData.analysis.skill_gap} />
                </div>
              )}

              {activeTab === 'rewrite' && (
                <RewriteDiffView rewriteReport={analysisData.analysis.rewrite_report} />
              )}

              {activeTab === 'interview' && (
                <InterviewPrep interviewPrep={analysisData.analysis.interview_prep} />
              )}

              {activeTab === 'chat' && (
                <CareerCoachChat sessionId={analysisData.session_id} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
