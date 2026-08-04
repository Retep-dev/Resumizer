import React from 'react';
import { Award, CheckCircle, AlertTriangle } from 'lucide-react';

export default function ATSScoreCard({ atsScore }) {
  if (!atsScore) return null;

  return (
    <div className="card-panel p-4 sm:p-6 rounded-3xl space-y-6 w-full">
      <div className="flex flex-col lg:flex-row items-center justify-between gap-6 pb-6 border-b border-slate-200">
        {/* Overall Score Meter */}
        <div className="flex flex-col sm:flex-row items-center text-center sm:text-left space-y-3 sm:space-y-0 sm:space-x-5 w-full lg:w-auto">
          <div className="h-20 w-20 sm:h-24 sm:w-24 rounded-2xl border-2 border-[#069494] bg-[#14B8A6]/15 flex flex-col items-center justify-center font-extrabold shrink-0 text-[#069494] shadow-sm">
            <span className="text-2xl sm:text-3xl">{atsScore.overall_score}</span>
            <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-widest text-slate-500">/ 100</span>
          </div>
          <div>
            <div className="flex items-center justify-center sm:justify-start space-x-2">
              <Award className="h-5 w-5 text-[#069494]" />
              <h2 className="text-lg sm:text-xl font-extrabold text-[#069494]">Overall ATS Match Score</h2>
            </div>
            <p className="text-slate-600 text-xs sm:text-sm mt-1 max-w-md font-medium">
              {atsScore.breakdown_summary}
            </p>
          </div>
        </div>

        {/* Metric Progress Bars (Accent #14B8A6 progress fill) */}
        <div className="w-full lg:w-80 space-y-3">
          <div>
            <div className="flex justify-between text-xs font-bold mb-1 text-slate-700">
              <span>Keyword Match</span>
              <span className="text-[#069494]">{atsScore.keyword_match_score}%</span>
            </div>
            <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div className="h-full bg-[#14B8A6] rounded-full" style={{ width: `${atsScore.keyword_match_score}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-bold mb-1 text-slate-700">
              <span>Experience Alignment</span>
              <span className="text-[#069494]">{atsScore.experience_match_score}%</span>
            </div>
            <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div className="h-full bg-[#14B8A6] rounded-full" style={{ width: `${atsScore.experience_match_score}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-bold mb-1 text-slate-700">
              <span>Formatting & Structure</span>
              <span className="text-[#069494]">{atsScore.formatting_score}%</span>
            </div>
            <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div className="h-full bg-[#14B8A6] rounded-full" style={{ width: `${atsScore.formatting_score}%` }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Keywords Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Matched Keywords (Primary #069494) */}
        <div className="p-4 rounded-2xl bg-[#069494]/5 border border-[#069494]/30">
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircle className="h-4 w-4 text-[#069494]" />
            <h4 className="font-bold text-xs sm:text-sm text-[#069494]">Matched Keywords ({atsScore.matched_keywords?.length || 0})</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.matched_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-md text-[11px] sm:text-xs font-bold bg-[#069494] text-white">
                {kw}
              </span>
            ))}
          </div>
        </div>

        {/* Missing Keywords (Highlight #F59E0B) */}
        <div className="p-4 rounded-2xl bg-[#F59E0B]/5 border border-[#F59E0B]/30">
          <div className="flex items-center space-x-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-[#F59E0B]" />
            <h4 className="font-bold text-xs sm:text-sm text-[#F59E0B]">Missing Critical Keywords ({atsScore.missing_keywords?.length || 0})</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.missing_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-md text-[11px] sm:text-xs font-bold bg-[#F59E0B] text-white">
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
