import apiClient from './client';
import {
  LoginCredentials,
  RegisterData,
  AuthResponse,
  ForgotPasswordData,
  ChangePasswordData,
  ResetPasswordData,
  UpdateProfileData,
  User,
} from '@/types/auth';
import { ApiResponse } from '@/types/api';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
    return response.data;
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/register', data);
    return response.data;
  },

  logout: async (refreshToken?: string | null): Promise<void> => {
    await apiClient.post('/auth/logout', {
      refresh: refreshToken || '',
    });
  },

  forgotPassword: async (data: ForgotPasswordData): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/auth/password-reset', data);
    return response.data;
  },

  changePassword: async (data: ChangePasswordData): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/auth/change-password', data);
    return response.data;
  },

  getProfile: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/profile');
    return response.data;
  },

  updateProfile: async (data: UpdateProfileData): Promise<User> => {
    const response = await apiClient.put<User>('/auth/profile', data);
    return response.data;
  },

  resetPassword: async (data: ResetPasswordData): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>(
      '/auth/password-reset/confirm', data,
    );
    return response.data;
  },

  verifyEmail: async (token: string): Promise<{ message: string; email: string }> => {
    const response = await apiClient.post<{ message: string; email: string }>(
      '/auth/verify-email', { token },
    );
    return response.data;
  },

  resendVerification: async (): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(
      '/auth/verify-email/resend',
    );
    return response.data;
  },

  refreshToken: async (): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/token/refresh');
    return response.data;
  },
};

export default authApi;
