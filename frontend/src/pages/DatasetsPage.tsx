import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { datasetsAPI } from '../services/api';
import { Database, Search, Plus, Trash2, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

interface Dataset {
  id: string;
  name: string;
  status: string;
  row_count: number;
  column_count: number;
  file_type: string;
  data_quality_score: number;
  created_at: string;
  project_name: string | null;
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    setIsLoading(true);
    try {
      const { data } = await datasetsAPI.list();
      setDatasets(data.results || data);
    } catch {
      toast.error('Failed to load datasets');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await datasetsAPI.delete(id);
      setDatasets(datasets.filter((d) => d.id !== id));
      toast.success('Dataset deleted');
    } catch {
      toast.error('Failed to delete dataset');
    }
  };

  const filtered = datasets.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Datasets</h1>
          <p className="text-gray-500 mt-1">Manage your uploaded datasets</p>
        </div>
        <button
          onClick={() => navigate('/datasets/upload')}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={18} />
          Upload Dataset
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
        <input
          type="text"
          placeholder="Search datasets..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field pl-10 max-w-md"
        />
      </div>

      {/* Dataset Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-primary-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-12">
          <Database className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No datasets found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((ds) => (
            <div key={ds.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-primary-600" />
                  <h3 className="font-medium text-gray-900 truncate max-w-[200px]">{ds.name}</h3>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  ds.status === 'ready' ? 'bg-green-100 text-green-700' :
                  ds.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                  ds.status === 'error' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {ds.status}
                </span>
              </div>

              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Rows</span>
                  <span className="font-medium">{ds.row_count?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Columns</span>
                  <span className="font-medium">{ds.column_count}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Type</span>
                  <span className="font-medium uppercase">{ds.file_type || 'CSV'}</span>
                </div>
                {ds.data_quality_score > 0 && (
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">Quality</span>
                      <span className="font-medium">{ds.data_quality_score}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-green-500"
                        style={{ width: `${ds.data_quality_score}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100 flex gap-2">
                <button
                  onClick={() => navigate(`/datasets/${ds.id}`)}
                  className="btn-primary text-sm flex-1"
                >
                  View
                </button>
                <button
                  onClick={() => handleDelete(ds.id, ds.name)}
                  className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
