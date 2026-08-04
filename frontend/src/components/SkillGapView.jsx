import React from 'react';
import { Target, AlertCircle, CheckCircle, Lightbulb } from 'lucide-react';

export default function SkillGapView({ skillGap }) {
  if (!skillGap) return null;

  return (
    <div className="card-panel p-4 sm:p-6 rounded-3xl space-y-6 w-full">
      <div className="flex items-center space-x-3 pb-4 border-b border-slate-200">
        <div className="h-10 w-10 rounded-xl bg-[#069494]/10 border border-[#069494]/30 flex items-center justify-center text-[#069494] shrink-0">
          <Target className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-extrabold text-[#069494]">Skill Gap Analysis</h3>
          <p className="text-xs text-slate-500 font-medium">Identified skill matches & missing prerequisites for target role</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hard Skills */}
        <div className="space-y-4">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Technical Hard Skills</h4>
          
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
            <div>
              <span className="text-xs text-[#069494] font-bold flex items-center gap-1.5 mb-2">
                <CheckCircle className="h-3.5 w-3.5" /> Matched Hard Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.matched_hard_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-bold bg-[#069494] text-white">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200">
              <span className="text-xs text-[#F59E0B] font-bold flex items-center gap-1.5 mb-2">
                <AlertCircle className="h-3.5 w-3.5" /> Missing Hard Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.missing_hard_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-bold bg-[#F59E0B] text-white">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Soft Skills */}
        <div className="space-y-4">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Soft & Leadership Skills</h4>
          
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
            <div>
              <span className="text-xs text-[#069494] font-bold flex items-center gap-1.5 mb-2">
                <CheckCircle className="h-3.5 w-3.5" /> Matched Soft Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.matched_soft_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-bold bg-[#069494] text-white">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200">
              <span className="text-xs text-[#F59E0B] font-bold flex items-center gap-1.5 mb-2">
                <AlertCircle className="h-3.5 w-3.5" /> Missing Soft Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.missing_soft_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-bold bg-[#F59E0B] text-white">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Priority Recommendations (Accent #14B8A6 background) */}
      {skillGap.priority_skill_recommendations?.length > 0 && (
        <div className="p-4 rounded-2xl bg-[#14B8A6]/15 border border-[#14B8A6]/50">
          <div className="flex items-center space-x-2 mb-2">
            <Lightbulb className="h-4 w-4 text-[#069494]" />
            <h4 className="font-extrabold text-sm text-[#069494]">Priority Skill Recommendations</h4>
          </div>
          <ul className="space-y-1 text-xs text-slate-800 font-semibold list-disc list-inside">
            {skillGap.priority_skill_recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
