import React from 'react';
import { Award, CheckCircle, AlertTriangle } from 'lucide-react';

function ScoreGauge({ score }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  // Color stops based on score
  const getScoreColor = (s) => {
    if (s >= 75) return { stroke: '#14B8A6', bg: 'text-teal-400', label: 'Strong Match' };
    if (s >= 50) return { stroke: '#F59E0B', bg: 'text-amber-400', label: 'Moderate Match' };
    return { stroke: '#EF4444', bg: 'text-red-400', label: 'Needs Work' };
  };

  const config = getScoreColor(score);

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg className="transform -rotate-90" width="140" height="140" viewBox="0 0 120 120">
        {/* Background ring */}
        <circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="10"
        />
        {/* Score ring */}
        <circle
          cx="60" cy="60" r={radius}
          fill="none"
          stroke={config.stroke}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="animate-gauge-fill transition-all duration-1000 ease-out"
          style={{ '--gauge-offset': offset }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl sm:text-4xl font-extrabold tracking-tight ${config.bg}`}>
          {score}
        </span>
        <span className="text-[9px] uppercase font-bold tracking-widest text-slate-500 mt-0.5">
          / 100
        </span>
      </div>
    </div>
  );
}

function MetricBar({ label, value, color = 'teal' }) {
  const colorMap = {
    teal: { bar: 'bg-teal-500', text: 'text-teal-400' },
    indigo: { bar: 'bg-indigo-500', text: 'text-indigo-400' },
    amber: { bar: 'bg-amber-500', text: 'text-amber-400' },
  };
  const c = colorMap[color] || colorMap.teal;

  return (
    <div>
      <div className="flex justify-between text-xs font-semibold mb-1.5">
        <span className="text-slate-400">{label}</span>
        <span className={c.text}>{value}%</span>
      </div>
      <div className="h-2 w-full bg-white/[0.04] rounded-full overflow-hidden border border-white/[0.06]">
        <div
          className={`h-full ${c.bar} rounded-full transition-all duration-700 ease-out`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export default function ATSScoreCard({ atsScore }) {
  if (!atsScore) return null;

  return (
    <div className="surface-card p-5 sm:p-7 space-y-6 w-full">
      {/* Header Section — Score + Metrics */}
      <div className="flex flex-col lg:flex-row items-center justify-between gap-8 pb-6 border-b border-white/[0.06]">
        {/* Overall Score Gauge */}
        <div className="flex flex-col sm:flex-row items-center text-center sm:text-left space-y-4 sm:space-y-0 sm:space-x-6 w-full lg:w-auto">
          <ScoreGauge score={atsScore.overall_score} />
          <div>
            <div className="flex items-center justify-center sm:justify-start space-x-2 mb-1.5">
              <Award className="h-5 w-5 text-teal-400" />
              <h2 className="text-lg sm:text-xl font-extrabold text-slate-100 font-display">
                Overall ATS Match
              </h2>
            </div>
            <p className="text-slate-400 text-xs sm:text-sm max-w-md font-medium leading-relaxed">
              {atsScore.breakdown_summary}
            </p>
          </div>
        </div>

        {/* Metric Progress Bars */}
        <div className="w-full lg:w-80 space-y-3.5">
          <MetricBar label="Keyword Match" value={atsScore.keyword_match_score} color="teal" />
          <MetricBar label="Experience Alignment" value={atsScore.experience_match_score} color="teal" />
          <MetricBar label="Formatting & Structure" value={atsScore.formatting_score} color="indigo" />
        </div>
      </div>

      {/* Keywords Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Matched Keywords */}
        <div className="p-4 rounded-xl surface-inner">
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircle className="h-4 w-4 text-teal-400" />
            <h4 className="font-bold text-xs sm:text-sm text-slate-200">
              Matched Keywords
              <span className="ml-1.5 text-slate-500 font-semibold">({atsScore.matched_keywords?.length || 0})</span>
            </h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.matched_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-md text-[11px] sm:text-xs font-semibold bg-teal-500/15 text-teal-300 border border-teal-500/20">
                {kw}
              </span>
            ))}
          </div>
        </div>

        {/* Missing Keywords */}
        <div className="p-4 rounded-xl surface-inner">
          <div className="flex items-center space-x-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <h4 className="font-bold text-xs sm:text-sm text-slate-200">
              Missing Keywords
              <span className="ml-1.5 text-slate-500 font-semibold">({atsScore.missing_keywords?.length || 0})</span>
            </h4>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {atsScore.missing_keywords?.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-md text-[11px] sm:text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/20">
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
