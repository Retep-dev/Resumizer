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
      className={`fixed top-0 left-0 right-0 z-50 w-full bg-navy-950/90 backdrop-blur-xl border-b border-white/[0.06] transition-transform duration-300 ease-in-out ${
        isVisible ? 'translate-y-0' : '-translate-y-full'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo & Brand */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onReset}>
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center text-white shadow-glow-teal-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="flex items-center space-x-2.5">
            <span className="text-xl font-extrabold text-slate-100 tracking-tight font-display">
              Resumizer<span className="text-teal-400">.</span>
            </span>
            <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-md bg-teal-500/10 text-teal-400 border border-teal-500/20 text-[10px] font-bold uppercase tracking-wider">
              Multi-Agent AI
            </span>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center space-x-3">
          <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-navy-800 border border-white/[0.06] text-xs font-semibold text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-pulse-soft"></span>
            <Bot className="h-3.5 w-3.5 text-teal-400" />
            <span>NVIDIA NIM Engine</span>
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
