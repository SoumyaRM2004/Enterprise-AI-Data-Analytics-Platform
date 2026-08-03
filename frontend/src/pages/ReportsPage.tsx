import { useEffect, useState } from 'react';
import { reportsAPI, datasetsAPI } from '../services/api';
import { FileText, Download, Clock, Plus, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

interface Report {
  id: number;
  title: string;
  report_type: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  file: string | null;
  dataset_name: string | null;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [scheduledReports, setScheduledReports] = useState<any[]>([]);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    title: '',
    report_type: 'dataset_analysis',
    frequency: 'weekly',
    email_recipients: [''],
  });

  useEffect(() => {
    loadReports();
    loadDatasets();
    loadScheduled();
  }, []);

  const loadReports = async () => {
    try {
      const { data } = await reportsAPI.list();
      setReports(data.results || data);
    } catch {}
  };

  const loadDatasets = async () => {
    try {
      const { data } = await datasetsAPI.list({ status: 'ready' });
      setDatasets(data.results || data);
    } catch {}
  };

  const loadScheduled = async () => {
    try {
      const { data } = await reportsAPI.getScheduled();
      setScheduledReports(data.results || data);
    } catch {}
  };

  const handleGenerate = async () => {
    if (!selectedDataset) return;
    setIsGenerating(true);
    try {
      await reportsAPI.generate(selectedDataset, { report_type: 'dataset_analysis' });
      toast.success('Report generation started!');
      setTimeout(loadReports, 3000);
    } catch {
      toast.error('Failed to generate report');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async (report: Report) => {
    try {
      const response = await reportsAPI.download(report.id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${report.title}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      toast.error('Failed to download report');
    }
  };

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDataset) return;
    try {
      await reportsAPI.createScheduled({
        dataset: selectedDataset,
        ...scheduleForm,
        email_recipients: scheduleForm.email_recipients.filter((e) => e.trim()),
      });
      toast.success('Scheduled report created!');
      setShowScheduleForm(false);
      loadScheduled();
    } catch {
      toast.error('Failed to create schedule');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500 mt-1">Generate and manage PDF reports</p>
        </div>
        <button
          onClick={() => setShowScheduleForm(!showScheduleForm)}
          className="btn-secondary flex items-center gap-2"
        >
          <Clock size={16} />
          Schedule Report
        </button>
      </div>

      {/* Generate Report */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate Report</h2>
        <div className="flex gap-4">
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="input-field max-w-xs"
          >
            <option value="">Select dataset...</option>
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>{ds.name}</option>
            ))}
          </select>
          <button
            onClick={handleGenerate}
            disabled={!selectedDataset || isGenerating}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            <FileText size={16} />
            {isGenerating ? 'Generating...' : 'Generate PDF Report'}
          </button>
        </div>
      </div>

      {/* Schedule Form */}
      {showScheduleForm && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Schedule Report</h2>
          <form onSubmit={handleCreateSchedule} className="space-y-4">
            <input
              type="text"
              placeholder="Report title"
              value={scheduleForm.title}
              onChange={(e) => setScheduleForm({ ...scheduleForm, title: e.target.value })}
              className="input-field"
              required
            />
            <select
              value={scheduleForm.frequency}
              onChange={(e) => setScheduleForm({ ...scheduleForm, frequency: e.target.value })}
              className="input-field max-w-xs"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
            <div>
              <label className="text-sm text-gray-500">Email recipients (comma-separated)</label>
              <input
                type="text"
                placeholder="user@example.com, team@example.com"
                value={scheduleForm.email_recipients.join(', ')}
                onChange={(e) => setScheduleForm({
                  ...scheduleForm,
                  email_recipients: e.target.value.split(',').map(s => s.trim()),
                })}
                className="input-field"
              />
            </div>
            <button type="submit" className="btn-primary">Create Schedule</button>
          </form>
        </div>
      )}

      {/* Reports List */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Generated Reports</h2>
        {reports.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No reports generated yet.</p>
        ) : (
          <div className="space-y-3">
            {reports.map((report) => (
              <div key={report.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-primary-600" />
                  <div>
                    <p className="font-medium text-gray-900">{report.title}</p>
                    <p className="text-sm text-gray-500">{report.dataset_name} • {new Date(report.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    report.status === 'completed' ? 'bg-green-100 text-green-700' :
                    report.status === 'generating' ? 'bg-yellow-100 text-yellow-700' :
                    report.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {report.status === 'completed' && <CheckCircle className="inline w-3 h-3 mr-1" />}
                    {report.status === 'generating' && <RefreshCw className="inline w-3 h-3 mr-1 animate-spin" />}
                    {report.status === 'failed' && <XCircle className="inline w-3 h-3 mr-1" />}
                    {report.status}
                  </span>
                  {report.status === 'completed' && report.file && (
                    <button
                      onClick={() => handleDownload(report)}
                      className="btn-primary text-sm py-1 px-3 flex items-center gap-1"
                    >
                      <Download size={14} />
                      Download
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Scheduled Reports */}
      {scheduledReports.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Scheduled Reports</h2>
          <div className="space-y-3">
            {scheduledReports.map((sr) => (
              <div key={sr.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">{sr.title}</p>
                  <p className="text-sm text-gray-500">{sr.frequency} • {sr.email_recipients?.join(', ')}</p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${sr.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                  {sr.is_active ? 'Active' : 'Paused'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
