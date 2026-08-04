import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Bot, RotateCcw } from 'lucide-react';

export default function Navbar({ onReset }) {
  const [isVisible, setIsVisible] = useState(true);
  const lastScrollY = useRef(0);
  const scrollTimeout = useRef(null);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      // Clear existing scroll timeout
      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }

      // Hide navbar when scrolling down past 60px
      if (currentScrollY > lastScrollY.current && currentScrollY > 60) {
        setIsVisible(false);
      } else {
        // Show navbar when scrolling up
        setIsVisible(true);
      }

      // Re-appear smoothly when scrolling stops (after 300ms pause)
      scrollTimeout.current = setTimeout(() => {
        setIsVisible(true);
      }, 350);

      lastScrollY.current = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }
    };
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 w-full bg-white/95 backdrop-blur-md border-b border-slate-200/80 transition-transform duration-300 ease-in-out ${
        isVisible ? 'translate-y-0 shadow-sm' : '-translate-y-full shadow-none'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onReset}>
          <div className="h-9 w-9 rounded-xl bg-[#069494] flex items-center justify-center text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xl font-extrabold text-[#0F172A] tracking-tight">
              Resumizer<span className="text-[#069494]">.</span>
            </span>
            <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full bg-[#F59E0B]/15 text-[#D97706] border border-[#F59E0B]/30 text-[10px] font-bold uppercase tracking-wider">
              AI Multi-Agent
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-100/80 border border-slate-200 text-xs font-semibold text-[#069494]">
            <span className="h-2 w-2 rounded-full bg-[#14B8A6] animate-pulse"></span>
            <Bot className="h-4 w-4 text-[#069494]" />
            <span>NVIDIA Multi-Agent Engine</span>
          </div>
          
          {onReset && (
            <button
              onClick={onReset}
              className="btn-secondary-serio flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold"
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
