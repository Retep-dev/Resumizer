import React from 'react';
import { Award, CheckCircle, AlertTriangle, FileText, Cpu } from 'lucide-react';

export default function ATSScoreCard({ atsScore }) {
  if (!atsScore) return null;

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10';
    if (score >= 60) return 'text-amber-400 border-amber-500/40 bg-amber-500/10';
    return 'text-rose-400 border-rose-500/40 bg-rose-500/10';
  };

  return (
    <div className="glass-panel p-6 rounded-3xl border border-slate-800 space-y-6">
      <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-6 border-b border-slate-800">
        {/* Overall Score Meter */}
        <div className="flex items-center space-x-5">
          <div className={`h-24 w-24 rounded-2xl border-2 flex flex-col items-center justify-center font-extrabold ${getScoreColor(atsScore.overall_score)}`}>
            <span className="text-3xl">{atsScore.overall_score}</span>
            <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">/ 100</span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <Award className="h-5 w-5 text-indigo-400" />
              <h2 className="text-xl font-bold text-white">Overall ATS Match Score</h2>
            </div>
            <p className="text-slate-400 text-sm mt-1 max-w-md">
              {atsScore.breakdown_summary}
            </p>
          </div>
        </div>

        {/* Metric Progress Bars */}
        <div className="w-full md:w-72 space-y-3">
          <div>
            <div className="flex justify-between text-xs font-semibold mb-1">
              <span className="text-slate-300">Keyword Match</span>
              <span className="text-indigo-400">{atsScore.keyword_match_score}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${atsScore.keyword_match_score}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-semibold mb-1">
              <span className="text-slate-300">Experience Alignment</span>
              <span className="text-purple-400">{atsScore.experience_match_score}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-purple-500 rounded-full" style={{ width: `${atsScore.experience_match_score}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-semibold mb-1">
              <span className="text-slate-300">Formatting & Structure</span>
              <span className="text-emerald-400">{atsScore.formatting_score}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${atsScore.formatting_score}%` }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Keywords Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Matched Keywords */}
        <div className="p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/20">
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            <h4 className="font-semibold text-sm text-emerald-300">Matched Keywords ({atsScore.matched_keywords?.length || 0})</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.matched_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                {kw}
              </span>
            ))}
          </div>
        </div>

        {/* Missing Keywords */}
        <div className="p-4 rounded-2xl bg-rose-500/5 border border-rose-500/20">
          <div className="flex items-center space-x-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-rose-400" />
            <h4 className="font-semibold text-sm text-rose-300">Missing Critical Keywords ({atsScore.missing_keywords?.length || 0})</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.missing_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-md text-xs font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20">
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
