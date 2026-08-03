import { create } from 'zustand';
import { authAPI } from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  company: string;
  date_joined: string;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
  fetchProfile: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await authAPI.login(username, password);
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      // Fetch profile
      const profileRes = await authAPI.getProfile();
      set({
        user: profileRes.data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Login failed',
        isLoading: false,
      });
      throw error;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      await authAPI.register(data);
      set({ isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data || 'Registration failed',
        isLoading: false,
      });
      throw error;
    }
  },

  logout: () => {
    authAPI.logout().catch(() => {});
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false, error: null });
  },

  fetchProfile: async () => {
    try {
      const { data } = await authAPI.getProfile();
      set({ user: data, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  },

  clearError: () => set({ error: null }),
}));

// Dataset store
interface DatasetState {
  datasets: any[];
  currentDataset: any | null;
  isLoading: boolean;
  fetchDatasets: (params?: any) => Promise<void>;
  fetchDataset: (id: string) => Promise<void>;
  setCurrentDataset: (dataset: any | null) => void;
}

export const useDatasetStore = create<DatasetState>((set) => ({
  datasets: [],
  currentDataset: null,
  isLoading: false,

  fetchDatasets: async (params) => {
    set({ isLoading: true });
    try {
      const { data } = await import('../services/api').then(m => m.datasetsAPI.list(params));
      set({ datasets: data.results || data, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  fetchDataset: async (id) => {
    set({ isLoading: true });
    try {
      const { data } = await import('../services/api').then(m => m.datasetsAPI.get(id));
      set({ currentDataset: data, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  setCurrentDataset: (dataset) => set({ currentDataset: dataset }),
}));

// Chat store
interface ChatState {
  sessions: any[];
  currentSession: any | null;
  messages: any[];
  isLoading: boolean;
  fetchSessions: () => Promise<void>;
  setCurrentSession: (session: any | null) => void;
  addMessage: (message: any) => void;
  setMessages: (messages: any[]) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  sessions: [],
  currentSession: null,
  messages: [],
  isLoading: false,

  fetchSessions: async () => {
    try {
      const { data } = await import('../services/api').then(m => m.chatbotAPI.listSessions());
      set({ sessions: data.results || data });
    } catch {}
  },

  setCurrentSession: (session) => set({ currentSession: session, messages: [] }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  setMessages: (messages) => set({ messages }),
}));
