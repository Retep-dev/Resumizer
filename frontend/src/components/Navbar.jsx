import React from 'react';
import { Sparkles, Bot, RotateCcw } from 'lucide-react';

export default function Navbar({ onReset }) {
  return (
    <header className="sticky top-0 z-40 w-full bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onReset}>
          <div className="h-10 w-10 rounded-xl bg-[#069494] flex items-center justify-center shadow-md">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-2xl font-extrabold text-[#069494] tracking-tight">
              Resumizer
            </span>
            <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full bg-[#FF69B4] text-white text-[11px] font-bold uppercase tracking-wider">
              AI Multi-Agent
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="hidden md:flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-slate-50 border border-[#069494]/30 text-xs font-semibold text-[#069494]">
            <Bot className="h-4 w-4 text-[#069494]" />
            <span>NVIDIA Multi-Agent Engine</span>
          </div>
          
          {onReset && (
            <button
              onClick={onReset}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-[#069494] bg-slate-100 hover:bg-[#00F0FF]/20 rounded-lg border border-[#069494] transition"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>New Analysis</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
