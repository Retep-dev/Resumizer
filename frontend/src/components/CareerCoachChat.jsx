import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, User, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';

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
      const response = await axios.post('/api/v1/chat', {
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
    <div className="card-panel rounded-3xl flex flex-col h-[580px] overflow-hidden w-full">
      {/* Header */}
      <div className="p-4 bg-[#069494] text-white flex items-center space-x-3">
        <div className="h-9 w-9 rounded-xl bg-white text-[#069494] flex items-center justify-center font-bold shadow-sm">
          <Bot className="h-5 w-5" />
        </div>
        <div>
          <h3 className="font-extrabold text-sm text-white flex items-center gap-2">
            AI Career Coach <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#14B8A6] text-white font-extrabold">RAG Active</span>
          </h3>
          <p className="text-[11px] text-slate-100 font-medium">Ask strategic questions backed by your resume & JD</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-50">
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
                  ? 'bg-[#069494] text-white'
                  : 'bg-[#069494] text-white'
              }`}
            >
              {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            <div
              className={`p-4 rounded-2xl text-xs leading-relaxed max-w-[85%] font-sans font-medium ${
                msg.role === 'user'
                  ? 'bg-[#069494] text-white rounded-tr-none whitespace-pre-wrap font-semibold'
                  : 'bg-white border border-slate-200 text-slate-900 rounded-tl-none space-y-2 shadow-sm'
              }`}
            >
              {msg.role === 'user' ? (
                msg.content
              ) : (
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-extrabold text-[#069494]" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc list-inside space-y-1 my-1.5" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal list-inside space-y-1 my-1.5" {...props} />,
                    li: ({ node, ...props }) => <li className="text-slate-800" {...props} />,
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-3">
            <div className="h-7 w-7 rounded-lg bg-[#069494] text-white flex items-center justify-center text-xs">
              <Bot className="h-4 w-4 animate-spin" />
            </div>
            <div className="p-3.5 rounded-2xl bg-white border border-slate-200 text-xs text-slate-600 font-semibold flex items-center space-x-2 shadow-sm">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-[#069494]" />
              <span>Coach is analyzing context & writing strategy...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-3 bg-white border-t border-slate-200 flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your Career Coach a question..."
          className="flex-1 px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-300 focus:border-[#069494] text-slate-900 text-xs focus:ring-2 focus:ring-[#14B8A6] font-medium"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className={`p-2.5 rounded-xl transition font-bold ${
            !input.trim() || loading
              ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
              : 'btn-primary'
          }`}
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
