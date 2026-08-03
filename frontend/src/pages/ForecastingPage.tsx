import { useEffect, useState } from 'react';
import { forecastingAPI, datasetsAPI } from '../services/api';
import { TrendingUp, AlertTriangle, Play, BarChart3 } from 'lucide-react';
import toast from 'react-hot-toast';

interface ForecastModel {
  id: number;
  name: string;
  method: string;
  target_column: string;
  status: string;
  horizon: number;
  metrics: Record<string, any>;
  created_at: string;
}

interface AnomalyResult {
  id: number;
  name: string;
  anomalies_count: number;
  target_column: string;
  created_at: string;
}

export default function ForecastingPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [models, setModels] = useState<ForecastModel[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyResult[]>([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '',
    method: 'arima',
    target_column: '',
    date_column: '',
    horizon: 30,
    parameters: {},
  });
  const [anomalyForm, setAnomalyForm] = useState({
    target_column: '',
    method: 'isolation_forest',
    sensitivity: 0.5,
  });
  const [anomalyDataset, setAnomalyDataset] = useState('');

  useEffect(() => {
    loadDatasets();
    loadModels();
    loadAnomalies();
  }, []);

  const loadDatasets = async () => {
    try {
      const { data } = await datasetsAPI.list({ status: 'ready' });
      setDatasets(data.results || data);
    } catch {}
  };

  const loadModels = async () => {
    try {
      const { data } = await forecastingAPI.list();
      setModels(data.results || data);
    } catch {}
  };

  const loadAnomalies = async () => {
    try {
      const { data } = await forecastingAPI.getAnomalies();
      setAnomalies(data.results || data);
    } catch {}
  };

  const handleCreateForecast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDataset) return;
    setIsCreating(true);
    try {
      await forecastingAPI.create(selectedDataset, form);
      toast.success('Forecast model created!');
      setShowForm(false);
      loadModels();
    } catch {
      toast.error('Failed to create forecast');
    } finally {
      setIsCreating(false);
    }
  };

  const handleCreateAnomaly = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!anomalyDataset) return;
    try {
      await forecastingAPI.createAnomalyDetection(anomalyDataset, anomalyForm);
      toast.success('Anomaly detection started!');
      loadAnomalies();
    } catch {
      toast.error('Failed to start anomaly detection');
    }
  };

  const getSelectedColumns = () => {
    const ds = datasets.find((d) => d.id === selectedDataset);
    return ds?.column_names || [];
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Forecasting</h1>
          <p className="text-gray-500 mt-1">Predict trends and detect anomalies with ML models</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          <Play size={16} />
          New Forecast
        </button>
      </div>

      {/* Create Forecast Form */}
      {showForm && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create Forecast Model</h2>
          <form onSubmit={handleCreateForecast} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Dataset</label>
                <select
                  value={selectedDataset}
                  onChange={(e) => setSelectedDataset(e.target.value)}
                  className="input-field"
                >
                  <option value="">Select dataset...</option>
                  {datasets.map((ds) => (
                    <option key={ds.id} value={ds.id}>{ds.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Model Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="input-field"
                  placeholder="e.g., Sales Forecast Q1"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Method</label>
                <select
                  value={form.method}
                  onChange={(e) => setForm({ ...form, method: e.target.value })}
                  className="input-field"
                >
                  <option value="arima">ARIMA</option>
                  <option value="sarimax">SARIMAX</option>
                  <option value="holt_winters">Holt-Winters</option>
                  <option value="prophet">Prophet</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Target Column</label>
                <select
                  value={form.target_column}
                  onChange={(e) => setForm({ ...form, target_column: e.target.value })}
                  className="input-field"
                  required
                >
                  <option value="">Select column...</option>
                  {getSelectedColumns().map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Date Column (optional)</label>
                <select
                  value={form.date_column}
                  onChange={(e) => setForm({ ...form, date_column: e.target.value })}
                  className="input-field"
                >
                  <option value="">None</option>
                  {getSelectedColumns().map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Forecast Horizon (periods)</label>
                <input
                  type="number"
                  value={form.horizon}
                  onChange={(e) => setForm({ ...form, horizon: Number(e.target.value) })}
                  className="input-field"
                  min={1}
                  max={365}
                />
              </div>
            </div>
            <button type="submit" disabled={isCreating} className="btn-primary disabled:opacity-50">
              {isCreating ? 'Creating...' : 'Create Model'}
            </button>
          </form>
        </div>
      )}

      {/* Anomaly Detection */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Anomaly Detection</h2>
        <form onSubmit={handleCreateAnomaly} className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="text-sm font-medium text-gray-700">Dataset</label>
            <select
              value={anomalyDataset}
              onChange={(e) => setAnomalyDataset(e.target.value)}
              className="input-field"
            >
              <option value="">Select dataset...</option>
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id}>{ds.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Target Column</label>
            <select
              value={anomalyForm.target_column}
              onChange={(e) => setAnomalyForm({ ...anomalyForm, target_column: e.target.value })}
              className="input-field"
              required
            >
              <option value="">Select...</option>
              {getSelectedColumns().map((col) => (
                <option key={col} value={col}>{col}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Method</label>
            <select
              value={anomalyForm.method}
              onChange={(e) => setAnomalyForm({ ...anomalyForm, method: e.target.value })}
              className="input-field"
            >
              <option value="isolation_forest">Isolation Forest</option>
              <option value="zscore">Z-Score</option>
              <option value="iqr">IQR</option>
            </select>
          </div>
          <button type="submit" className="btn-primary flex items-center gap-2">
            <AlertTriangle size={16} />
            Detect
          </button>
        </form>
      </div>

      {/* Models List */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Forecast Models</h2>
        {models.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No forecast models yet. Create one above.</p>
        ) : (
          <div className="space-y-3">
            {models.map((model) => (
              <div key={model.id} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <TrendingUp className="w-5 h-5 text-primary-600" />
                    <div>
                      <p className="font-medium text-gray-900">{model.name}</p>
                      <p className="text-sm text-gray-500">
                        {model.method} • Target: {model.target_column} • Horizon: {model.horizon}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    model.status === 'completed' ? 'bg-green-100 text-green-700' :
                    model.status === 'running' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {model.status}
                  </span>
                </div>
                {model.metrics && Object.keys(model.metrics).length > 0 && (
                  <div className="mt-3 grid grid-cols-3 gap-4">
                    {Object.entries(model.metrics).slice(0, 6).map(([key, value]) => (
                      <div key={key}>
                        <p className="text-xs text-gray-500">{key}</p>
                        <p className="text-sm font-medium">{typeof value === 'number' ? value.toFixed(4) : value}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Anomalies List */}
      {anomalies.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Anomaly Detection Results</h2>
          <div className="space-y-3">
            {anomalies.map((a) => (
              <div key={a.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  <div>
                    <p className="font-medium text-gray-900">{a.name}</p>
                    <p className="text-sm text-gray-500">
                      {a.target_column} • {a.anomalies_count} anomalies detected
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
