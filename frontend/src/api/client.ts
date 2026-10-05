import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ApiError } from '@/types/api';
import { useAuthStore } from '@/stores/authStore';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

// Request interceptor to add auth token and ensure trailing slash
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add trailing slash to URL if not present (Django convention)
    if (config.url && !config.url.endsWith('/') && !config.url.includes('?')) {
      config.url = `${config.url}/`;
    }

    const token = localStorage.getItem('access_token');

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Clear auth state - ProtectedRoute will handle the redirect via React Router
      useAuthStore.getState().clearAuth();

      return Promise.reject(error);
    }

    // Format error response
    // Backend uses 'message', 'error' (single), or 'errors' (array) as keys
    const data = error.response?.data as any;
    const apiError: ApiError = {
      message:
        data?.message ||
        data?.error ||
        (Array.isArray(data?.errors) ? data.errors.join(', ') : undefined) ||
        (Array.isArray(data?.non_field_errors) ? data.non_field_errors.join(', ') : undefined) ||
        error.message ||
        'An error occurred',
      errors: data?.errors,
      status: error.response?.status,
    };

    return Promise.reject(apiError);
  }
);

export const client = apiClient;
export default apiClient;
