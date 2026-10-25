import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Menu, PanelLeft } from 'lucide-react';
import { LandlordSidebar } from './LandlordSidebar';
import { useSidebar } from '@/lib/useSidebar';
import { useAuthStore } from '@/stores/authStore';
import { cn } from '@/lib/utils';

/**
 * Shell for the landlord console.
 *
 * Mirrors AppLayout's geometry so the two feel like one product, with its own
 * ribbon rather than a reused Header — that one hardcodes links to /dashboard,
 * /profile and /settings, all of which mean the tenant app.
 *
 * The ribbon is tinted and labelled on purpose. Every screen beneath it shows
 * other customers' data, and an operator who forgets which app they are in is
 * one click from suspending the wrong account.
 */
export const LandlordLayout = () => {
  // Its own storage key: collapsing this rail must not collapse the tenant one.
  const { collapsed, open, toggleCollapsed, toggleOpen, close } =
    useSidebar('mailflow-landlord-sidebar-collapsed');
  const { pathname } = useLocation();
  const user = useAuthStore((s) => s.user);

  useEffect(() => close(), [pathname, close]);

  return (
    <div className="app-ground min-h-screen">
      <header className="fixed inset-x-0 top-0 z-50 flex h-14 items-center gap-2 border-b border-warning/30 bg-warning/[.07] px-3 backdrop-blur">
        <div
          className={cn(
            'flex items-center gap-2 transition-[width] duration-200',
            collapsed ? 'lg:w-[52px]' : 'lg:w-[222px]'
          )}
        >
          <button
            type="button"
            onClick={toggleOpen}
            aria-label="Toggle navigation"
            className="grid h-8 w-8 place-items-center rounded-md text-muted-foreground hover:bg-card hover:text-foreground lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
            className="hidden h-8 w-8 place-items-center rounded-md text-muted-foreground hover:bg-card hover:text-foreground lg:grid"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
          {!collapsed && (
            <span className="hidden text-[13.5px] font-bold tracking-tight lg:inline">
              Platform console
            </span>
          )}
        </div>

        <span className="rounded border border-warning/50 bg-warning/[.14] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-foreground">
          Cross-tenant
        </span>

        <span className="ml-auto truncate text-[12.5px] text-muted-foreground">
          {user?.email}
        </span>
      </header>

      <LandlordSidebar collapsed={collapsed} open={open} onNavigate={close} />

      {open && (
        <button
          type="button"
          onClick={close}
          aria-label="Close navigation"
          className="fixed inset-0 top-14 z-30 bg-foreground/30 lg:hidden"
        />
      )}

      <div
        className={cn(
          'pt-14 transition-[margin] duration-200',
          collapsed ? 'lg:ml-[68px]' : 'lg:ml-[238px]'
        )}
      >
        <main className="min-w-0 p-3.5">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
