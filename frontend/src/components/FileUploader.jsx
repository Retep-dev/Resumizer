import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, Sparkles, Loader2, AlertCircle } from 'lucide-react';

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
    <div className="w-full max-w-4xl mx-auto py-4 sm:py-8 px-2 sm:px-4">
      <div className="text-center mb-6 sm:mb-10">
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-3 sm:mb-4">
          Supercharge Your Resume with <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
            AI Multi-Agent RAG Coaching
          </span>
        </h1>
        <p className="text-slate-400 text-sm sm:text-lg max-w-2xl mx-auto px-2">
          Upload your resume and paste your target job description. Our 5-agent pipeline will score your ATS match, identify skill gaps, rewrite bullets using the STAR method, and generate custom interview prep.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center space-x-3 text-red-400 text-xs sm:text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          {/* File Upload Zone */}
          <div className="space-y-2">
            <label className="block text-xs sm:text-sm font-semibold text-slate-200">
              1. Upload Resume (PDF / DOCX / TXT)
            </label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`min-h-[200px] sm:h-64 border-2 border-dashed rounded-2xl p-4 sm:p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                file
                  ? 'border-emerald-500/50 bg-emerald-500/5'
                  : 'border-slate-700 hover:border-indigo-500/60 bg-slate-900/60 hover:bg-slate-900'
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
                <div className="flex flex-col items-center space-y-2 sm:space-y-3">
                  <div className="h-12 w-12 sm:h-14 sm:w-14 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <CheckCircle2 className="h-6 w-6 sm:h-7 sm:w-7" />
                  </div>
                  <div>
                    <p className="font-semibold text-white text-xs sm:text-sm truncate max-w-[220px]">{file.name}</p>
                    <p className="text-[11px] sm:text-xs text-slate-400 mt-0.5">{(file.size / 1024).toFixed(1)} KB • Click to change</p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center space-y-2 sm:space-y-3">
                  <div className="h-12 w-12 sm:h-14 sm:w-14 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                    <Upload className="h-5 w-5 sm:h-6 sm:w-6" />
                  </div>
                  <div>
                    <p className="text-slate-200 font-medium text-xs sm:text-sm">Drag & drop your resume file here</p>
                    <p className="text-[11px] sm:text-xs text-slate-400 mt-1">Supports PDF, DOCX, TXT</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Job Description Textarea */}
          <div className="space-y-2">
            <label className="block text-xs sm:text-sm font-semibold text-slate-200">
              2. Target Job Description
            </label>
            <textarea
              rows={8}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job posting, key requirements, qualifications, and duties here..."
              className="w-full min-h-[200px] sm:h-64 p-4 rounded-2xl bg-slate-900/60 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder-slate-500 text-xs sm:text-sm resize-none"
            />
          </div>
        </div>

        {/* Submit CTA */}
        <div className="flex justify-center pt-2 sm:pt-4">
          <button
            type="submit"
            disabled={!file || !jobDescription.trim() || isLoading}
            className={`w-full sm:w-auto px-6 sm:px-8 py-3.5 sm:py-4 rounded-xl font-bold text-sm sm:text-lg flex items-center justify-center space-x-3 transition-all ${
              !file || !jobDescription.trim() || isLoading
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-xl glow-button'
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 sm:h-6 sm:w-6 animate-spin text-white" />
                <span>Running Multi-Agent Pipeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5 sm:h-6 sm:w-6 text-indigo-200" />
                <span>Analyze & Optimize Resume</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
