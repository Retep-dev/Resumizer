import React, { useState } from 'react';
import { HelpCircle, ChevronDown, ChevronUp, Sparkles, UserCheck, AlertCircle } from 'lucide-react';

export default function InterviewPrep({ interviewPrep }) {
  const [openIndex, setOpenIndex] = useState(0); // Default open first question

  const rawQuestions = interviewPrep?.questions || interviewPrep?.interview_questions || [];

  const getTypeBadge = (type) => {
    switch (type) {
      case 'behavioral':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20">Behavioral</span>;
      case 'technical':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">Technical</span>;
      case 'gap_focused':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">Gap Focused</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-300">General</span>;
    }
  };

  const toggleAccordion = (idx) => {
    setOpenIndex(openIndex === idx ? null : idx);
  };

  return (
    <div className="glass-panel p-6 rounded-3xl border border-slate-800 space-y-6">
      <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
        <div className="h-10 w-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
          <HelpCircle className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Targeted Interview Questions & Prep</h3>
          <p className="text-xs text-slate-400">AI-generated behavioral, technical, and skill-gap questions with STAR strategy & model answers</p>
        </div>
      </div>

      {rawQuestions.length === 0 ? (
        <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-amber-400 mx-auto" />
          <h4 className="font-bold text-white text-sm">No Interview Questions Generated</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The Interview Preparation Agent did not return structured questions for this specific resume run. Please re-run the analysis or ask your AI Career Coach in the Chat tab for tailored interview prep!
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {rawQuestions.map((q, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden transition-all"
              >
                <button
                  onClick={() => toggleAccordion(idx)}
                  className="w-full p-4 text-left flex items-start justify-between gap-4 hover:bg-slate-800/40 transition"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center space-x-2">
                      {getTypeBadge(q.question_type)}
                      <span className="text-xs text-slate-400">Question #{idx + 1}</span>
                    </div>
                    <h4 className="font-semibold text-sm text-white leading-snug">
                      {q.question}
                    </h4>
                  </div>
                  <div className="text-slate-400 mt-1">
                    {isOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="p-4 bg-slate-950/60 border-t border-slate-800/80 space-y-4 text-xs">
                    {/* Context / Reason */}
                    {q.context_or_reason && (
                      <div className="space-y-1">
                        <span className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider">Why Asked</span>
                        <p className="text-slate-300">{q.context_or_reason}</p>
                      </div>
                    )}

                    {/* STAR Guide */}
                    {q.star_guide && (
                      <div className="space-y-1 p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                        <span className="font-semibold text-indigo-300 uppercase text-[10px] tracking-wider flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> STAR Answer Strategy
                        </span>
                        <p className="text-indigo-200">{q.star_guide}</p>
                      </div>
                    )}

                    {/* Sample Answer */}
                    {q.sample_answer && (
                      <div className="space-y-1 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                        <span className="font-semibold text-emerald-300 uppercase text-[10px] tracking-wider flex items-center gap-1">
                          <UserCheck className="h-3 w-3" /> High-Scoring Sample Response
                        </span>
                        <p className="text-emerald-200 leading-relaxed font-sans">{q.sample_answer}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
