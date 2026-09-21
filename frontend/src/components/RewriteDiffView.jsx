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
    <div className="surface-card p-5 sm:p-7 space-y-6 w-full">
      {/* Section Header */}
      <div className="flex items-center space-x-3 pb-4 border-b border-white/[0.06]">
        <div className="h-9 w-9 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 shrink-0">
          <FileEdit className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-extrabold text-slate-100 font-display">Tailored Resume & STAR Rewriter</h3>
          <p className="text-xs text-slate-500 font-medium">Original vs optimized bullets with metrics & injected keywords</p>
        </div>
      </div>

      {/* Tailored Professional Summary */}
      {rewriteReport.tailored_summary && (
        <div className="p-4 rounded-xl surface-inner border-l-2 border-l-teal-500 space-y-2">
          <div className="flex items-center space-x-2 text-teal-400 font-extrabold text-[11px] uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Tailored Professional Summary</span>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-medium">
            {rewriteReport.tailored_summary}
          </p>
        </div>
      )}

      {/* Experience Bullet Rewrites */}
      <div className="space-y-6">
        {rewriteReport.rewritten_experiences?.map((exp, expIdx) => (
          <div key={expIdx} className="space-y-3">
            {/* Job Header */}
            <div className="flex flex-wrap items-center gap-2 text-sm font-extrabold">
              <span className="text-teal-400">{exp.job_title}</span>
              <span className="text-slate-600">·</span>
              <span className="text-slate-400">{exp.company}</span>
            </div>

            {/* Bullets */}
            <div className="space-y-3">
              {exp.rewritten_bullets?.map((bullet, bulletIdx) => {
                const uniqueId = `${expIdx}-${bulletIdx}`;
                return (
                  <div key={bulletIdx} className="p-4 rounded-xl surface-inner grid grid-cols-1 lg:grid-cols-2 gap-4 relative">
                    {/* Original */}
                    <div className="space-y-1.5">
                      <span className="text-[10px] uppercase font-bold text-slate-600 tracking-wider">Original</span>
                      <p className="text-xs text-slate-400 leading-relaxed bg-navy-950/50 p-3 rounded-lg border border-white/[0.04]">
                        {bullet.original_bullet}
                      </p>
                    </div>

                    {/* Arrow indicator (desktop only) */}
                    <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
                      <div className="h-7 w-7 rounded-full bg-navy-800 border border-white/[0.08] flex items-center justify-center">
                        <ArrowRight className="h-3.5 w-3.5 text-teal-400" />
                      </div>
                    </div>

                    {/* Rewritten */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold text-teal-400 tracking-wider flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> Optimized
                        </span>
                        <button
                          onClick={() => handleCopy(bullet.rewritten_bullet, uniqueId)}
                          className="p-1 text-slate-500 hover:text-teal-400 rounded-md bg-navy-800 border border-white/[0.06] hover:border-teal-500/30 transition"
                          title="Copy bullet point"
                        >
                          {copiedIndex === uniqueId ? (
                            <Check className="h-3.5 w-3.5 text-teal-400" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </button>
                      </div>
                      <p className="text-xs text-slate-200 font-semibold leading-relaxed bg-teal-500/5 p-3 rounded-lg border border-teal-500/15">
                        {bullet.rewritten_bullet}
                      </p>
                      {bullet.added_keywords?.length > 0 && (
                        <div className="flex items-center space-x-1.5 text-[10px] text-slate-500 font-medium mt-1">
                          <span>Keywords added:</span>
                          <div className="flex flex-wrap gap-1">
                            {bullet.added_keywords.map((kw, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-teal-500/15 text-teal-300 font-mono font-semibold text-[10px] border border-teal-500/20">
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
