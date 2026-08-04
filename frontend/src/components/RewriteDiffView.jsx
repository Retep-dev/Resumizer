import React, { useState } from 'react';
import { FileEdit, Copy, Check, Sparkles, ArrowRight } from 'lucide-react';

export default function RewriteDiffView({ rewriteReport }) {
  const [copiedIndex, setCopiedIndex] = useState(null);

  if (!rewriteReport) return null;

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="glass-panel p-4 sm:p-6 rounded-3xl border border-slate-800 space-y-6 w-full">
      <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
        <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
          <FileEdit className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-bold text-white">Tailored Resume & STAR Rewriter</h3>
          <p className="text-xs text-slate-400">Side-by-side original vs optimized bullet points incorporating metrics & missing skills</p>
        </div>
      </div>

      {/* Tailored Professional Summary */}
      {rewriteReport.tailored_summary && (
        <div className="p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/20 space-y-2">
          <div className="flex items-center space-x-2 text-indigo-300 font-semibold text-xs uppercase tracking-wider">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <span>Tailored Professional Summary</span>
          </div>
          <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">
            {rewriteReport.tailored_summary}
          </p>
        </div>
      )}

      {/* Experience Bullet Rewrites */}
      <div className="space-y-6">
        {rewriteReport.rewritten_experiences?.map((exp, expIdx) => (
          <div key={expIdx} className="space-y-3">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs sm:text-sm font-bold text-white">
              <span className="text-indigo-400">{exp.job_title}</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-300">{exp.company}</span>
            </div>

            <div className="space-y-3">
              {exp.rewritten_bullets?.map((bullet, bulletIdx) => {
                const uniqueId = `${expIdx}-${bulletIdx}`;
                return (
                  <div key={bulletIdx} className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 grid grid-cols-1 lg:grid-cols-2 gap-4 relative group">
                    {/* Original */}
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Original Bullet</span>
                      <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/40 p-3 rounded-xl border border-slate-800/60">
                        {bullet.original_bullet}
                      </p>
                    </div>

                    {/* Rewritten */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> STAR Rewritten Bullet
                        </span>
                        <button
                          onClick={() => handleCopy(bullet.rewritten_bullet, uniqueId)}
                          className="p-1 text-slate-400 hover:text-white rounded-md bg-slate-800 border border-slate-700 transition"
                          title="Copy bullet point"
                        >
                          {copiedIndex === uniqueId ? (
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </button>
                      </div>
                      <p className="text-xs text-emerald-200 font-medium leading-relaxed bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20">
                        {bullet.rewritten_bullet}
                      </p>
                      {bullet.added_keywords?.length > 0 && (
                        <div className="flex items-center space-x-1 text-[10px] text-slate-400 mt-1">
                          <span>Added Keywords:</span>
                          <div className="flex flex-wrap gap-1">
                            {bullet.added_keywords.map((kw, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
                                {kw}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
