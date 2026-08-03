import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { datasetsAPI } from '../services/api';
import { Upload, FileSpreadsheet, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      if (!name) {
        setName(f.name.replace(/\.[^.]+$/, ''));
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name || file.name);

    try {
      const { data } = await datasetsAPI.upload(formData);
      setUploadProgress(true);
      toast.success('Dataset uploaded! Processing...');

      // Poll for status
      const checkStatus = async () => {
        try {
          const res = await datasetsAPI.get(data.id);
          if (res.data.status === 'ready') {
            toast.success('Dataset is ready!');
            navigate(`/datasets/${data.id}`);
          } else if (res.data.status === 'error') {
            toast.error('Processing failed');
            setIsUploading(false);
          } else {
            setTimeout(checkStatus, 3000);
          }
        } catch {
          setTimeout(checkStatus, 5000);
        }
      };
      setTimeout(checkStatus, 5000);
    } catch (error: any) {
      toast.error(error.response?.data?.file?.[0] || 'Upload failed');
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Dataset</h1>
        <p className="text-gray-500 mt-1">Upload a CSV or Excel file to begin analysis</p>
      </div>

      <form onSubmit={handleUpload} className="card space-y-6">
        {/* File Drop Zone */}
        <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-primary-400 transition-colors">
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.tsv"
            onChange={handleFileChange}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 font-medium">
              {file ? file.name : 'Click to select a file'}
            </p>
            <p className="text-sm text-gray-400 mt-1">
              Supports CSV, XLSX, XLS, TSV (max 100MB)
            </p>
          </label>
        </div>

        {/* Dataset Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Dataset Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input-field"
            placeholder="My Dataset"
          />
        </div>

        {/* File Details */}
        {file && (
          <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
            <FileSpreadsheet className="w-5 h-5 text-green-600" />
            <div className="text-sm">
              <p className="font-medium text-gray-900">{file.name}</p>
              <p className="text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
            <CheckCircle className="w-5 h-5 text-green-600 ml-auto" />
          </div>
        )}

        <button
          type="submit"
          disabled={!file || isUploading}
          className="btn-primary w-full py-3 disabled:opacity-50"
        >
          {isUploading ? 'Uploading & Processing...' : 'Upload Dataset'}
        </button>

        {uploadProgress && (
          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
            <div className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-primary-700">Processing your dataset. This may take a moment...</p>
          </div>
        )}
      </form>

      {/* Supported Formats */}
      <div className="card">
        <h3 className="font-semibold text-gray-900 mb-3">Supported Formats</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { ext: 'CSV', desc: 'Comma-separated values' },
            { ext: 'TSV', desc: 'Tab-separated values' },
            { ext: 'XLSX', desc: 'Excel workbook' },
            { ext: 'XLS', desc: 'Excel 97-2003' },
          ].map((fmt) => (
            <div key={fmt.ext} className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="font-bold text-primary-600">{fmt.ext}</p>
              <p className="text-xs text-gray-500">{fmt.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
