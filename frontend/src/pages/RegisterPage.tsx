import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../utils/store';
import { Brain } from 'lucide-react';
import toast from 'react-hot-toast';

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    company: '',
  });
  const { register, isLoading, error } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await register(formData);
      toast.success('Account created! Please log in.');
      navigate('/login');
    } catch {
      toast.error('Registration failed');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-gray-100 py-12">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center mb-8">
            <Brain className="w-12 h-12 text-primary-600 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900">Create Account</h1>
            <p className="text-gray-500 mt-1">Join the AI Analytics Platform</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <input
                name="first_name"
                placeholder="First name"
                onChange={handleChange}
                className="input-field"
              />
              <input
                name="last_name"
                placeholder="Last name"
                onChange={handleChange}
                className="input-field"
              />
            </div>
            <input
              name="username"
              placeholder="Username"
              onChange={handleChange}
              className="input-field"
              required
            />
            <input
              name="email"
              type="email"
              placeholder="Email"
              onChange={handleChange}
              className="input-field"
              required
            />
            <input
              name="company"
              placeholder="Company (optional)"
              onChange={handleChange}
              className="input-field"
            />
            <input
              name="password"
              type="password"
              placeholder="Password (min 8 characters)"
              onChange={handleChange}
              className="input-field"
              required
              minLength={8}
            />
            <input
              name="password_confirm"
              type="password"
              placeholder="Confirm password"
              onChange={handleChange}
              className="input-field"
              required
              minLength={8}
            />

            {error && (
              <div className="text-red-600 text-sm">
                {typeof error === 'object'
                  ? Object.values(error).flat().join(', ')
                  : error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-3 disabled:opacity-50"
            >
              {isLoading ? 'Creating...' : 'Create Account'}
            </button>
          </form>

          <p className="text-center mt-6 text-sm text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
