import React, { useState } from 'react';
import { HelpCircle, ChevronDown, ChevronUp, Sparkles, UserCheck, AlertCircle } from 'lucide-react';

export default function InterviewPrep({ interviewPrep }) {
  const [openIndex, setOpenIndex] = useState(0);

  const rawQuestions = interviewPrep?.questions || interviewPrep?.interview_questions || [];

  const getTypeBadge = (type) => {
    switch (type) {
      case 'behavioral':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#069494] text-white">Behavioral</span>;
      case 'technical':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#00F0FF] text-slate-900">Technical</span>;
      case 'gap_focused':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#FF69B4] text-white">Gap Focused</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">General</span>;
    }
  };

  const toggleAccordion = (idx) => {
    setOpenIndex(openIndex === idx ? null : idx);
  };

  return (
    <div className="card-panel p-4 sm:p-6 rounded-3xl space-y-6 w-full">
      <div className="flex items-center space-x-3 pb-4 border-b border-slate-200">
        <div className="h-10 w-10 rounded-xl bg-[#069494]/10 border border-[#069494]/30 flex items-center justify-center text-[#069494] shrink-0">
          <HelpCircle className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base sm:text-lg font-extrabold text-[#069494]">Targeted Interview Questions & Prep</h3>
          <p className="text-xs text-slate-500 font-medium">AI-generated behavioral, technical, and skill-gap questions with STAR strategy & model answers</p>
        </div>
      </div>

      {rawQuestions.length === 0 ? (
        <div className="p-8 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-[#FF69B4] mx-auto" />
          <h4 className="font-bold text-slate-800 text-sm">No Interview Questions Generated</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto font-medium">
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
                className="rounded-2xl bg-slate-50 border border-slate-200 overflow-hidden transition-all"
              >
                <button
                  onClick={() => toggleAccordion(idx)}
                  className="w-full p-4 text-left flex items-start justify-between gap-4 hover:bg-slate-100 transition"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center space-x-2">
                      {getTypeBadge(q.question_type)}
                      <span className="text-xs font-bold text-slate-500">Question #{idx + 1}</span>
                    </div>
                    <h4 className="font-extrabold text-xs sm:text-sm text-slate-900 leading-snug">
                      {q.question}
                    </h4>
                  </div>
                  <div className="text-slate-500 mt-1">
                    {isOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="p-4 bg-white border-t border-slate-200 space-y-4 text-xs">
                    {/* Context / Reason */}
                    {q.context_or_reason && (
                      <div className="space-y-1">
                        <span className="font-bold text-[#069494] uppercase text-[10px] tracking-wider">Why Asked</span>
                        <p className="text-slate-700 font-medium">{q.context_or_reason}</p>
                      </div>
                    )}

                    {/* STAR Guide */}
                    {q.star_guide && (
                      <div className="space-y-1 p-3 rounded-xl bg-[#00F0FF]/15 border border-[#00F0FF]/40">
                        <span className="font-extrabold text-[#069494] uppercase text-[10px] tracking-wider flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> STAR Answer Strategy
                        </span>
                        <p className="text-slate-900 font-semibold">{q.star_guide}</p>
                      </div>
                    )}

                    {/* Sample Answer */}
                    {q.sample_answer && (
                      <div className="space-y-1 p-3 rounded-xl bg-[#069494]/10 border border-[#069494]/30">
                        <span className="font-extrabold text-[#069494] uppercase text-[10px] tracking-wider flex items-center gap-1">
                          <UserCheck className="h-3 w-3" /> High-Scoring Sample Response
                        </span>
                        <p className="text-slate-800 font-semibold leading-relaxed font-sans">{q.sample_answer}</p>
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
