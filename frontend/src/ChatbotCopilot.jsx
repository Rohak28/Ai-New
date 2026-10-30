import { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  X, 
  Send, 
  Sparkles, 
  Minimize2, 
  Maximize2, 
  MessageSquare, 
  RefreshCw, 
  ChevronRight,
  ShieldAlert,
  HelpCircle,
  Cpu
} from 'lucide-react';

export default function ChatbotCopilot({ apiBase, activeReport }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `**Hello! I am your NeuroNest Automotive IVN AI Copilot.** 🚗⚡\n\nI am grounded in official automotive standards (ISO 11898-1/2, ISO 14229 UDS) and historical vehicle failure memory.\n\nYou can ask me anything about:\n- **Physical Layer Testing:** Rise/Fall time limits (> 200 ns), Bit Rate Tolerance (1998 - 2002 ns), Jitter, Cable Capacitance.\n- **Protocol & Network:** CAN, CAN-FD, LIN, Automotive Ethernet, DBC mapping, and bus-off recovery.\n- **Report Diagnostics:** Real-time root-cause explanations and step-by-step bench fixes for your uploaded reports.`
    }
  ]);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen && !isMinimized) {
      scrollToBottom();
      inputRef.current?.focus();
    }
  }, [messages, isOpen, isMinimized]);

  const defaultSuggestions = [
    "Why does rise time > 200 ns cause bit length expansion?",
    "What is the pass criteria for Bit Rate Tolerance?",
    "How do I fix a CAN Bus-Off state on an ECU?",
    "What are the ISO 11898-2 termination requirements?"
  ];

  const reportSuggestions = activeReport ? [
    `Analyze why test case failures occurred in Report #${activeReport?.metadata?.report_no || ''}`,
    "What is the recommended fix for the failed test cases in this report?",
    "Check if any ECU is out of specification in this run",
    "Why does rise time > 200 ns cause bit length expansion?"
  ] : defaultSuggestions;

  const handleSend = async (textToSend) => {
    const query = (textToSend || input).trim();
    if (!query || isLoading) return;

    setInput('');
    const newMessages = [...messages, { role: 'user', content: query }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const historyPayload = newMessages.slice(-6).map(m => ({
        role: m.role,
        content: m.content
      }));

      const res = await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          history: historyPayload,
          report_id: activeReport?.metadata?.report_no || null
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.reply || "No response received."
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: "⚠️ **Connection Error:** Unable to reach the AI Copilot endpoint. Please ensure the backend server is running on port 8001."
        }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ **Network Error:** ${err.message || "Failed to connect to backend server."}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        role: 'assistant',
        content: "Conversation history cleared. How can I help you with your IVN test or automotive standards questions today?"
      }
    ]);
  };

  // Helper to render bold and lists simply in messages
  const renderFormattedText = (text) => {
    return text.split('\n').map((line, idx) => {
      // Bold rendering
      const parts = line.split(/(\*\*.*?\*\*)/g);
      return (
        <span key={idx} className="block min-h-[1.2rem]">
          {parts.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={pIdx} className="font-bold text-slate-900">{part.slice(2, -2)}</strong>;
            }
            if (part.startsWith('- ') || part.startsWith('* ')) {
              return <span key={pIdx} className="inline-block pl-2 text-slate-700">• {part.slice(2)}</span>;
            }
            return <span key={pIdx}>{part}</span>;
          })}
        </span>
      );
    });
  };

  return (
    <>
      {/* Floating Launcher Button */}
      {!isOpen && (
        <button
          onClick={() => { setIsOpen(true); setIsMinimized(false); }}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-brand-accent text-white rounded-full shadow-2xl hover:shadow-indigo-500/40 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer group border border-white/20"
        >
          <div className="relative">
            <Bot className="w-6 h-6 text-white group-hover:rotate-12 transition-transform duration-200" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse border-2 border-slate-900"></span>
          </div>
          <div className="text-left">
            <div className="text-xs font-semibold uppercase tracking-wider text-blue-200 leading-none">Automotive AI</div>
            <div className="text-sm font-extrabold tracking-tight">IVN Copilot</div>
          </div>
          <Sparkles className="w-4 h-4 text-amber-300 ml-1" />
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div 
          className={`fixed bottom-6 right-6 z-50 bg-white/95 backdrop-blur-xl border border-slate-200/80 rounded-2xl shadow-2xl flex flex-col transition-all duration-300 overflow-hidden font-sans ${
            isMinimized 
              ? 'w-80 h-16' 
              : 'w-[440px] h-[640px] max-w-[calc(100vw-2rem)] max-h-[calc(100vh-4rem)]'
          }`}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-4 text-white flex items-center justify-between border-b border-white/10 select-none">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center shadow-md shadow-indigo-500/30">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-extrabold text-sm tracking-tight text-white">NeuroNest Copilot</h3>
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    RAG Grounded
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 font-medium">Automotive IVN & CAN Diagnostic Assistant</p>
              </div>
            </div>

            <div className="flex items-center gap-1 text-slate-400">
              <button 
                onClick={() => setIsMinimized(!isMinimized)} 
                className="p-1.5 hover:text-white hover:bg-white/10 rounded-lg transition-colors cursor-pointer"
                title={isMinimized ? "Expand" : "Minimize"}
              >
                {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
              </button>
              <button 
                onClick={() => setIsOpen(false)} 
                className="p-1.5 hover:text-white hover:bg-rose-500/20 hover:text-rose-300 rounded-lg transition-colors cursor-pointer"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Context Ribbon */}
          {!isMinimized && (
            <div className="bg-slate-100/90 px-4 py-2 border-b border-slate-200/80 flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 text-slate-600 truncate">
                <Cpu className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                <span className="font-semibold text-slate-700">Context:</span>
                {activeReport ? (
                  <span className="truncate text-indigo-700 font-bold bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                    Report #{activeReport?.metadata?.report_no || 'Active'} ({activeReport?.metadata?.project_name || 'IVN'})
                  </span>
                ) : (
                  <span className="text-slate-500 font-medium">General Automotive Standards Mode</span>
                )}
              </div>
              <button
                onClick={handleClearHistory}
                className="text-[11px] font-semibold text-slate-400 hover:text-slate-700 flex items-center gap-1 ml-2 transition-colors cursor-pointer"
                title="Reset conversation"
              >
                <RefreshCw className="w-3 h-3" />
                Reset
              </button>
            </div>
          )}

          {/* Messages Area */}
          {!isMinimized && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs leading-relaxed bg-slate-50/50">
              {messages.map((msg, index) => (
                <div 
                  key={index}
                  className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0 shadow-sm mt-0.5 text-white">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div 
                    className={`max-w-[85%] rounded-2xl p-3.5 shadow-sm ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-none font-medium'
                        : 'bg-white border border-slate-200/80 text-slate-700 rounded-tl-none font-normal'
                    }`}
                  >
                    {renderFormattedText(msg.content)}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-2.5 items-start">
                  <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0 shadow-sm mt-0.5 text-white">
                    <Bot className="w-4 h-4 animate-spin" />
                  </div>
                  <div className="bg-white border border-slate-200/80 rounded-2xl rounded-tl-none p-3.5 shadow-sm text-slate-500 flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-bounce"></span>
                    <span className="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.2s]"></span>
                    <span className="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-bounce [animation-delay:0.4s]"></span>
                    <span className="text-[11px] font-semibold text-slate-600 ml-1">Copilot reasoning with RAG context...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Quick Prompt Suggestions */}
          {!isMinimized && messages.length <= 2 && !isLoading && (
            <div className="px-3 py-2 bg-slate-100/70 border-t border-slate-200/60">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-500" />
                Suggested Questions
              </div>
              <div className="flex flex-col gap-1.5">
                {reportSuggestions.slice(0, 3).map((prompt, pIdx) => (
                  <button
                    key={pIdx}
                    onClick={() => handleSend(prompt)}
                    className="text-left text-[11px] text-slate-700 bg-white hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 border border-slate-200/80 rounded-lg px-2.5 py-1.5 transition-all truncate flex items-center justify-between group cursor-pointer font-medium"
                  >
                    <span className="truncate">{prompt}</span>
                    <ChevronRight className="w-3 h-3 text-slate-400 group-hover:text-indigo-600 group-hover:translate-x-0.5 transition-all shrink-0 ml-1" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Footer */}
          {!isMinimized && (
            <div className="p-3 bg-white border-t border-slate-200 flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about CAN, ISO standards, or this report..."
                disabled={isLoading}
                className="flex-1 bg-slate-100 border border-slate-300/80 rounded-xl px-3.5 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 transition-all font-medium disabled:opacity-50"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isLoading}
                className="w-9 h-9 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl flex items-center justify-center shadow-md hover:shadow-indigo-500/30 hover:scale-105 active:scale-95 disabled:opacity-40 disabled:hover:scale-100 transition-all cursor-pointer shrink-0"
                title="Send message (Enter)"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
