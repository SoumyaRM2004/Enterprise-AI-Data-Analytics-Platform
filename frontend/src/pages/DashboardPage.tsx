import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { datasetsAPI, analyticsAPI } from '../services/api';
import {
  Database,
  FileText,
  TrendingUp,
  Users,
  ArrowUpRight,
  Brain,
} from 'lucide-react';

interface Dataset {
  id: string;
  name: string;
  status: string;
  row_count: number;
  column_count: number;
  created_at: string;
  data_quality_score: number;
}

export default function DashboardPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [stats, setStats] = useState({
    totalDatasets: 0,
    totalRows: 0,
    totalReports: 0,
    activeSessions: 0,
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [dsResponse] = await Promise.all([
        datasetsAPI.list({ status: 'ready' }),
      ]);
      const ds = dsResponse.data.results || dsResponse.data;
      setDatasets(ds);
      setStats({
        totalDatasets: ds.length,
        totalRows: ds.reduce((sum: number, d: Dataset) => sum + d.row_count, 0),
        totalReports: 0,
        activeSessions: 0,
      });
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    }
  };

  const statCards = [
    { label: 'Datasets', value: stats.totalDatasets, icon: Database, color: 'bg-blue-500', trend: '+2 this week' },
    { label: 'Total Records', value: stats.totalRows.toLocaleString(), icon: FileText, color: 'bg-green-500', trend: 'Across all datasets' },
    { label: 'Reports', value: stats.totalReports, icon: TrendingUp, color: 'bg-purple-500', trend: 'Generated' },
    { label: 'AI Sessions', value: stats.activeSessions, icon: Brain, color: 'bg-amber-500', trend: 'Active' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Overview of your analytics platform</p>
        </div>
        <button
          onClick={() => navigate('/datasets/upload')}
          className="btn-primary flex items-center gap-2"
        >
          <ArrowUpRight size={18} />
          Upload Dataset
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => (
          <div key={stat.label} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                <p className="text-xs text-green-600 mt-2">{stat.trend}</p>
              </div>
              <div className={`${stat.color} p-3 rounded-xl`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Datasets */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Datasets</h2>
          <button
            onClick={() => navigate('/datasets')}
            className="text-primary-600 text-sm hover:underline"
          >
            View all
          </button>
        </div>

        {datasets.length === 0 ? (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No datasets yet. Upload your first dataset to get started.</p>
            <button
              onClick={() => navigate('/datasets/upload')}
              className="btn-primary mt-4"
            >
              Upload Dataset
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {datasets.slice(0, 5).map((ds) => (
              <div
                key={ds.id}
                onClick={() => navigate(`/datasets/${ds.id}`)}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-primary-600" />
                  <div>
                    <p className="font-medium text-gray-900">{ds.name}</p>
                    <p className="text-sm text-gray-500">
                      {ds.row_count.toLocaleString()} rows • {ds.column_count} columns
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${
                    ds.status === 'ready' ? 'bg-green-100 text-green-700' :
                    ds.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {ds.status}
                  </span>
                  {ds.data_quality_score > 0 && (
                    <p className="text-xs text-gray-500 mt-1">Quality: {ds.data_quality_score}%</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/chat')}>
          <Brain className="w-8 h-8 text-primary-600 mb-3" />
          <h3 className="font-semibold text-gray-900">AI Chat</h3>
          <p className="text-sm text-gray-500 mt-1">Ask questions about your data in natural language</p>
        </div>
        <div className="card cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/forecasting')}>
          <TrendingUp className="w-8 h-8 text-green-600 mb-3" />
          <h3 className="font-semibold text-gray-900">Forecasting</h3>
          <p className="text-sm text-gray-500 mt-1">Predict future trends using ML models</p>
        </div>
        <div className="card cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/reports')}>
          <FileText className="w-8 h-8 text-purple-600 mb-3" />
          <h3 className="font-semibold text-gray-900">Reports</h3>
          <p className="text-sm text-gray-500 mt-1">Generate PDF reports and schedule deliveries</p>
        </div>
      </div>
    </div>
  );
}
