import { Link, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  CreditCard,
  LayoutDashboard,
  ShieldAlert,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  name: string;
  href: string;
  icon: typeof LayoutDashboard;
}

/**
 * Ordered by how often an operator reaches for each, not by hierarchy.
 * Deliverability sits high because it is the one thing that can damage every
 * tenant at once — all of them send from one IP.
 */
const navigation: NavItem[] = [
  { name: 'Overview', href: '/landlord', icon: LayoutDashboard },
  { name: 'Tenants', href: '/landlord/tenants', icon: Building2 },
  { name: 'Deliverability', href: '/landlord/deliverability', icon: ShieldAlert },
  { name: 'Revenue', href: '/landlord/revenue', icon: CreditCard },
];

interface LandlordSidebarProps {
  collapsed: boolean;
  open: boolean;
  onNavigate: () => void;
}

export const LandlordSidebar = ({ collapsed, open, onNavigate }: LandlordSidebarProps) => {
  const { pathname } = useLocation();

  // `/landlord` would otherwise light up for every child route beneath it.
  const isActive = (href: string) =>
    href === '/landlord' ? pathname === href : pathname.startsWith(href);

  return (
    <aside
      className={cn(
        'fixed bottom-0 left-0 top-14 z-40 flex flex-col gap-4 overflow-hidden border-r bg-sidebar py-3 transition-[width,transform] duration-200',
        collapsed ? 'w-[68px] px-2' : 'w-[238px] px-3',
        open ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:translate-x-0'
      )}
      aria-label="Platform navigation"
    >
      <nav className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto overflow-x-hidden">
        {!collapsed && <p className="eyebrow mb-1.5 px-2">Platform</p>}
        {collapsed && <span className="mx-auto mb-1.5 h-px w-5 bg-border" aria-hidden="true" />}

        {navigation.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              to={item.href}
              onClick={onNavigate}
              title={collapsed ? item.name : undefined}
              className={cn(
                'flex items-center gap-2.5 rounded-md border border-transparent py-2 text-[13.5px] font-medium transition-colors',
                collapsed ? 'justify-center px-0' : 'px-2.5',
                active
                  ? 'border-border bg-accent font-semibold text-foreground'
                  : 'text-muted-foreground hover:bg-card hover:text-foreground'
              )}
            >
              <item.icon
                className={cn(
                  'h-4 w-4 flex-none',
                  active ? 'text-brand' : 'text-subtle-foreground'
                )}
              />
              {!collapsed && <span className="truncate">{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-none flex-col gap-3">
        {/* Every screen here shows other people's data. The warning is the one
            piece of chrome that should not be subtle, and the way out is kept
            next to it. */}
        {!collapsed && (
          <div className="rounded-[var(--radius)] border border-warning/40 bg-warning/[.08] p-3">
            <p className="text-[12px] font-semibold text-foreground">Cross-tenant view</p>
            <p className="mt-0.5 text-[11.5px] leading-snug text-muted-foreground">
              You are seeing every customer's data. Actions here affect real accounts.
            </p>
          </div>
        )}

        <Link
          to="/dashboard"
          onClick={onNavigate}
          title={collapsed ? 'Leave console' : undefined}
          className={cn(
            'flex items-center gap-2.5 rounded-md border border-transparent py-2 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-card hover:text-foreground',
            collapsed ? 'justify-center px-0' : 'px-2.5'
          )}
        >
          <ArrowLeft className="h-4 w-4 flex-none text-subtle-foreground" />
          {!collapsed && <span className="truncate">Leave console</span>}
        </Link>
      </div>
    </aside>
  );
};
