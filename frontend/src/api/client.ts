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

    // `apps.core.exceptions.custom_exception_handler` answers every validation
    // failure with message: "Validation error" and puts what actually went
    // wrong in `details`. Taking `message` alone turned "Old password is
    // incorrect." into a bare "Validation error" with nothing to act on, so
    // the field messages win when there are any.
    const fieldMessages = (() => {
      const details = data?.details;
      if (!details || typeof details !== 'object' || Array.isArray(details)) return undefined;
      const parts = Object.values(details as Record<string, unknown>)
        .flatMap((v) => (Array.isArray(v) ? v : [v]))
        .filter((v): v is string => typeof v === 'string' && v.trim().length > 0);
      return parts.length ? parts.join(' ') : undefined;
    })();

    const apiError: ApiError = {
      message:
        fieldMessages ||
        data?.message ||
        data?.error ||
        (Array.isArray(data?.errors) ? data.errors.join(', ') : undefined) ||
        (Array.isArray(data?.non_field_errors) ? data.non_field_errors.join(', ') : undefined) ||
        error.message ||
        'An error occurred',
      errors: data?.errors ?? data?.details,
      status: error.response?.status,
    };

    return Promise.reject(apiError);
  }
);

export const client = apiClient;
export default apiClient;
