import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/authStore';
import { authApi } from '@/api/auth';
import {
  LoginCredentials,
  RegisterData,
  ForgotPasswordData,
  ChangePasswordData,
  UpdateProfileData,
} from '@/types/auth';

export const useAuth = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setAuth, clearAuth, user, organization, isAuthenticated } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      // Backend returns: { user, tokens: { access, refresh }, message }
      // user.organization is nested inside user object
      setAuth(data.user, data.user.organization, data.tokens.access, data.tokens.refresh);
      toast.success('Login successful!');
      navigate('/contacts');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Login failed');
    },
  });

  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: (data) => {
      // Backend returns: { user, tokens: { access, refresh }, message }
      setAuth(data.user, data.user.organization, data.tokens.access, data.tokens.refresh);
      toast.success('Registration successful!');
      navigate('/contacts');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Registration failed');
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(useAuthStore.getState().refreshToken),
    onSuccess: () => {
      clearAuth();
      queryClient.clear();
      toast.success('Logged out successfully');
      navigate('/login');
    },
    onError: () => {
      // Even if API call fails, clear local auth
      clearAuth();
      queryClient.clear();
      navigate('/login');
    },
  });

  const forgotPasswordMutation = useMutation({
    mutationFn: authApi.forgotPassword,
    onSuccess: (data) => {
      toast.success(data.data.message || 'Password reset email sent!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to send reset email');
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: (data) => {
      toast.success(data.data.message || 'Password changed successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to change password');
    },
  });

  const updateProfileMutation = useMutation({
    mutationFn: authApi.updateProfile,
    onSuccess: (data) => {
      useAuthStore.getState().updateUser(data);
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      toast.success('Profile updated successfully!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update profile');
    },
  });

  const { data: profile, isLoading: isLoadingProfile } = useQuery({
    queryKey: ['profile'],
    queryFn: authApi.getProfile,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    user,
    organization,
    isAuthenticated,
    profile,
    isLoadingProfile,
    login: (credentials: LoginCredentials) => loginMutation.mutate(credentials),
    register: (data: RegisterData) => registerMutation.mutate(data),
    logout: () => logoutMutation.mutate(),
    forgotPassword: (data: ForgotPasswordData) => forgotPasswordMutation.mutate(data),
    changePassword: (data: ChangePasswordData) => changePasswordMutation.mutate(data),
    updateProfile: (data: UpdateProfileData) => updateProfileMutation.mutate(data),
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
  };
};
