import React from 'react';
import { Target, AlertCircle, CheckCircle, Lightbulb } from 'lucide-react';

export default function SkillGapView({ skillGap }) {
  if (!skillGap) return null;

  return (
    <div className="glass-panel p-6 rounded-3xl border border-slate-800 space-y-6">
      <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
        <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
          <Target className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Skill Gap Analysis</h3>
          <p className="text-xs text-slate-400">Identified skill matches & missing prerequisites for target role</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hard Skills */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider text-xs">Technical Hard Skills</h4>
          
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div>
              <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5 mb-2">
                <CheckCircle className="h-3.5 w-3.5" /> Matched Hard Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.matched_hard_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800">
              <span className="text-xs text-rose-400 font-semibold flex items-center gap-1.5 mb-2">
                <AlertCircle className="h-3.5 w-3.5" /> Missing Hard Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.missing_hard_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-rose-500/10 text-rose-300 border border-rose-500/20">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Soft Skills */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider text-xs">Soft & Leadership Skills</h4>
          
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div>
              <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5 mb-2">
                <CheckCircle className="h-3.5 w-3.5" /> Matched Soft Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.matched_soft_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800">
              <span className="text-xs text-amber-400 font-semibold flex items-center gap-1.5 mb-2">
                <AlertCircle className="h-3.5 w-3.5" /> Missing Soft Skills
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skillGap.missing_soft_skills?.map((skill, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-amber-500/10 text-amber-300 border border-amber-500/20">
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
        <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
          <div className="flex items-center space-x-2 mb-2">
            <Lightbulb className="h-4 w-4 text-indigo-400" />
            <h4 className="font-semibold text-sm text-indigo-300">Priority Skill Recommendations</h4>
          </div>
          <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
            {skillGap.priority_skill_recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
