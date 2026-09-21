import React, { useState } from 'react';
import { HelpCircle, ChevronDown, ChevronUp, Sparkles, UserCheck, AlertCircle } from 'lucide-react';

const typeBadgeConfig = {
  behavioral: { label: 'Behavioral', bg: 'bg-teal-500/15', text: 'text-teal-300', border: 'border-teal-500/20' },
  technical: { label: 'Technical', bg: 'bg-indigo-500/15', text: 'text-indigo-300', border: 'border-indigo-500/20' },
  gap_focused: { label: 'Gap Focused', bg: 'bg-amber-500/15', text: 'text-amber-300', border: 'border-amber-500/20' },
};

export default function InterviewPrep({ interviewPrep }) {
  const [openIndex, setOpenIndex] = useState(0);

  const rawQuestions = interviewPrep?.questions || interviewPrep?.interview_questions || [];

  const getTypeBadge = (type) => {
    const config = typeBadgeConfig[type] || { label: 'General', bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/20' };
    return (
      <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold ${config.bg} ${config.text} border ${config.border}`}>
        {config.label}
      </span>
    );
  };

  const toggleAccordion = (idx) => {
    setOpenIndex(openIndex === idx ? null : idx);
  };

  return (
    <div className="surface-card p-5 sm:p-7 space-y-6 w-full">
      {/* Section Header */}
      <div className="flex items-center space-x-3 pb-4 border-b border-white/[0.06]">
        <div className="h-9 w-9 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 shrink-0">
          <HelpCircle className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-extrabold text-slate-100 font-display">Interview Questions & Prep</h3>
          <p className="text-xs text-slate-500 font-medium">AI-generated questions with STAR strategy & model answers</p>
        </div>
      </div>

      {rawQuestions.length === 0 ? (
        <div className="p-8 rounded-xl surface-inner text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-amber-400 mx-auto" />
          <h4 className="font-bold text-slate-300 text-sm">No Interview Questions Generated</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto font-medium">
            The Interview Preparation Agent did not return structured questions for this run. Please re-run the analysis or ask your AI Career Coach in the Chat tab for tailored interview prep!
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {rawQuestions.map((q, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className={`rounded-xl surface-inner overflow-hidden transition-all ${
                  isOpen ? 'border-white/[0.1]' : ''
                }`}
              >
                <button
                  onClick={() => toggleAccordion(idx)}
                  className="w-full p-4 text-left flex items-start justify-between gap-4 hover:bg-white/[0.02] transition"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center space-x-2">
                      {getTypeBadge(q.question_type)}
                      <span className="text-[11px] font-semibold text-slate-600">Q{idx + 1}</span>
                    </div>
                    <h4 className="font-bold text-xs sm:text-sm text-slate-200 leading-snug">
                      {q.question}
                    </h4>
                  </div>
                  <div className={`text-slate-500 mt-1 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}>
                    <ChevronDown className="h-5 w-5" />
                  </div>
                </button>

                {isOpen && (
                  <div className="px-4 pb-4 space-y-3 text-xs animate-fade-in">
                    {/* Context / Reason */}
                    {q.context_or_reason && (
                      <div className="space-y-1 p-3 rounded-lg bg-navy-950/50 border border-white/[0.04]">
                        <span className="font-bold text-slate-500 uppercase text-[10px] tracking-wider">Why This Is Asked</span>
                        <p className="text-slate-400 font-medium leading-relaxed">{q.context_or_reason}</p>
                      </div>
                    )}

                    {/* STAR Guide */}
                    {q.star_guide && (
                      <div className="space-y-1 p-3 rounded-lg bg-teal-500/5 border border-teal-500/15">
                        <span className="font-extrabold text-teal-400 uppercase text-[10px] tracking-wider flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> STAR Answer Strategy
                        </span>
                        <p className="text-slate-300 font-semibold leading-relaxed">{q.star_guide}</p>
                      </div>
                    )}

                    {/* Sample Answer */}
                    {q.sample_answer && (
                      <div className="space-y-1 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/15">
                        <span className="font-extrabold text-indigo-400 uppercase text-[10px] tracking-wider flex items-center gap-1">
                          <UserCheck className="h-3 w-3" /> Sample Response
                        </span>
                        <p className="text-slate-300 font-medium leading-relaxed">{q.sample_answer}</p>
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
