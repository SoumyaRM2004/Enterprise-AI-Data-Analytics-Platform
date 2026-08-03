import { useEffect, useState } from 'react';
import { authAPI } from '../services/api';
import { Shield, Search, Clock } from 'lucide-react';

interface AuditLog {
  id: number;
  action: string;
  description: string;
  resource_type: string;
  resource_id: string;
  timestamp: string;
  ip_address: string;
}

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const { data } = await authAPI.getAuditLogs();
      setLogs(data.results || data);
    } catch {
      console.error('Failed to load audit logs');
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = logs.filter(
    (log) =>
      log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.description.toLowerCase().includes(search.toLowerCase())
  );

  const actionColors: Record<string, string> = {
    LOGIN: 'bg-green-100 text-green-700',
    LOGOUT: 'bg-gray-100 text-gray-700',
    REGISTER: 'bg-blue-100 text-blue-700',
    UPLOAD: 'bg-purple-100 text-purple-700',
    DELETE: 'bg-red-100 text-red-700',
    QUERY: 'bg-amber-100 text-amber-700',
    REPORT: 'bg-indigo-100 text-indigo-700',
    FORECAST: 'bg-teal-100 text-teal-700',
    UPDATE: 'bg-orange-100 text-orange-700',
    CREATE: 'bg-cyan-100 text-cyan-700',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
          <p className="text-gray-500 mt-1">Track all actions performed on the platform</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
        <input
          type="text"
          placeholder="Search actions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field pl-10"
        />
      </div>

      {/* Logs Table */}
      <div className="card overflow-x-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No audit logs found.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-4 py-3 text-left font-medium text-gray-700">Action</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Description</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Resource</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">IP Address</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 100).map((log) => (
                <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      actionColors[log.action] || 'bg-gray-100 text-gray-700'
                    }`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{log.description}</td>
                  <td className="px-4 py-3">
                    {log.resource_type && (
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                        {log.resource_type}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{log.ip_address || '-'}</td>
                  <td className="px-4 py-3 text-gray-500">
                    <div className="flex items-center gap-1">
                      <Clock size={12} />
                      {new Date(log.timestamp).toLocaleString()}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
