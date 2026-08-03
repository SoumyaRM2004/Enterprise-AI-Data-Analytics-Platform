import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { datasetsAPI, analyticsAPI } from '../services/api';
import {
  BarChart, LineChart, PieChart, ScatterChart,
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  PointElement, LineElement, ArcElement, Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';
import {
  ArrowLeft, Database, Table, BarChart3, Download,
  Trash2, Play, AlertCircle, CheckCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, ArcElement, Title, Tooltip, Legend, Filler);

interface DatasetProfile {
  column_names: string[];
  column_types: Record<string, string>;
  data_profile: Record<string, any>;
  row_count: number;
  column_count: number;
  data_quality_score: number;
  sample_data: Record<string, any>[];
}

interface ChartConfig {
  type: string;
  title: string;
  data: any;
  options?: any;
}

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<any>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [charts, setCharts] = useState<ChartConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'profile' | 'charts' | 'data'>('overview');

  useEffect(() => {
    if (id) loadDataset();
  }, [id]);

  const loadDataset = async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const [dsRes, dashboardRes] = await Promise.all([
        datasetsAPI.get(id),
        analyticsAPI.getDashboard(id),
      ]);
      setDataset(dsRes.data);
      if (dashboardRes.data) {
        setProfile(dashboardRes.data.profile || null);
        setCharts(dashboardRes.data.charts || []);
      }
    } catch {
      toast.error('Failed to load dataset');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    try {
      await analyticsAPI.generateReport(id!);
      toast.success('Report generation started!');
    } catch {
      toast.error('Failed to generate report');
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" /></div>;
  }

  if (!dataset) return <div className="text-center py-12 text-gray-500">Dataset not found.</div>;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Database },
    { id: 'profile', label: 'Data Profile', icon: Table },
    { id: 'charts', label: 'Charts', icon: BarChart3 },
    { id: 'data', label: 'Data Preview', icon: Table },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/datasets')} className="p-2 hover:bg-gray-100 rounded-lg">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{dataset.name}</h1>
            <p className="text-sm text-gray-500">{dataset.row_count?.toLocaleString()} rows • {dataset.column_count} columns</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={handleGenerateReport} className="btn-primary flex items-center gap-2">
            <Download size={16} />
            Generate Report
          </button>
        </div>
      </div>

      {/* Status */}
      <div className={`flex items-center gap-2 p-3 rounded-lg ${
        dataset.status === 'ready' ? 'bg-green-50 text-green-700' :
        dataset.status === 'processing' ? 'bg-yellow-50 text-yellow-700' :
        'bg-red-50 text-red-700'
      }`}>
        {dataset.status === 'ready' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
        <span className="text-sm font-medium">Status: {dataset.status}</span>
        {dataset.error_message && <span className="text-sm ml-2">{dataset.error_message}</span>}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary-600 text-primary-600 font-medium'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card">
              <p className="text-sm text-gray-500">Rows</p>
              <p className="text-xl font-bold">{(profile?.row_count ?? dataset.row_count)?.toLocaleString() || '-'}</p>
            </div>
            <div className="card">
              <p className="text-sm text-gray-500">Columns</p>
              <p className="text-xl font-bold">{profile?.column_count ?? dataset.column_count ?? '-'}</p>
            </div>
            <div className="card">
              <p className="text-sm text-gray-500">Quality Score</p>
              <p className="text-xl font-bold text-green-600">{profile?.data_quality_score ?? dataset.data_quality_score ?? 100}%</p>
            </div>
            <div className="card">
              <p className="text-sm text-gray-500">Data Type</p>
              <p className="text-xl font-bold uppercase">{dataset.file_type || 'CSV'}</p>
            </div>
          </div>

          {/* Quick Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {charts.slice(0, 4).map((chart, idx) => (
              <div key={idx} className="card">
                <h3 className="font-medium text-gray-900 mb-4">{chart.title}</h3>
                <div className="h-64">
                  {chart.type === 'bar' && <Bar data={chart.data} options={chart.options} />}
                  {chart.type === 'line' && <Line data={chart.data} options={chart.options} />}
                  {chart.type === 'pie' && <Pie data={chart.data} options={chart.options} />}
                  {chart.type === 'scatter' && <Scatter data={chart.data} options={chart.options} />}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'profile' && (
        <div className="space-y-4">
          {Object.entries(profile?.data_profile || (profile && !profile.data_profile ? profile : {})).map(([colName, colInfo]: [string, any]) => (
            <div key={colName} className="card">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                {colName}
                {colInfo?.dtype && <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{colInfo.dtype}</span>}
              </h3>
              {colInfo && typeof colInfo === 'object' && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
                  <div><p className="text-xs text-gray-500">Null Count</p><p className="font-medium">{colInfo.null_count ?? '-'}</p></div>
                  <div><p className="text-xs text-gray-500">Null %</p><p className="font-medium">{colInfo.null_percent ?? 0}%</p></div>
                  <div><p className="text-xs text-gray-500">Unique</p><p className="font-medium">{colInfo.unique_count ?? '-'}</p></div>
                  {colInfo.mean !== undefined && colInfo.mean !== null && <div><p className="text-xs text-gray-500">Mean</p><p className="font-medium">{colInfo.mean}</p></div>}
                  {colInfo.std !== undefined && colInfo.std !== null && <div><p className="text-xs text-gray-500">Std Dev</p><p className="font-medium">{colInfo.std}</p></div>}
                  {colInfo.min !== undefined && colInfo.min !== null && <div><p className="text-xs text-gray-500">Min</p><p className="font-medium">{colInfo.min}</p></div>}
                  {colInfo.max !== undefined && colInfo.max !== null && <div><p className="text-xs text-gray-500">Max</p><p className="font-medium">{colInfo.max}</p></div>}
                  {colInfo.skewness !== undefined && colInfo.skewness !== null && <div><p className="text-xs text-gray-500">Skewness</p><p className="font-medium">{colInfo.skewness}</p></div>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'charts' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {charts.map((chart, idx) => (
            <div key={idx} className="card">
              <h3 className="font-medium text-gray-900 mb-4">{chart.title}</h3>
              <div className="h-80">
                {chart.type === 'bar' && <Bar data={chart.data} options={{ ...chart.options, maintainAspectRatio: false }} />}
                {chart.type === 'line' && <Line data={chart.data} options={{ ...chart.options, maintainAspectRatio: false }} />}
                {chart.type === 'pie' && <Pie data={chart.data} options={{ ...chart.options, maintainAspectRatio: false }} />}
                {chart.type === 'scatter' && <Scatter data={chart.data} options={{ ...chart.options, maintainAspectRatio: false }} />}
                {chart.type === 'histogram' && <Bar data={chart.data} options={{ ...chart.options, maintainAspectRatio: false }} />}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'data' && (
        <div className="card overflow-x-auto">
          {(() => {
            const cols = profile?.column_names || dataset?.column_names || [];
            const rows = profile?.sample_data || dataset?.sample_data || [];
            if (cols.length === 0) return <p className="text-gray-500 py-4 text-center">No preview data available.</p>;
            return (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    {cols.map((col) => (
                      <th key={col} className="px-4 py-3 text-left font-medium text-gray-700">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 20).map((row, idx) => (
                    <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                      {cols.map((col) => (
                        <td key={col} className="px-4 py-3 text-gray-600">
                          {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })()}
        </div>
      )}
    </div>
  );
}
