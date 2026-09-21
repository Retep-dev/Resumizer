import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, User, Loader2, FileText, Briefcase } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '../api';

export default function CareerCoachChat({ sessionId }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your AI Career Coach. I have analyzed your resume and the target job description. Ask me anything about application strategy, salary negotiation, or interview answers!'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading || !sessionId) return;

    const userMsg = input.trim();
    setInput('');
    const newMessages = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);
    setLoading(true);

    try {
      const response = await api.post('/api/v1/chat', {
        session_id: sessionId,
        message: userMsg,
        chat_history: newMessages.slice(1, -1)
      });

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.data.reply }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I ran into an issue connecting to the Career Coach agent. Please try again.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="surface-card flex flex-col h-[600px] overflow-hidden w-full">
      {/* Header */}
      <div className="p-4 bg-navy-800 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center border border-teal-500/20">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-extrabold text-sm text-slate-100 flex items-center gap-2 font-display">
              AI Career Coach
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-500/15 text-indigo-300 font-bold border border-indigo-500/20">
                RAG
              </span>
            </h3>
            <p className="text-[11px] text-slate-500 font-medium">Grounded in your resume & target job description</p>
          </div>
        </div>

        {/* Context indicators */}
        <div className="hidden sm:flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-navy-900 border border-white/[0.06] text-[10px] text-slate-500 font-medium">
            <FileText className="h-3 w-3 text-teal-500" />
            <span>Resume</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-navy-900 border border-white/[0.06] text-[10px] text-slate-500 font-medium">
            <Briefcase className="h-3 w-3 text-indigo-400" />
            <span>Job Desc</span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-navy-950/50">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex items-start space-x-3 ${
              msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}
          >
            <div
              className={`h-7 w-7 rounded-lg flex items-center justify-center text-xs flex-shrink-0 font-bold ${
                msg.role === 'user'
                  ? 'bg-teal-500/15 text-teal-400 border border-teal-500/20'
                  : 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/20'
              }`}
            >
              {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            <div
              className={`p-3.5 rounded-2xl text-xs leading-relaxed max-w-[85%] font-medium ${
                msg.role === 'user'
                  ? 'bg-teal-600 text-white rounded-tr-sm font-semibold'
                  : 'bg-surface border border-white/[0.06] text-slate-300 rounded-tl-sm space-y-2'
              }`}
            >
              {msg.role === 'user' ? (
                msg.content
              ) : (
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-extrabold text-teal-400" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc list-inside space-y-1 my-1.5" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal list-inside space-y-1 my-1.5" {...props} />,
                    li: ({ node, ...props }) => <li className="text-slate-300" {...props} />,
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {loading && (
          <div className="flex items-start space-x-3">
            <div className="h-7 w-7 rounded-lg bg-indigo-500/15 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
              <Bot className="h-4 w-4" />
            </div>
            <div className="p-3.5 rounded-2xl bg-surface border border-white/[0.06] rounded-tl-sm flex items-center space-x-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-typing-dot-1"></span>
              <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-typing-dot-2"></span>
              <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-typing-dot-3"></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-3 bg-navy-800 border-t border-white/[0.06] flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your Career Coach a question..."
          className="flex-1 px-4 py-2.5 rounded-xl bg-navy-900 border border-white/[0.08] focus:border-teal-500/40 text-slate-200 text-xs focus:ring-2 focus:ring-teal-500/15 font-medium outline-none transition placeholder-slate-600"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className={`p-2.5 rounded-xl transition font-bold ${
            !input.trim() || loading
              ? 'bg-navy-700 text-slate-600 cursor-not-allowed'
              : 'btn-primary-serio'
          }`}
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
