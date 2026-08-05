import { useEffect, useState, useRef } from 'react';
import { chatbotAPI, datasetsAPI } from '../services/api';
import {
  Send, Plus, MessageSquare, Database, BarChart3, Brain, Table as TableIcon,
  Trash2, Code, ChevronDown, Sparkles
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  PointElement, LineElement, ArcElement, Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, ArcElement, Title, Tooltip, Legend, Filler);

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
  const [expandedSql, setExpandedSql] = useState<Record<number, boolean>>({});
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

  const toggleSql = (idx: number) => {
    setExpandedSql((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const parseCleanContent = (rawContent: string): string => {
    if (!rawContent) return '';
    let content = rawContent.trim();
    if (content.startsWith('{') && content.endsWith('}')) {
      try {
        const parsed = JSON.parse(content);
        content = parsed.content || parsed.summary || parsed.message || '';
      } catch {}
    }
    return content.replace(/\*\*Executed Query:\*\*[\s\S]*/i, '').trim();
  };

  const getOrderedColumns = (cols: string[]): string[] => {
    if (!cols) return [];
    const stockIndex = cols.findIndex((c) =>
      ['stockcode', 'productid', 'itemid', 'sku'].some((term) => c.toLowerCase().includes(term))
    );
    const descIndex = cols.findIndex((c) =>
      ['description', 'productname', 'name', 'itemname', 'title'].some((term) => c.toLowerCase().includes(term))
    );

    if (stockIndex !== -1 && descIndex !== -1 && Math.abs(stockIndex - descIndex) > 1) {
      const reordered = [...cols];
      const descCol = reordered.splice(descIndex, 1)[0];
      const newStockIndex = reordered.findIndex((c) =>
        ['stockcode', 'productid', 'itemid', 'sku'].some((term) => c.toLowerCase().includes(term))
      );
      reordered.splice(newStockIndex + 1, 0, descCol);
      return reordered;
    }
    return cols;
  };

  const renderInteractiveChart = (msg: Message) => {
    const data = msg.query_result?.data;
    if (!data || !data.rows || data.rows.length === 0 || !data.columns) return null;

    const cols = data.columns;
    const config = msg.chart_config || {};

    let xCol = config.x && cols.includes(config.x) ? config.x : cols.find((c: string) => typeof data.rows[0][c] === 'string');
    if (!xCol) xCol = cols[0];

    let yCol = config.y && cols.includes(config.y) ? config.y : cols.find((c: string) => c !== xCol && typeof data.rows[0][c] === 'number');
    if (!yCol) yCol = cols.find((c: string) => c !== xCol);

    if (!xCol || !yCol || xCol === yCol) return null;

    const labels = data.rows.slice(0, 15).map((r: any) => String(r[xCol] ?? ''));
    const values = data.rows.slice(0, 15).map((r: any) => Number(r[yCol]) || 0);

    const chartData = {
      labels,
      datasets: [
        {
          label: yCol,
          data: values,
          backgroundColor: 'rgba(59, 130, 246, 0.65)',
          borderColor: 'rgb(37, 99, 235)',
          borderWidth: 1.5,
          borderRadius: 4,
        },
      ],
    };

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true },
      },
      scales: {
        x: { ticks: { font: { size: 10 }, maxRotation: 45 } },
        y: { ticks: { font: { size: 10 } } },
      },
    };

    const chartType = (config.type || 'bar').toLowerCase();

    return (
      <div className="mt-4 p-4 bg-gray-50/80 border border-gray-200 rounded-xl">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 size={15} className="text-primary-600" />
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Visualization: {yCol} by {xCol}
          </span>
        </div>
        <div className="h-52 w-full">
          {chartType === 'line' ? (
            <Line data={chartData} options={chartOptions} />
          ) : chartType === 'pie' ? (
            <Pie data={chartData} options={chartOptions} />
          ) : (
            <Bar data={chartData} options={chartOptions} />
          )}
        </div>
      </div>
    );
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
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!currentSession && messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center py-12">
                <Brain className="w-16 h-16 text-primary-500 mx-auto mb-4 animate-pulse" />
                <h2 className="text-xl font-semibold text-gray-900 mb-2">AI Analytics Assistant</h2>
                <p className="text-gray-500 max-w-md mx-auto text-sm">
                  Ask natural language questions about your data, generate SQL queries, create visualizations, and uncover AI insights.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 justify-center">
                  {['Show monthly sales trends', 'Find top 10 customers', 'Detect anomalies', 'Predict next quarter revenue'].map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="px-3.5 py-1.5 bg-gray-100 hover:bg-primary-50 hover:text-primary-700 hover:border-primary-200 border border-transparent rounded-full text-xs font-medium text-gray-700 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                const cleanContent = parseCleanContent(msg.content);
                const hasQueryResults = msg.query_result?.data?.rows?.length > 0;
                const orderedColumns = getOrderedColumns(msg.query_result?.data?.columns || []);

                return (
                  <div
                    key={idx}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl ${
                        isUser
                          ? 'bg-primary-600 text-white px-4 py-3'
                          : 'bg-white border border-gray-200 shadow-sm text-gray-900 p-5'
                      }`}
                    >
                      {/* User message */}
                      {isUser ? (
                        <p className="whitespace-pre-wrap text-sm">{cleanContent}</p>
                      ) : (
                        /* Assistant BI Card layout */
                        <div className="space-y-4">
                          {/* 1. Natural Language Summary */}
                          {cleanContent && (
                            <div className="flex gap-2 items-start">
                              <Sparkles size={16} className="text-primary-600 shrink-0 mt-0.5" />
                              <p className="text-sm font-normal text-gray-800 leading-relaxed whitespace-pre-wrap">
                                {cleanContent}
                              </p>
                            </div>
                          )}

                          {/* 2. Key Findings */}
                          {msg.metadata?.key_findings?.length > 0 && (
                            <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                              <p className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">Key Findings</p>
                              <ul className="space-y-1">
                                {msg.metadata.key_findings.map((f: string, fIdx: number) => (
                                  <li key={fIdx} className="text-xs text-gray-600 flex items-start gap-1.5">
                                    <span className="text-primary-500 font-bold">•</span>
                                    <span>{f}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* 3. Interactive Chart Visualization */}
                          {renderInteractiveChart(msg)}

                          {/* 4. Query Results Data Table */}
                          {hasQueryResults && (
                            <div className="mt-4 border border-gray-200 rounded-xl overflow-hidden">
                              <div className="bg-gray-50 px-3.5 py-2.5 border-b border-gray-200 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <TableIcon size={14} className="text-gray-500" />
                                  <span className="text-xs font-semibold text-gray-700">Query Results</span>
                                </div>
                                <span className="text-xs font-medium text-gray-500 bg-gray-200/70 px-2 py-0.5 rounded-full">
                                  {msg.query_result.data.row_count} rows
                                </span>
                              </div>
                              <div className="overflow-x-auto max-h-64">
                                <table className="text-xs w-full text-left">
                                  <thead>
                                    <tr className="bg-gray-100/70 border-b border-gray-200 text-gray-600">
                                      {orderedColumns.map((col: string) => (
                                        <th key={col} className="px-3.5 py-2 font-semibold whitespace-nowrap">{col}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-100">
                                    {msg.query_result.data.rows.slice(0, 50).map((row: any, i: number) => (
                                      <tr key={i} className="hover:bg-gray-50/80 transition-colors">
                                        {orderedColumns.map((col: string) => (
                                          <td key={col} className="px-3.5 py-2 text-gray-700 whitespace-nowrap">
                                            {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* 5. Collapsible "Show SQL" Section */}
                          {msg.sql_query && (
                            <div className="pt-1">
                              <button
                                onClick={() => toggleSql(idx)}
                                className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 px-2.5 py-1.5 rounded-lg transition-colors"
                              >
                                <Code size={13} />
                                <span>{expandedSql[idx] ? 'Hide SQL' : 'Show SQL'}</span>
                                <ChevronDown size={13} className={`transition-transform duration-200 ${expandedSql[idx] ? 'rotate-180' : ''}`} />
                              </button>
                              {expandedSql[idx] && (
                                <div className="mt-2.5 p-3.5 bg-slate-900 rounded-xl shadow-inner border border-slate-800">
                                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Executed SQL Query</p>
                                  <pre className="text-xs text-emerald-400 font-mono overflow-x-auto whitespace-pre leading-relaxed">{msg.sql_query}</pre>
                                </div>
                              )}
                            </div>
                          )}

                          {/* 6. Follow-up Suggestions */}
                          {msg.metadata?.follow_up_questions?.length > 0 && (
                            <div className="pt-2 border-t border-gray-100">
                              <p className="text-xs font-medium text-gray-400 mb-2">Suggested Follow-ups:</p>
                              <div className="flex flex-wrap gap-2">
                                {msg.metadata.follow_up_questions.map((q: string, qIdx: number) => (
                                  <button
                                    key={qIdx}
                                    onClick={() => sendMessage(q)}
                                    className="text-xs bg-primary-50/80 hover:bg-primary-100 text-primary-700 border border-primary-200/50 px-3 py-1.5 rounded-full transition-colors font-medium text-left"
                                  >
                                    {q}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              {isSending && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 shadow-sm rounded-2xl px-5 py-4">
                    <div className="flex items-center gap-2">
                      <Sparkles size={16} className="text-primary-600 animate-spin" />
                      <span className="text-xs font-medium text-gray-500">Analyzing data and generating insights...</span>
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
              placeholder="Ask a question about your data..."
              className="input-field flex-1 text-sm"
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
