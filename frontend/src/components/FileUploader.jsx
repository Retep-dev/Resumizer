import React, { useState, useRef } from 'react';
import { Upload, CheckCircle2, Sparkles, Loader2, AlertCircle } from 'lucide-react';

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
    <div className="w-full max-w-4xl mx-auto py-4 sm:py-8 px-3 sm:px-4 overflow-x-hidden">
      <div className="text-center mb-6 sm:mb-10 w-full">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#14B8A6]/10 border border-[#14B8A6]/30 text-[#069494] text-xs font-bold uppercase tracking-wider mb-3">
          <Sparkles className="h-3.5 w-3.5" />
          <span>AI Resume Optimization & Career Coach</span>
        </div>

        <h1 className="text-2xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-[#0F172A] mb-3 sm:mb-4 leading-tight break-words max-w-full">
          Optimize Your Resume for <br className="hidden sm:inline" />
          <span className="text-[#069494]">
            Maximum ATS Match & Impact
          </span>
        </h1>
        <p className="text-slate-600 text-xs sm:text-base leading-relaxed max-w-2xl mx-auto px-1 break-words font-medium">
          Upload your resume and paste your target job description. Our 5-agent pipeline will score your ATS match, identify skill gaps, rewrite bullets using the STAR method, and generate custom interview prep.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-3.5 sm:p-4 rounded-xl bg-red-50 border border-red-200 flex items-center space-x-2.5 text-red-700 text-xs sm:text-sm font-medium">
          <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 flex-shrink-0 text-red-500" />
          <span className="break-words">{error}</span>
        </div>
      )}

      <div className="material-card p-5 sm:p-8 space-y-6">
        <form onSubmit={handleSubmit} className="space-y-6 w-full">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6 w-full">
            {/* File Upload Zone */}
            <div className="space-y-2 w-full">
              <label className="block text-xs sm:text-sm font-bold text-slate-800 flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-[#069494] text-white text-[11px] font-extrabold flex items-center justify-center">1</span>
                <span>Upload Resume Document</span>
              </label>
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`min-h-[180px] sm:h-64 border-2 border-dashed rounded-2xl p-4 flex flex-col items-center justify-center text-center cursor-pointer transition-all w-full ${
                  file
                    ? 'border-[#069494] bg-[#14B8A6]/10'
                    : 'border-slate-300 hover:border-[#069494] bg-slate-50 hover:bg-slate-100/60'
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
                  <div className="flex flex-col items-center space-y-2">
                    <div className="h-12 w-12 rounded-full bg-[#069494] text-white flex items-center justify-center shadow-sm">
                      <CheckCircle2 className="h-6 w-6" />
                    </div>
                    <div className="max-w-full px-2">
                      <p className="font-bold text-[#0F172A] text-xs sm:text-sm truncate max-w-[200px]">{file.name}</p>
                      <p className="text-[11px] text-slate-500 font-medium mt-0.5">{(file.size / 1024).toFixed(1)} KB • Click to change</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-2">
                    <div className="h-12 w-12 rounded-full bg-[#069494]/10 text-[#069494] flex items-center justify-center">
                      <Upload className="h-6 w-6" />
                    </div>
                    <div className="px-2">
                      <p className="text-slate-800 font-bold text-xs sm:text-sm">Click to upload or drag & drop</p>
                      <p className="text-[11px] text-slate-500 mt-1 font-medium">Supports PDF, DOCX, TXT format</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Job Description Textarea */}
            <div className="space-y-2 w-full">
              <label className="block text-xs sm:text-sm font-bold text-slate-800 flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-[#069494] text-white text-[11px] font-extrabold flex items-center justify-center">2</span>
                <span>Target Job Description</span>
              </label>
              <textarea
                rows={7}
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job posting, key requirements, qualifications, and duties here..."
                className="w-full min-h-[180px] sm:h-64 p-3.5 sm:p-4 rounded-2xl bg-slate-50 border border-slate-300 focus:border-[#069494] focus:ring-2 focus:ring-[#14B8A6]/30 text-slate-900 placeholder-slate-400 text-xs sm:text-sm resize-none font-medium outline-none transition"
              />
            </div>
          </div>

          {/* Submit CTA */}
          <div className="flex justify-center pt-2 sm:pt-4 w-full">
            <button
              type="submit"
              disabled={!file || !jobDescription.trim() || isLoading}
              className={`w-full sm:w-auto px-8 sm:px-10 py-3.5 sm:py-4 flex items-center justify-center space-x-2.5 ${
                !file || !jobDescription.trim() || isLoading
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-300 rounded-xl font-bold text-xs sm:text-base'
                  : 'btn-primary-serio text-xs sm:text-base'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin text-white" />
                  <span>Running Multi-Agent Pipeline...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
                  <span>Analyze & Optimize Resume</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
