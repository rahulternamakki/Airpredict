"use client";

import { useState, useRef, useEffect } from 'react';
import { chatWithAgent, getAgentSuggestions } from '@/lib/api';
import { Send, User, Bot, Sparkles, Info, ArrowRight } from 'lucide-react';

export default function AssistantPage() {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([]);
  const [input, setInput] = useState('');
  const [agentType, setAgentType] = useState('vayu'); // vayu or delphi
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getAgentSuggestions(agentType)
      .then(res => setSuggestions(res.data || []))
      .catch(() => setSuggestions([
        "What is the health advisory for today?",
        "Why is the AQI high in East Delhi?",
        "Explain the impact of traffic reduction.",
        "What are the GRAP-4 measures?"
      ]));
  }, [agentType]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (msg: string = input) => {
    if (!msg.trim()) return;

    const newMsg: { role: 'user', content: string } = { role: 'user', content: msg };
    setMessages(prev => [...prev, newMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await chatWithAgent({
        message: msg,
        agent_type: agentType,
        history: messages
      });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "I'm having trouble connecting to my brain right now. Please try again later." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-160px)] flex flex-col gap-6 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between bg-white p-2 rounded-2xl border border-gray-100 shadow-sm">
        <div className="flex gap-2 p-1 bg-gray-50 rounded-xl flex-1">
          <button 
            onClick={() => setAgentType('vayu')}
            className={`flex-1 py-3 px-6 rounded-lg font-bold transition-all ${agentType === 'vayu' ? 'bg-green-600 text-white shadow-lg shadow-green-200' : 'text-gray-500 hover:text-gray-700'}`}
          >
            VAYU (Health Assistant)
          </button>
          <button 
            onClick={() => setAgentType('delphi')}
            className={`flex-1 py-3 px-6 rounded-lg font-bold transition-all ${agentType === 'delphi' ? 'bg-blue-600 text-white shadow-lg shadow-blue-200' : 'text-gray-500 hover:text-gray-700'}`}
          >
            DELPHI (Policy Advisor)
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden bg-white rounded-[2.5rem] border border-gray-100 shadow-sm flex flex-col h-full relative">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-10 space-y-8 no-scrollbar">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-6 opacity-40 grayscale select-none">
              <div className="p-6 bg-gray-50 rounded-full">
                <Bot size={64} className="text-gray-400" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold">Hello! I am {agentType === 'vayu' ? 'Vayu' : 'Delphi'}.</h3>
                <p className="max-w-sm">Ask me anything about air quality, health impacts, or policy measures in Delhi.</p>
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex gap-4 max-w-[80%] ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`p-3 h-fit rounded-2xl ${m.role === 'user' ? 'bg-gray-900 text-white' : (agentType === 'vayu' ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700')}`}>
                    {m.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                  </div>
                  <div className={`p-6 rounded-[2rem] text-lg leading-relaxed ${m.role === 'user' ? 'bg-gray-100 text-gray-900 rounded-tr-none' : (agentType === 'vayu' ? 'bg-green-50/50 text-gray-800 rounded-tl-none' : 'bg-blue-50/50 text-gray-800 rounded-tl-none')}`}>
                    {m.content}
                  </div>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="flex gap-4 max-w-[80%]">
                <div className={`p-3 h-fit rounded-2xl ${agentType === 'vayu' ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700'}`}>
                  <Bot size={20} className="animate-pulse" />
                </div>
                <div className="flex gap-1 items-center p-6 bg-gray-50 rounded-[2rem] rounded-tl-none">
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-8 space-y-6">
          <div className="flex overflow-x-auto gap-3 no-scrollbar pb-2">
            {suggestions.map((s, i) => (
              <button 
                key={i} 
                onClick={() => handleSend(s)}
                className="whitespace-nowrap px-5 py-2.5 bg-gray-50 text-gray-600 hover:bg-gray-100 rounded-full text-sm font-bold border border-gray-100 transition-all flex items-center gap-2"
              >
                {s}
                <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>

          <div className="relative group">
            <input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={`Ask ${agentType === 'vayu' ? 'Vayu' : 'Delphi'} something...`}
              className="w-full bg-gray-50 border-gray-100 focus:bg-white focus:border-gray-200 focus:ring-4 focus:ring-gray-100 rounded-[2.5rem] py-5 px-8 outline-none text-lg transition-all pr-16"
            />
            <button 
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="absolute right-3 top-3 bottom-3 aspect-square bg-gray-900 text-white rounded-full flex items-center justify-center hover:scale-105 active:scale-95 disabled:opacity-50 disabled:scale-100 transition-all shadow-lg"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
