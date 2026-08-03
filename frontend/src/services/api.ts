import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/login/token/refresh/`, {
            refresh: refreshToken,
          });
          localStorage.setItem('access_token', data.access);
          originalRequest.headers.Authorization = `Bearer ${data.access}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login/', { username, password }),
  register: (data: { username: string; email: string; password: string; password_confirm: string }) =>
    api.post('/auth/register/', data),
  getProfile: () => api.get('/auth/profile/'),
  updateProfile: (data: any) => api.patch('/auth/profile/', data),
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post('/auth/change-password/', data),
  logout: () => api.post('/auth/logout/'),
  getUsers: () => api.get('/auth/users/'),
  getAuditLogs: (params?: any) => api.get('/auth/audit-logs/', { params }),
};

// Datasets API
export const datasetsAPI = {
  list: (params?: any) => api.get('/datasets/', { params }),
  upload: (formData: FormData) =>
    api.post('/datasets/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  get: (id: string) => api.get(`/datasets/${id}/`),
  delete: (id: string) => api.delete(`/datasets/${id}/`),
  getProfile: (id: string) => api.get(`/datasets/${id}/profile/`),
  getVersions: (id: string) => api.get(`/datasets/${id}/versions/`),
  getCleaningJobs: (id: string) => api.get(`/datasets/${id}/cleaning/`),
  createCleaningJob: (id: string, data: any) =>
    api.post(`/datasets/${id}/cleaning/`, data),
};

// Projects API
export const projectsAPI = {
  list: () => api.get('/datasets/projects/'),
  create: (data: any) => api.post('/datasets/projects/', data),
  get: (id: number) => api.get(`/datasets/projects/${id}/`),
  update: (id: number, data: any) => api.patch(`/datasets/projects/${id}/`, data),
  delete: (id: number) => api.delete(`/datasets/projects/${id}/`),
};

// Analytics API
export const analyticsAPI = {
  getDashboard: (datasetId: string) => api.get(`/analytics/dashboard/${datasetId}/`),
  getChartData: (datasetId: string, params: any) =>
    api.get(`/analytics/dashboard/${datasetId}/chart/`, { params }),
  executeQuery: (datasetId: string, sql: string) =>
    api.post(`/analytics/dashboard/${datasetId}/query/`, { sql }),
  generateReport: (datasetId: string) =>
    api.post(`/analytics/dashboard/${datasetId}/generate-report/`),
  getReports: () => api.get('/analytics/reports/'),
  getSavedQueries: () => api.get('/analytics/queries/'),
  createSavedQuery: (data: any) => api.post('/analytics/queries/', data),
  getWidgets: () => api.get('/analytics/widgets/'),
  createWidget: (data: any) => api.post('/analytics/widgets/', data),
};

// Chatbot API
export const chatbotAPI = {
  listSessions: () => api.get('/chatbot/sessions/'),
  createSession: (data: any) => api.post('/chatbot/sessions/', data),
  getSession: (id: number) => api.get(`/chatbot/sessions/${id}/`),
  deleteSession: (id: number) => api.delete(`/chatbot/sessions/${id}/`),
  sendMessage: (sessionId: number, data: { message: string; message_type?: string }) =>
    api.post(`/chatbot/sessions/${sessionId}/send/`, data),
  getProviders: () => api.get('/chatbot/providers/'),
};

// Forecasting API
export const forecastingAPI = {
  list: () => api.get('/forecasting/'),
  create: (datasetId: string, data: any) =>
    api.post(`/forecasting/${datasetId}/create/`, data),
  getDetail: (id: number) => api.get(`/forecasting/${id}/detail/`),
  delete: (id: number) => api.delete(`/forecasting/${id}/`),
  getAnomalies: () => api.get('/forecasting/anomalies/'),
  createAnomalyDetection: (datasetId: string, data: any) =>
    api.post(`/forecasting/${datasetId}/anomalies/`, data),
  deleteAnomaly: (id: number) => api.delete(`/forecasting/anomalies/${id}/`),
};

// Reports API
export const reportsAPI = {
  list: () => api.get('/reports/'),
  generate: (datasetId: string, data?: any) =>
    api.post(`/reports/${datasetId}/generate/`, data),
  getDetail: (id: number) => api.get(`/reports/${id}/`),
  delete: (id: number) => api.delete(`/reports/${id}/`),
  download: (id: number) =>
    api.get(`/reports/${id}/download/`, { responseType: 'blob' }),
  getScheduled: () => api.get('/reports/scheduled/'),
  createScheduled: (data: any) => api.post('/reports/scheduled/', data),
};

export default api;
