import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Organization } from '@/types/auth';

interface AuthState {
  user: User | null;
  organization: Organization | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  _hasHydrated: boolean;
  /** `organization` is null for platform staff, who belong to no tenant. */
  setAuth: (
    user: User,
    organization: Organization | null,
    accessToken: string,
    refreshToken?: string,
  ) => void;
  clearAuth: () => void;
  updateUser: (user: User) => void;
  setHasHydrated: (hasHydrated: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      organization: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      _hasHydrated: false,

      setAuth: (user, organization, accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        set({
          user,
          organization,
          accessToken,
          refreshToken: refreshToken || null,
          isAuthenticated: true,
        });
      },

      clearAuth: () => {
        localStorage.removeItem('access_token');
        set({
          user: null,
          organization: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      updateUser: (user) => {
        // The organization rides along, because it was only ever written by
        // setAuth: a plan change (or anything else about the org) stayed
        // invisible until the next sign-in, which made every plan-gated
        // feature look broken right after an upgrade.
        set(user.organization ? { user, organization: user.organization } : { user });
      },

      setHasHydrated: (hasHydrated) => {
        set({ _hasHydrated: hasHydrated });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        organization: state.organization,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
