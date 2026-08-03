import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../utils/store';
import {
  LayoutDashboard,
  Database,
  Upload,
  MessageSquare,
  FileText,
  TrendingUp,
  Settings,
  Shield,
  LogOut,
  Menu,
  X,
  Brain,
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/datasets', icon: Database, label: 'Datasets' },
  { path: '/datasets/upload', icon: Upload, label: 'Upload' },
  { path: '/chat', icon: MessageSquare, label: 'AI Chat' },
  { path: '/reports', icon: FileText, label: 'Reports' },
  { path: '/forecasting', icon: TrendingUp, label: 'Forecasting' },
  { path: '/settings', icon: Settings, label: 'Settings' },
  { path: '/audit-logs', icon: Shield, label: 'Audit Logs' },
];

export default function MainLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-white border-r border-gray-200 flex flex-col transition-all duration-300 fixed h-full z-30`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          {sidebarOpen ? (
            <div className="flex items-center gap-2">
              <Brain className="w-8 h-8 text-primary-600" />
              <div>
                <h1 className="font-bold text-lg text-gray-900">AI Analytics</h1>
                <p className="text-xs text-gray-500">Enterprise Platform</p>
              </div>
            </div>
          ) : (
            <Brain className="w-8 h-8 text-primary-600 mx-auto" />
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 rounded hover:bg-gray-100"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <item.icon size={20} />
              {sidebarOpen && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-gray-200">
          {sidebarOpen && user && (
            <div className="mb-3">
              <p className="text-sm font-medium text-gray-900">{user.username}</p>
              <p className="text-xs text-gray-500">{user.role} {user.company && `• ${user.company}`}</p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors w-full"
          >
            <LogOut size={18} />
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className={`flex-1 ${sidebarOpen ? 'ml-64' : 'ml-20'} transition-all duration-300`}>
        <div className="p-6 overflow-y-auto h-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
