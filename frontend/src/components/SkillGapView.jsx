import React from 'react';
import { Target, AlertCircle, CheckCircle, Lightbulb } from 'lucide-react';

export default function SkillGapView({ skillGap }) {
  if (!skillGap) return null;

  return (
    <div className="surface-card p-5 sm:p-7 space-y-6 w-full">
      {/* Section Header */}
      <div className="flex items-center space-x-3 pb-4 border-b border-white/[0.06]">
        <div className="h-9 w-9 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 shrink-0">
          <Target className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-extrabold text-slate-100 font-display">Skill Gap Analysis</h3>
          <p className="text-xs text-slate-500 font-medium">Skill matches & missing prerequisites for target role</p>
        </div>
      </div>

      {/* Skills Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Hard Skills */}
        <div className="space-y-3">
          <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Technical Hard Skills</h4>

          <div className="p-4 rounded-xl surface-inner space-y-4">
            <div>
              <span className="text-xs text-teal-400 font-bold flex items-center gap-1.5 mb-2.5">
                <CheckCircle className="h-3.5 w-3.5" /> Matched
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.matched_hard_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-semibold bg-teal-500/15 text-teal-300 border border-teal-500/20">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-white/[0.06]">
              <span className="text-xs text-amber-400 font-bold flex items-center gap-1.5 mb-2.5">
                <AlertCircle className="h-3.5 w-3.5" /> Missing
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.missing_hard_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/20">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Soft Skills */}
        <div className="space-y-3">
          <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Soft & Leadership Skills</h4>

          <div className="p-4 rounded-xl surface-inner space-y-4">
            <div>
              <span className="text-xs text-teal-400 font-bold flex items-center gap-1.5 mb-2.5">
                <CheckCircle className="h-3.5 w-3.5" /> Matched
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.matched_soft_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-semibold bg-teal-500/15 text-teal-300 border border-teal-500/20">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-white/[0.06]">
              <span className="text-xs text-amber-400 font-bold flex items-center gap-1.5 mb-2.5">
                <AlertCircle className="h-3.5 w-3.5" /> Missing
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.missing_soft_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/20">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Priority Recommendations */}
      {skillGap.priority_skill_recommendations?.length > 0 && (
        <div className="p-4 rounded-xl surface-inner border-l-2 border-l-teal-500">
          <div className="flex items-center space-x-2 mb-2.5">
            <Lightbulb className="h-4 w-4 text-teal-400" />
            <h4 className="font-extrabold text-sm text-slate-200">Priority Recommendations</h4>
          </div>
          <ul className="space-y-1.5 text-xs text-slate-400 font-medium list-disc list-inside">
            {skillGap.priority_skill_recommendations.map((rec, i) => (
              <li key={i} className="leading-relaxed">{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
