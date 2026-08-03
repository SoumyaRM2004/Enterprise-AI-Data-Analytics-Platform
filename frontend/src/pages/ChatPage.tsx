import { useEffect, useState, useRef } from 'react';
import { chatbotAPI, datasetsAPI } from '../services/api';
import { Send, Plus, MessageSquare, Database, BarChart3, Brain, Table, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface Message {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  message_type?: string;
  sql_query?: string;
  query_result?: any;
  chart_config?: any;
  metadata?: any;
}

interface Session {
  id: number;
  title: string;
  dataset: string | number | null;
  dataset_name: string | null;
  session_type: string;
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadSessions();
    loadDatasets();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSessions = async () => {
    try {
      const { data } = await chatbotAPI.listSessions();
      setSessions(data.results || data);
    } catch {}
  };

  const loadDatasets = async () => {
    try {
      const { data } = await datasetsAPI.list({ status: 'ready' });
      const list = data.results || data;
      setDatasets(list);
      if (list.length > 0) {
        setSelectedDataset((prev) => prev || String(list[0].id));
      }
    } catch {}
  };

  const createSession = async (overrideDataset?: string | null) => {
    const dsId = overrideDataset !== undefined ? overrideDataset : selectedDataset;
    try {
      const { data } = await chatbotAPI.createSession({
        dataset: dsId || null,
        title: 'New Chat',
        session_type: dsId ? 'nl_to_sql' : 'general',
      });
      setSessions((prev) => [data, ...prev]);
      setCurrentSession(data);
      setMessages([]);
      return data;
    } catch {
      toast.error('Failed to create session');
      return null;
    }
  };

  const selectSession = async (session: Session) => {
    setCurrentSession(session);
    if (session.dataset) {
      setSelectedDataset(String(session.dataset));
    }
    try {
      const { data } = await chatbotAPI.getSession(session.id);
      setMessages(data.messages || []);
    } catch {}
  };

  const sendMessage = async (textOverride?: string) => {
    const textToSend = (textOverride || input).trim();
    if (!textToSend) return;

    let activeSession = currentSession;
    if (!activeSession) {
      activeSession = await createSession();
      if (!activeSession) return;
    }

    const userMsg: Message = {
      role: 'user',
      content: textToSend,
      message_type: 'text',
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsSending(true);

    try {
      const { data } = await chatbotAPI.sendMessage(activeSession.id, {
        message: userMsg.content,
        message_type: userMsg.message_type,
      });

      setMessages((prev) => [...prev, data.assistant_message]);

      if (data.user_message?.content) {
        setCurrentSession((prevSession) =>
          prevSession ? { ...prevSession, title: data.user_message.content.substring(0, 50) } : null
        );
      }
    } catch {
      toast.error('Failed to send message');
    } finally {
      setIsSending(false);
    }
  };

  const deleteSession = async (id: number) => {
    try {
      await chatbotAPI.deleteSession(id);
      setSessions(sessions.filter((s) => s.id !== id));
      if (currentSession?.id === id) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch {
      toast.error('Failed to delete session');
    }
  };

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-6">
      {/* Sidebar - Sessions */}
      <div className="w-72 bg-white rounded-xl border border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={() => createSession()}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>

        {/* Dataset selector */}
        <div className="p-4 border-b border-gray-200">
          <label className="text-xs font-medium text-gray-500 mb-1 block">Dataset Context</label>
          <select
            value={selectedDataset || ''}
            onChange={(e) => {
              const dsId = e.target.value || null;
              setSelectedDataset(dsId);
            }}
            className="input-field text-sm"
          >
            <option value="">Select dataset (optional)</option>
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>{ds.name}</option>
            ))}
          </select>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto p-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => selectSession(session)}
              className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                currentSession?.id === session.id
                  ? 'bg-primary-50 border border-primary-200'
                  : 'hover:bg-gray-50'
              }`}
            >
              <MessageSquare size={16} className={currentSession?.id === session.id ? 'text-primary-600' : 'text-gray-400'} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{session.title || 'Untitled'}</p>
                <p className="text-xs text-gray-500">{session.dataset_name || 'No dataset'}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                className="p-1 text-gray-400 hover:text-red-500"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 bg-white rounded-xl border border-gray-200 flex flex-col">
        {/* Messages view */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {!currentSession && messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center py-12">
                <Brain className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-gray-900 mb-2">AI Analytics Assistant</h2>
                <p className="text-gray-500 max-w-md mx-auto">
                  Ask questions about your data, generate SQL queries, create visualizations, and get AI-powered insights.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 justify-center">
                  {['Show monthly sales trends', 'Find top products', 'Detect anomalies', 'Predict next quarter'].map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-sm text-gray-700 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}>
                    {/* Text content */}
                    <p className="whitespace-pre-wrap text-sm">{msg.content}</p>

                    {/* SQL Query */}
                    {msg.sql_query && (
                      <div className="mt-3 p-3 bg-gray-800 rounded-lg">
                        <p className="text-xs text-green-400 mb-1">SQL Query:</p>
                        <pre className="text-sm text-green-300 font-mono overflow-x-auto">{msg.sql_query}</pre>
                      </div>
                    )}

                    {/* Query Results Table */}
                    {msg.query_result?.data?.rows && (
                      <div className="mt-3">
                        <p className="text-xs text-gray-500 mb-1">
                          Results: {msg.query_result.data.row_count} rows
                        </p>
                        <div className="overflow-x-auto max-h-64">
                          <table className="text-xs w-full">
                            <thead>
                              <tr className="border-b border-gray-200">
                                {msg.query_result.data.columns?.map((col: string) => (
                                  <th key={col} className="px-2 py-1 text-left font-medium">{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {msg.query_result.data.rows.slice(0, 50).map((row: any, i: number) => (
                                <tr key={i} className="border-b border-gray-100">
                                  {msg.query_result.data.columns?.map((col: string) => (
                                    <td key={col} className="px-2 py-1">{row[col] ?? '-'}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Chart suggestion */}
                    {msg.chart_config?.type && (
                      <div className="mt-3 flex items-center gap-2 p-2 bg-blue-50 rounded-lg">
                        <BarChart3 size={16} className="text-blue-600" />
                        <span className="text-sm text-blue-700">
                          Suggested: {msg.chart_config.type} chart
                          {msg.chart_config.x && ` (${msg.chart_config.x} vs ${msg.chart_config.y})`}
                        </span>
                      </div>
                    )}

                    {/* Key findings */}
                    {msg.metadata?.key_findings?.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-gray-500 mb-1">Key Findings:</p>
                        <ul className="list-disc list-inside text-sm">
                          {msg.metadata.key_findings.map((f: string, i: number) => (
                            <li key={i} className="text-gray-600">{f}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isSending && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask about your data..."
              className="input-field flex-1"
              disabled={isSending}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isSending}
              className="btn-primary px-4 disabled:opacity-50"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
