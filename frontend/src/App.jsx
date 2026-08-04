import React, { useState } from 'react';
import axios from 'axios';
import Navbar from './components/Navbar';
import FileUploader from './components/FileUploader';
import ATSScoreCard from './components/ATSScoreCard';
import SkillGapView from './components/SkillGapView';
import RewriteDiffView from './components/RewriteDiffView';
import InterviewPrep from './components/InterviewPrep';
import CareerCoachChat from './components/CareerCoachChat';
import { Award, Target, FileEdit, HelpCircle, MessageSquare } from 'lucide-react';

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
      const response = await axios.post('/api/v1/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setAnalysisData(response.data);
      setActiveTab('overview');
    } catch (err) {
      setError(
        err.response?.data?.detail || 'An error occurred while analyzing the resume. Please check backend logs.'
      );
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
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans">
      <Navbar onReset={analysisData ? handleReset : null} />

      <main className="flex-1 pb-16">
        {!analysisData ? (
          <FileUploader
            onAnalyze={handleAnalyze}
            isLoading={isLoading}
            error={error}
          />
        ) : (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            {/* Header summary banner */}
            <div className="glass-panel p-6 rounded-3xl border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-extrabold text-white">
                  Analysis Complete for <span className="text-indigo-400">{analysisData.analysis.resume_data.full_name}</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Session ID: <code className="text-slate-300 font-mono">{analysisData.session_id}</code>
                </p>
              </div>

              {/* Navigation Tabs */}
              <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-2xl bg-slate-900 border border-slate-800">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
                    activeTab === 'overview'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <Award className="h-4 w-4" />
                  <span>ATS & Gaps</span>
                </button>

                <button
                  onClick={() => setActiveTab('rewrite')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
                    activeTab === 'rewrite'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <FileEdit className="h-4 w-4" />
                  <span>STAR Rewriter</span>
                </button>

                <button
                  onClick={() => setActiveTab('interview')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
                    activeTab === 'interview'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <HelpCircle className="h-4 w-4" />
                  <span>Interview Prep</span>
                </button>

                <button
                  onClick={() => setActiveTab('chat')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
                    activeTab === 'chat'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <MessageSquare className="h-4 w-4" />
                  <span>AI Career Coach</span>
                </button>
              </div>
            </div>

            {/* Tab Views */}
            {activeTab === 'overview' && (
              <div className="space-y-8">
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
        )}
      </main>
    </div>
  );
}
