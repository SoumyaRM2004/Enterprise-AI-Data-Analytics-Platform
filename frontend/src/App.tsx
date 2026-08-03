import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './utils/store';
import { useEffect } from 'react';

// Layouts
import MainLayout from './components/MainLayout';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import DatasetsPage from './pages/DatasetsPage';
import DatasetDetailPage from './pages/DatasetDetailPage';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import ReportsPage from './pages/ReportsPage';
import ForecastingPage from './pages/ForecastingPage';
import SettingsPage from './pages/SettingsPage';
import AuditLogPage from './pages/AuditLogPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" />;
  return <>{children}</>;
}

function App() {
  const fetchProfile = useAuthStore((s) => s.fetchProfile);

  useEffect(() => {
    if (localStorage.getItem('access_token')) {
      fetchProfile();
    }
  }, []);

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="datasets/upload" element={<UploadPage />} />
          <Route path="datasets/:id" element={<DatasetDetailPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="forecasting" element={<ForecastingPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="audit-logs" element={<AuditLogPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
