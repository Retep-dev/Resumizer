import React, { useState } from 'react';
import { FileEdit, Copy, Check, Sparkles } from 'lucide-react';

export default function RewriteDiffView({ rewriteReport }) {
  const [copiedIndex, setCopiedIndex] = useState(null);

  if (!rewriteReport) return null;

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="material-card p-5 sm:p-7 space-y-6 w-full">
      <div className="flex items-center space-x-3 pb-4 border-b border-slate-200/80">
        <div className="h-9 w-9 rounded-xl bg-[#069494]/10 border border-[#069494]/30 flex items-center justify-center text-[#069494] shrink-0 shadow-xs">
          <FileEdit className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-extrabold text-[#0F172A]">Tailored Resume & STAR Rewriter</h3>
          <p className="text-xs text-slate-500 font-medium">Side-by-side original vs optimized bullet points incorporating metrics & missing skills</p>
        </div>
      </div>

      {/* Tailored Professional Summary */}
      {rewriteReport.tailored_summary && (
        <div className="p-4 rounded-xl bg-[#14B8A6]/10 border border-[#14B8A6]/30 space-y-2">
          <div className="flex items-center space-x-2 text-[#069494] font-extrabold text-xs uppercase tracking-wider">
            <Sparkles className="h-4 w-4 text-[#069494]" />
            <span>Tailored Professional Summary</span>
          </div>
          <p className="text-xs sm:text-sm text-slate-800 leading-relaxed font-medium">
            {rewriteReport.tailored_summary}
          </p>
        </div>
      )}

      {/* Experience Bullet Rewrites */}
      <div className="space-y-6">
        {rewriteReport.rewritten_experiences?.map((exp, expIdx) => (
          <div key={expIdx} className="space-y-3">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs sm:text-sm font-extrabold text-[#0F172A]">
              <span className="text-[#069494]">{exp.job_title}</span>
              <span className="text-slate-400">•</span>
              <span className="text-slate-700">{exp.company}</span>
            </div>

            <div className="space-y-3">
              {exp.rewritten_bullets?.map((bullet, bulletIdx) => {
                const uniqueId = `${expIdx}-${bulletIdx}`;
                return (
                  <div key={bulletIdx} className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-1 lg:grid-cols-2 gap-4 relative">
                    {/* Original */}
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Original Bullet</span>
                      <p className="text-xs text-slate-600 leading-relaxed bg-white p-3 rounded-lg border border-slate-200">
                        {bullet.original_bullet}
                      </p>
                    </div>

                    {/* Rewritten */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold text-[#069494] tracking-wider flex items-center gap-1">
                          <Sparkles className="h-3 w-3 text-[#069494]" /> STAR Rewritten Bullet
                        </span>
                        <button
                          onClick={() => handleCopy(bullet.rewritten_bullet, uniqueId)}
                          className="p-1 text-slate-500 hover:text-[#069494] rounded-md bg-white border border-slate-200 hover:border-slate-300 transition shadow-2xs"
                          title="Copy bullet point"
                        >
                          {copiedIndex === uniqueId ? (
                            <Check className="h-3.5 w-3.5 text-[#069494]" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </button>
                      </div>
                      <p className="text-xs text-slate-900 font-semibold leading-relaxed bg-[#14B8A6]/15 p-3 rounded-lg border border-[#14B8A6]/30">
                        {bullet.rewritten_bullet}
                      </p>
                      {bullet.added_keywords?.length > 0 && (
                        <div className="flex items-center space-x-1 text-[10px] text-slate-500 font-medium mt-1">
                          <span>Added Keywords:</span>
                          <div className="flex flex-wrap gap-1">
                            {bullet.added_keywords.map((kw, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-[#069494] text-white font-mono font-semibold">
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
