import React from 'react';
import { Award, CheckCircle, AlertTriangle } from 'lucide-react';

export default function ATSScoreCard({ atsScore }) {
  if (!atsScore) return null;

  return (
    <div className="material-card p-5 sm:p-7 space-y-6 w-full">
      <div className="flex flex-col lg:flex-row items-center justify-between gap-6 pb-6 border-b border-slate-200/80">
        {/* Overall Score Meter */}
        <div className="flex flex-col sm:flex-row items-center text-center sm:text-left space-y-3 sm:space-y-0 sm:space-x-5 w-full lg:w-auto">
          <div className="h-20 w-20 sm:h-24 sm:w-24 rounded-2xl border border-[#069494]/30 bg-[#14B8A6]/10 flex flex-col items-center justify-center font-extrabold shrink-0 text-[#069494] shadow-xs">
            <span className="text-2xl sm:text-3xl font-extrabold tracking-tight">{atsScore.overall_score}</span>
            <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-widest text-slate-500">/ 100</span>
          </div>
          <div>
            <div className="flex items-center justify-center sm:justify-start space-x-2">
              <Award className="h-5 w-5 text-[#069494]" />
              <h2 className="text-lg sm:text-xl font-extrabold text-[#0F172A]">Overall ATS Match Score</h2>
            </div>
            <p className="text-slate-600 text-xs sm:text-sm mt-1 max-w-md font-medium leading-relaxed">
              {atsScore.breakdown_summary}
            </p>
          </div>
        </div>

        {/* Metric Progress Bars */}
        <div className="w-full lg:w-80 space-y-3">
          <div>
            <div className="flex justify-between text-xs font-bold mb-1 text-slate-700">
              <span>Keyword Match</span>
              <span className="text-[#069494]">{atsScore.keyword_match_score}%</span>
            </div>
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div className="h-full bg-[#14B8A6] rounded-full transition-all duration-500" style={{ width: `${atsScore.keyword_match_score}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-bold mb-1 text-slate-700">
              <span>Experience Alignment</span>
              <span className="text-[#069494]">{atsScore.experience_match_score}%</span>
            </div>
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div className="h-full bg-[#14B8A6] rounded-full transition-all duration-500" style={{ width: `${atsScore.experience_match_score}%` }}></div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-bold mb-1 text-slate-700">
              <span>Formatting & Structure</span>
              <span className="text-[#069494]">{atsScore.formatting_score}%</span>
            </div>
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div className="h-full bg-[#14B8A6] rounded-full transition-all duration-500" style={{ width: `${atsScore.formatting_score}%` }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Keywords Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Matched Keywords */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircle className="h-4 w-4 text-[#069494]" />
            <h4 className="font-bold text-xs sm:text-sm text-[#0F172A]">Matched Keywords ({atsScore.matched_keywords?.length || 0})</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.matched_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-lg text-[11px] sm:text-xs font-semibold bg-[#069494] text-white shadow-2xs">
                {kw}
              </span>
            ))}
          </div>
        </div>

        {/* Missing Keywords */}
        <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200">
          <div className="flex items-center space-x-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-[#D97706]" />
            <h4 className="font-bold text-xs sm:text-sm text-[#D97706]">Missing Critical Keywords ({atsScore.missing_keywords?.length || 0})</h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.missing_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-lg text-[11px] sm:text-xs font-semibold bg-[#F59E0B] text-white shadow-2xs">
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
