import React, { useState, useRef } from 'react';
import { Upload, CheckCircle2, Sparkles, Loader2, AlertCircle, Cpu } from 'lucide-react';

export default function FileUploader({ onAnalyze, isLoading, error }) {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file || !jobDescription.trim()) return;
    onAnalyze(file, jobDescription);
  };

  return (
    <div className="w-full max-w-4xl mx-auto py-6 sm:py-12 px-3 sm:px-4 overflow-x-hidden">
      {/* Hero Section */}
      <div className="text-center mb-8 sm:mb-12 w-full animate-fade-in">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 text-[11px] font-bold uppercase tracking-wider mb-5">
          <Cpu className="h-3.5 w-3.5" />
          <span>5-Agent AI Pipeline · NVIDIA NIM</span>
        </div>

        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-slate-100 mb-4 leading-tight break-words max-w-full font-display">
          AI-Powered Resume{' '}
          <br className="hidden sm:inline" />
          <span className="gradient-text-teal">Optimization & Analysis</span>
        </h1>
        <p className="text-slate-400 text-sm sm:text-base leading-relaxed max-w-2xl mx-auto px-1 break-words font-medium">
          Upload your resume and paste the target job description. Our multi-agent pipeline scores ATS match, identifies skill gaps, rewrites bullets using STAR, and generates interview prep.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-3.5 sm:p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center space-x-2.5 text-red-400 text-xs sm:text-sm font-medium animate-fade-in">
          <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 flex-shrink-0 text-red-400" />
          <span className="break-words">{error}</span>
        </div>
      )}

      {/* Upload Form Card */}
      <div className="surface-card p-5 sm:p-8 space-y-6 animate-fade-in-delay" style={{ opacity: 0 }}>
        <form onSubmit={handleSubmit} className="space-y-6 w-full">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6 w-full">
            {/* File Upload Zone */}
            <div className="space-y-2.5 w-full">
              <label className="block text-xs sm:text-sm font-bold text-slate-300 flex items-center gap-2">
                <span className="h-5 w-5 rounded-md bg-teal-500/20 text-teal-400 text-[11px] font-extrabold flex items-center justify-center border border-teal-500/30">1</span>
                <span>Upload Resume Document</span>
              </label>
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`min-h-[180px] sm:h-64 border-2 border-dashed rounded-xl p-4 flex flex-col items-center justify-center text-center cursor-pointer transition-all w-full ${
                  file
                    ? 'border-teal-500/40 bg-teal-500/5'
                    : 'border-white/[0.1] hover:border-teal-500/30 bg-navy-900/50 hover:bg-navy-800/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc,.txt,.md"
                  onChange={handleFileChange}
                  className="hidden"
                />

                {file ? (
                  <div className="flex flex-col items-center space-y-2.5">
                    <div className="h-12 w-12 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center border border-teal-500/20">
                      <CheckCircle2 className="h-6 w-6" />
                    </div>
                    <div className="max-w-full px-2">
                      <p className="font-bold text-slate-200 text-xs sm:text-sm truncate max-w-[200px]">{file.name}</p>
                      <p className="text-[11px] text-slate-500 font-medium mt-0.5">{(file.size / 1024).toFixed(1)} KB • Click to change</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-2.5">
                    <div className="h-12 w-12 rounded-xl bg-navy-700 text-slate-400 flex items-center justify-center border border-white/[0.06]">
                      <Upload className="h-6 w-6" />
                    </div>
                    <div className="px-2">
                      <p className="text-slate-300 font-bold text-xs sm:text-sm">Click to upload or drag & drop</p>
                      <p className="text-[11px] text-slate-500 mt-1 font-medium">PDF, DOCX, TXT, or MD</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Job Description Textarea */}
            <div className="space-y-2.5 w-full">
              <label className="block text-xs sm:text-sm font-bold text-slate-300 flex items-center gap-2">
                <span className="h-5 w-5 rounded-md bg-teal-500/20 text-teal-400 text-[11px] font-extrabold flex items-center justify-center border border-teal-500/30">2</span>
                <span>Target Job Description</span>
              </label>
              <textarea
                rows={7}
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job posting, key requirements, qualifications, and duties here..."
                className="w-full min-h-[180px] sm:h-64 p-3.5 sm:p-4 rounded-xl bg-navy-900 border border-white/[0.08] focus:border-teal-500/40 focus:ring-2 focus:ring-teal-500/15 text-slate-200 placeholder-slate-600 text-xs sm:text-sm resize-none font-medium outline-none transition"
              />
            </div>
          </div>

          {/* Submit CTA */}
          <div className="flex justify-center pt-2 sm:pt-4 w-full">
            <button
              type="submit"
              disabled={!file || !jobDescription.trim() || isLoading}
              className={`w-full sm:w-auto px-8 sm:px-10 py-3.5 sm:py-4 flex items-center justify-center space-x-2.5 rounded-xl font-bold text-xs sm:text-base transition-all duration-200 ${
                !file || !jobDescription.trim() || isLoading
                  ? 'bg-navy-700 text-slate-600 cursor-not-allowed border border-white/[0.06]'
                  : 'btn-primary-serio'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
                  <span>Running Multi-Agent Pipeline...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 sm:h-5 sm:w-5" />
                  <span>Analyze & Optimize Resume</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Pipeline Indicator */}
        <div className="flex items-center justify-center gap-3 pt-2">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-600 font-medium">
            <span className="h-1 w-1 rounded-full bg-teal-500/40"></span>
            ATS Scoring
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-slate-600 font-medium">
            <span className="h-1 w-1 rounded-full bg-teal-500/40"></span>
            Skill Gap Analysis
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-slate-600 font-medium">
            <span className="h-1 w-1 rounded-full bg-teal-500/40"></span>
            STAR Rewriter
          </div>
          <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-slate-600 font-medium">
            <span className="h-1 w-1 rounded-full bg-teal-500/40"></span>
            Interview Prep
          </div>
          <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-slate-600 font-medium">
            <span className="h-1 w-1 rounded-full bg-indigo-500/40"></span>
            RAG Career Coach
          </div>
        </div>
      </div>
    </div>
  );
}
