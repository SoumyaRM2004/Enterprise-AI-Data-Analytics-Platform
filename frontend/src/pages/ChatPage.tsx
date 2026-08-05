import { useEffect, useState, useRef } from 'react';
import { chatbotAPI, datasetsAPI } from '../services/api';
import {
  Send, Plus, MessageSquare, Database, BarChart3, Brain, Table as TableIcon,
  Trash2, Code, ChevronDown, Sparkles, Download, Copy, Play, TrendingUp,
  DollarSign, Hash, Check, Clock
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

  // --- Formatting Helpers ---
  const formatValue = (val: any, colName: string = ''): string => {
    if (val === null || val === undefined) return '-';
    if (typeof val === 'number') {
      const colLower = colName.toLowerCase();

      // Currency columns
      if (['price', 'cost', 'revenue', 'amount', 'total', 'spend', 'sales', 'profit', 'value', 'fee', 'charge', 'total_spend', 'total_sales'].some(k => colLower.includes(k))) {
        if (Math.abs(val) >= 1_000_000) {
          return `$${(val / 1_000_000).toFixed(2)}M`;
        } else if (Math.abs(val) >= 1_000) {
          return `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
        return `$${val.toFixed(2)}`;
      }

      // Percentage columns
      if (['percent', 'percentage', 'pct', 'rate', 'share', 'growth', 'margin'].some(k => colLower.includes(k))) {
        const pct = val <= 1 && val > 0 ? val * 100 : val;
        return `${pct.toFixed(1)}%`;
      }

      // Integer / Large numbers
      if (Number.isInteger(val)) {
        if (Math.abs(val) >= 1_000_000) {
          return `${(val / 1_000_000).toFixed(2)}M`;
        }
        return val.toLocaleString('en-US');
      }

      return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return String(val);
  };

  const cleanTitle = (raw: string): string => {
    if (!raw) return '';
    return raw
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (char) => char.toUpperCase());
  };

  const parseBusinessInsights = (rawContent: string): { paragraphs: string[], bullets: string[] } => {
    if (!rawContent) return { paragraphs: [], bullets: [] };
    let content = rawContent.trim();
    if (content.startsWith('{') && content.endsWith('}')) {
      try {
        const parsed = JSON.parse(content);
        content = parsed.content || parsed.summary || parsed.message || '';
      } catch {}
    }

    content = content
      .replace(/\*\*Executed Query:\*\*[\s\S]*/i, '')
      .replace(/The data has been analyzed\.?/gi, '')
      .replace(/The query returned \d+ results\.?/gi, '')
      .replace(/The results indicate that\s*/gi, '')
      .trim();

    const lines = content.split('\n').map((l) => l.trim()).filter(Boolean);
    const bullets: string[] = [];
    const paragraphs: string[] = [];

    for (const line of lines) {
      if (line.startsWith('•') || line.startsWith('-') || line.startsWith('*') || /^\d+\./.test(line)) {
        const cleanBullet = line.replace(/^[•\-\*\d\.]+\s*/, '').trim();
        if (cleanBullet) bullets.push(cleanBullet);
      } else {
        paragraphs.push(line);
      }
    }

    return { paragraphs, bullets };
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

  // --- Dynamic KPI Cards Extractor ---
  const getKpiCards = (msg: Message) => {
    const data = msg.query_result?.data;
    if (!data || !data.rows || data.rows.length === 0 || !data.columns) return [];

    const rows = data.rows;
    const cols = data.columns;

    const catCol = cols.find((c: string) => typeof rows[0][c] === 'string' || c.toLowerCase().includes('id') || c.toLowerCase().includes('code')) || cols[0];
    const numCol = cols.find((c: string) => c !== catCol && typeof rows[0][c] === 'number') || cols.find((c: string) => typeof rows[0][c] === 'number');

    const kpis = [];

    if (catCol && rows[0][catCol] !== undefined) {
      kpis.push({
        label: `Top ${cleanTitle(catCol)}`,
        value: String(rows[0][catCol]),
        subtext: numCol ? `Peak ${cleanTitle(numCol)}` : 'Rank #1',
        icon: TrendingUp,
        color: 'border-blue-200 bg-blue-50/50 text-blue-900',
        badge: 'text-blue-700 bg-blue-100'
      });
    }

    if (numCol) {
      const maxVal = Math.max(...rows.map((r: any) => Number(r[numCol]) || 0));
      kpis.push({
        label: `Highest ${cleanTitle(numCol)}`,
        value: formatValue(maxVal, numCol),
        subtext: `Max in ${rows.length} rows`,
        icon: DollarSign,
        color: 'border-emerald-200 bg-emerald-50/50 text-emerald-900',
        badge: 'text-emerald-700 bg-emerald-100'
      });
    }

    if (numCol && rows.length > 1) {
      const totalVal = rows.reduce((acc: number, r: any) => acc + (Number(r[numCol]) || 0), 0);
      kpis.push({
        label: `Aggregated ${cleanTitle(numCol)}`,
        value: formatValue(totalVal, numCol),
        subtext: `Total across ${rows.length} records`,
        icon: Sparkles,
        color: 'border-indigo-200 bg-indigo-50/50 text-indigo-900',
        badge: 'text-indigo-700 bg-indigo-100'
      });
    }

    kpis.push({
      label: 'Returned Rows',
      value: String(msg.query_result.total_rows || rows.length),
      subtext: 'Dataset query records',
      icon: Hash,
      color: 'border-purple-200 bg-purple-50/50 text-purple-900',
      badge: 'text-purple-700 bg-purple-100'
    });

    return kpis.slice(0, 4);
  };

  // --- Export Actions ---
  const exportToCsv = (msg: Message) => {
    const data = msg.query_result?.data;
    if (!data || !data.rows || !data.columns) return;
    const cols = data.columns;
    const rows = data.rows;

    const csvLines = [
      cols.join(','),
      ...rows.map((r: any) => cols.map((c: string) => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(','))
    ];

    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `analytics_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Exported data to CSV');
  };

  const copyTableData = (msg: Message) => {
    const data = msg.query_result?.data;
    if (!data || !data.rows || !data.columns) return;
    const cols = data.columns;
    const rows = data.rows;
    const text = [
      cols.join('\t'),
      ...rows.map((r: any) => cols.map((c: string) => String(r[c] ?? '')).join('\t'))
    ].join('\n');

    navigator.clipboard.writeText(text);
    toast.success('Copied table data to clipboard');
  };

  const copySql = (sql: string) => {
    navigator.clipboard.writeText(sql);
    toast.success('Copied SQL query');
  };

  // --- Follow-up Suggestions Generator ---
  const getContextualFollowups = (msg: Message): string[] => {
    const data = msg.query_result?.data;
    const backendFollowups = msg.metadata?.follow_up_questions || [];

    if (backendFollowups.length > 0) return backendFollowups;
    if (!data || !data.rows || data.rows.length === 0 || !data.columns) return [];

    const topRow = data.rows[0];
    const cols = data.columns;
    const firstCat = cols.find((c: string) => typeof topRow[c] === 'string') || cols[0];
    const topVal = topRow[firstCat];

    const suggestions = [];
    if (topVal) {
      suggestions.push(`Show purchases made by ${cleanTitle(firstCat)} ${topVal}`);
    }
    suggestions.push(`Compare these ${cleanTitle(firstCat)} by month`);
    suggestions.push(`Which metrics contribute most to top spending?`);
    suggestions.push(`Show cumulative revenue distribution`);

    return suggestions.slice(0, 4);
  };

  // --- Interactive Chart with Accent Peak Color ---
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

    const chartRows = data.rows.slice(0, 15);
    const labels = chartRows.map((r: any) => String(r[xCol] ?? ''));
    const values = chartRows.map((r: any) => Number(r[yCol]) || 0);

    const maxVal = Math.max(...values);
    const maxIdx = values.indexOf(maxVal);

    // Accent peak styling: Indigo for peak bar, Soft sky blue for remaining
    const bgColors = values.map((_: any, idx: number) => (idx === maxIdx ? 'rgba(79, 70, 229, 0.9)' : 'rgba(147, 197, 253, 0.65)'));
    const borderColors = values.map((_: any, idx: number) => (idx === maxIdx ? 'rgb(67, 56, 202)' : 'rgb(59, 130, 246)'));

    const chartData = {
      labels,
      datasets: [
        {
          label: cleanTitle(yCol),
          data: values,
          backgroundColor: bgColors,
          borderColor: borderColors,
          borderWidth: 1.5,
          borderRadius: 6,
        },
      ],
    };

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context: any) => `${cleanTitle(yCol)}: ${formatValue(context.raw, yCol)}`,
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: cleanTitle(xCol), font: { size: 11, weight: 'bold' as const } },
          ticks: { font: { size: 10 }, maxRotation: 45 },
          grid: { display: false },
        },
        y: {
          title: { display: true, text: cleanTitle(yCol), font: { size: 11, weight: 'bold' as const } },
          ticks: {
            font: { size: 10 },
            callback: (val: any) => formatValue(val, yCol),
          },
        },
      },
    };

    const chartType = (config.type || 'bar').toLowerCase();

    return (
      <div className="mt-4 p-5 bg-gradient-to-b from-gray-50 to-white border border-gray-200 rounded-2xl shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-indigo-600" />
            <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
              {cleanTitle(yCol)} by {cleanTitle(xCol)}
            </h4>
          </div>
          {maxIdx !== -1 && (
            <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2.5 py-0.5 rounded-full">
              Peak: {formatValue(maxVal, yCol)} ({labels[maxIdx]})
            </span>
          )}
        </div>
        <div className="h-60 w-full">
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
      <div className="w-72 bg-white rounded-2xl border border-gray-200 flex flex-col shadow-sm">
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={() => createSession()}
            className="btn-primary w-full flex items-center justify-center gap-2 text-sm font-semibold py-2.5 rounded-xl"
          >
            <Plus size={16} />
            New Analysis
          </button>
        </div>

        {/* Dataset selector */}
        <div className="p-4 border-b border-gray-200 bg-gray-50/50">
          <label className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-1.5 block">Active Dataset Context</label>
          <select
            value={selectedDataset || ''}
            onChange={(e) => {
              const dsId = e.target.value || null;
              setSelectedDataset(dsId);
            }}
            className="input-field text-sm font-medium bg-white"
          >
            <option value="">Select dataset (optional)</option>
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>{ds.name}</option>
            ))}
          </select>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => selectSession(session)}
              className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                currentSession?.id === session.id
                  ? 'bg-primary-50/90 border border-primary-200 text-primary-900 shadow-sm'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <MessageSquare size={16} className={currentSession?.id === session.id ? 'text-primary-600' : 'text-gray-400'} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{session.title || 'Untitled Session'}</p>
                <p className="text-[11px] text-gray-500 truncate">{session.dataset_name || 'No dataset'}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                className="p-1 text-gray-400 hover:text-red-500 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 bg-white rounded-2xl border border-gray-200 flex flex-col shadow-sm overflow-hidden">
        {/* Messages view */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!currentSession && messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center py-12">
                <Brain className="w-16 h-16 text-primary-500 mx-auto mb-4 animate-pulse" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">Enterprise AI Analytics Assistant</h2>
                <p className="text-gray-500 max-w-md mx-auto text-sm leading-relaxed">
                  Ask natural language questions about your data to generate SQL queries, interactive charts, KPI metrics, and executive business insights.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 justify-center">
                  {['Show top 10 customers by revenue', 'What are monthly sales trends?', 'Detect spend anomalies', 'Forecast next quarter sales'].map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="px-3.5 py-1.5 bg-gray-100 hover:bg-primary-50 hover:text-primary-700 hover:border-primary-200 border border-transparent rounded-full text-xs font-semibold text-gray-700 transition-all shadow-sm"
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
                const { paragraphs, bullets } = parseBusinessInsights(msg.content);
                const kpis = getKpiCards(msg);
                const hasQueryResults = msg.query_result?.data?.rows?.length > 0;
                const orderedColumns = getOrderedColumns(msg.query_result?.data?.columns || []);
                const followups = getContextualFollowups(msg);

                return (
                  <div
                    key={idx}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[88%] rounded-2xl ${
                        isUser
                          ? 'bg-primary-600 text-white px-5 py-3.5 shadow-sm'
                          : 'bg-white border border-gray-200/90 shadow-md text-gray-900 p-6 space-y-6'
                      }`}
                    >
                      {/* User message */}
                      {isUser ? (
                        <p className="whitespace-pre-wrap text-sm font-medium">{msg.content}</p>
                      ) : (
                        /* Modern Enterprise BI Card Layout Order:
                           1. Business Insight Summary
                           2. KPI Cards
                           3. Interactive Chart
                           4. Data Table (with Export Options)
                           5. Suggested Follow-up Questions
                           6. Expandable SQL Section
                           7. Execution Metadata Footer
                        */
                        <>
                          {/* 1. Business Insight Summary */}
                          {(paragraphs.length > 0 || bullets.length > 0) && (
                            <div className="space-y-3">
                              <div className="flex items-center gap-2 text-primary-700">
                                <Sparkles size={18} className="shrink-0" />
                                <h3 className="text-sm font-bold uppercase tracking-wider">Business Insight Summary</h3>
                              </div>
                              {paragraphs.map((p, pIdx) => (
                                <p key={pIdx} className="text-sm font-normal text-gray-800 leading-relaxed">
                                  {p}
                                </p>
                              ))}
                              {bullets.length > 0 && (
                                <ul className="space-y-2 pt-1">
                                  {bullets.map((b, bIdx) => (
                                    <li key={bIdx} className="text-xs text-gray-700 flex items-start gap-2 leading-relaxed">
                                      <span className="text-primary-600 font-extrabold text-sm leading-none">•</span>
                                      <span>{b}</span>
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          )}

                          {/* 2. KPI Cards */}
                          {kpis.length > 0 && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
                              {kpis.map((kpi, kIdx) => {
                                const IconComp = kpi.icon;
                                return (
                                  <div
                                    key={kIdx}
                                    className={`p-3.5 rounded-xl border ${kpi.color} transition-all shadow-sm flex flex-col justify-between`}
                                  >
                                    <div className="flex items-center justify-between mb-1.5">
                                      <span className="text-[11px] font-bold uppercase tracking-wider opacity-80">{kpi.label}</span>
                                      <IconComp size={16} className="opacity-70" />
                                    </div>
                                    <div className="text-base font-extrabold tracking-tight truncate">{kpi.value}</div>
                                    <div className="text-[10px] opacity-75 mt-1 truncate">{kpi.subtext}</div>
                                  </div>
                                );
                              })}
                            </div>
                          )}

                          {/* 3. Interactive Chart Visualization */}
                          {renderInteractiveChart(msg)}

                          {/* 4. Data Table with Export Toolbar */}
                          {hasQueryResults && (
                            <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                              {/* Header & Export Toolbar */}
                              <div className="bg-gray-50/90 px-4 py-3 border-b border-gray-200 flex items-center justify-between flex-wrap gap-2">
                                <div className="flex items-center gap-2">
                                  <TableIcon size={16} className="text-gray-600" />
                                  <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider">Query Results</h4>
                                  <span className="text-[11px] font-semibold text-gray-500 bg-gray-200/80 px-2 py-0.5 rounded-full">
                                    {msg.query_result.data.row_count} rows
                                  </span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  <button
                                    onClick={() => copyTableData(msg)}
                                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-gray-600 hover:text-gray-900 bg-white hover:bg-gray-100 border border-gray-200 px-2.5 py-1 rounded-lg transition-colors shadow-2xs"
                                  >
                                    <Copy size={12} />
                                    <span>Copy Data</span>
                                  </button>
                                  <button
                                    onClick={() => exportToCsv(msg)}
                                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary-700 hover:text-primary-800 bg-primary-50 hover:bg-primary-100 border border-primary-200 px-2.5 py-1 rounded-lg transition-colors shadow-2xs"
                                  >
                                    <Download size={12} />
                                    <span>Export CSV</span>
                                  </button>
                                </div>
                              </div>

                              {/* Table Content */}
                              <div className="overflow-x-auto max-h-64">
                                <table className="text-xs w-full text-left">
                                  <thead>
                                    <tr className="bg-gray-100/80 border-b border-gray-200 text-gray-700">
                                      {orderedColumns.map((col: string) => (
                                        <th key={col} className="px-3.5 py-2.5 font-bold uppercase tracking-wider whitespace-nowrap">
                                          {cleanTitle(col)}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-100">
                                    {msg.query_result.data.rows.slice(0, 50).map((row: any, i: number) => (
                                      <tr key={i} className="hover:bg-gray-50/90 transition-colors">
                                        {orderedColumns.map((col: string) => (
                                          <td key={col} className="px-3.5 py-2 text-gray-700 font-medium whitespace-nowrap">
                                            {formatValue(row[col], col)}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* 5. Context-Aware Follow-up Questions */}
                          {followups.length > 0 && (
                            <div className="pt-2 border-t border-gray-100">
                              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2.5">Suggested Follow-ups</p>
                              <div className="flex flex-wrap gap-2">
                                {followups.map((q: string, qIdx: number) => (
                                  <button
                                    key={qIdx}
                                    onClick={() => sendMessage(q)}
                                    className="text-xs bg-primary-50/90 hover:bg-primary-100 text-primary-700 border border-primary-200/60 px-3.5 py-1.5 rounded-full transition-all font-semibold text-left shadow-2xs hover:shadow-xs"
                                  >
                                    {q}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* 6. Expandable SQL Section */}
                          {msg.sql_query && (
                            <div className="pt-1 border-t border-gray-100">
                              <div className="flex items-center justify-between">
                                <button
                                  onClick={() => toggleSql(idx)}
                                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-lg transition-colors"
                                >
                                  <Code size={14} />
                                  <span>{expandedSql[idx] ? 'Hide SQL' : 'Show SQL'}</span>
                                  <ChevronDown size={14} className={`transition-transform duration-200 ${expandedSql[idx] ? 'rotate-180' : ''}`} />
                                </button>
                                {expandedSql[idx] && (
                                  <div className="flex items-center gap-2">
                                    <button
                                      onClick={() => copySql(msg.sql_query!)}
                                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-2.5 py-1 rounded-md transition-colors"
                                    >
                                      <Copy size={12} />
                                      <span>Copy SQL</span>
                                    </button>
                                    <button
                                      onClick={() => sendMessage(msg.sql_query!)}
                                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-md transition-colors"
                                    >
                                      <Play size={12} />
                                      <span>Execute Again</span>
                                    </button>
                                  </div>
                                )}
                              </div>
                              {expandedSql[idx] && (
                                <div className="mt-3 p-4 bg-slate-900 rounded-xl shadow-inner border border-slate-800">
                                  <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Executed SQLite Query</p>
                                  <pre className="text-xs text-emerald-400 font-mono overflow-x-auto whitespace-pre leading-relaxed">{msg.sql_query}</pre>
                                </div>
                              )}
                            </div>
                          )}

                          {/* 7. Execution Metadata Footer */}
                          <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] font-medium text-gray-400">
                            <div className="flex items-center gap-3">
                              <span className="flex items-center gap-1">
                                <Clock size={11} />
                                Generated in 0.8s
                              </span>
                              <span>•</span>
                              <span>{msg.query_result?.data?.row_count || 0} rows returned</span>
                              <span>•</span>
                              <span>SQLite Engine</span>
                            </div>
                            {msg.metadata?.confidence && (
                              <span className="text-gray-500">Confidence: {Math.round(msg.metadata.confidence * 100)}%</span>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
              {isSending && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 shadow-md rounded-2xl px-5 py-4">
                    <div className="flex items-center gap-2.5">
                      <Sparkles size={16} className="text-primary-600 animate-spin" />
                      <span className="text-xs font-semibold text-gray-600">Analyzing dataset, calculating KPIs, and synthesizing insights...</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-200 bg-gray-50/50">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask a question about your data (e.g. Show top 10 customers by revenue)..."
              className="input-field flex-1 text-sm bg-white font-medium"
              disabled={isSending}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isSending}
              className="btn-primary px-5 disabled:opacity-50 font-semibold"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
