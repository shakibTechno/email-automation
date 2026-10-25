import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Mail,
  Zap,
  FileText,
  BarChart3,
  Settings,
  Tags,
  LayoutTemplate,
  Layout,
  Filter,
  HeartHandshake,
  Building2,
  CreditCard,
  Puzzle,
  ListOrdered,
  Sparkles,
  ArrowRight,
  ChevronDown,
  ShieldAlert,
} from 'lucide-react';
import { cn, getInitials } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';

type NavItem = { name: string; href: string; icon: typeof LayoutDashboard };
type NavGroup = { label: string; items: NavItem[] };

/**
 * Grouped by the job each screen does, not alphabetically — the groups mirror
 * the lifecycle a contact moves through: captured, organised, engaged, closed.
 */
const navigation: NavGroup[] = [
  {
    label: 'Workspace',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Contacts', href: '/contacts', icon: Users },
      { name: 'Tags', href: '/contacts/tags', icon: Tags },
      { name: 'Segments', href: '/segments', icon: Filter },
    ],
  },
  {
    label: 'Engage',
    items: [
      { name: 'Campaigns', href: '/campaigns', icon: Mail },
      { name: 'Sequences', href: '/sequences', icon: ListOrdered },
      { name: 'Workflows', href: '/workflows', icon: Zap },
      { name: 'Templates', href: '/templates', icon: LayoutTemplate },
    ],
  },
  {
    label: 'Capture',
    items: [
      { name: 'Forms', href: '/forms', icon: FileText },
      { name: 'Landing Pages', href: '/landing-pages', icon: Layout },
    ],
  },
  {
    label: 'Sales',
    items: [
      { name: 'Pipeline', href: '/crm', icon: HeartHandshake },
      { name: 'Companies', href: '/crm/companies', icon: Building2 },
    ],
  },
  {
    label: 'Insight',
    items: [{ name: 'Analytics', href: '/analytics', icon: BarChart3 }],
  },
  {
    label: 'Account',
    items: [
      { name: 'Integrations', href: '/integrations', icon: Puzzle },
      { name: 'Billing', href: '/billing', icon: CreditCard },
      { name: 'Settings', href: '/settings', icon: Settings },
    ],
  },
];

/** `/crm` must not light up for `/crm/companies`, so exact-match the siblings. */
const useIsActive = () => {
  const { pathname } = useLocation();
  return (href: string) => {
    const exactOnly = ['/crm', '/contacts'];
    if (exactOnly.includes(href)) {
      // `/contacts` must not stay lit on `/contacts/tags`, which is its own entry.
      const childPrefixes = ['/crm/companies', '/contacts/tags'];
      if (childPrefixes.some((p) => pathname.startsWith(p))) return false;
    }
    return pathname === href || pathname.startsWith(href + '/');
  };
};

interface SidebarProps {
  /** Desktop: narrow the rail to icons only. */
  collapsed: boolean;
  /** Below lg: the rail is an overlay drawer. */
  open: boolean;
  onNavigate: () => void;
}

export const Sidebar = ({ collapsed, open, onNavigate }: SidebarProps) => {
  const isActive = useIsActive();
  const { user, organization } = useAuth();

  return (
    <aside
      className={cn(
        // Attached to the left edge, under the fixed ribbon. No rounding, no
        // gap — the rail and the ribbon read as one piece of chrome.
        'fixed bottom-0 left-0 top-14 z-40 flex flex-col gap-4 overflow-hidden border-r bg-sidebar py-3 transition-[width,transform] duration-200',
        collapsed ? 'w-[68px] px-2' : 'w-[238px] px-3',
        // Below lg it slides in over the content instead of squeezing it.
        open ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:translate-x-0'
      )}
      aria-label="Main navigation"
    >
      <nav className="flex min-h-0 flex-1 flex-col gap-[18px] overflow-y-auto overflow-x-hidden">
        {navigation.map((group) => (
          <div key={group.label} className="flex flex-none flex-col gap-0.5">
            {!collapsed && <p className="eyebrow mb-1.5 px-2">{group.label}</p>}
            {collapsed && <span className="mx-auto mb-1.5 h-px w-5 bg-border" aria-hidden="true" />}

            {group.items.map((item) => {
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
          </div>
        ))}
      </nav>

      <div className="flex flex-none flex-col gap-3">
        {/* The only way into the cross-tenant console from the tenant app.
            Hidden entirely for customers — they have no reason to know it
            exists, and the API refuses them regardless. */}
        {user?.is_staff && (
          <Link
            to="/landlord"
            onClick={onNavigate}
            title={collapsed ? 'Platform console' : undefined}
            className={cn(
              'flex items-center gap-2.5 rounded-md border border-warning/40 bg-warning/[.08] py-2 text-[13px] font-medium text-foreground transition-colors hover:bg-warning/[.14]',
              collapsed ? 'justify-center px-0' : 'px-2.5'
            )}
          >
            <ShieldAlert className="h-4 w-4 flex-none text-warning" />
            {!collapsed && <span className="truncate">Platform console</span>}
          </Link>
        )}

        {!collapsed && (
          <div className="rounded-[var(--radius)] border bg-secondary/60 p-3.5 text-center [background-image:radial-gradient(130%_90%_at_50%_0%,hsl(var(--brand-dim)/.20),transparent_62%)]">
            <span className="mx-auto mb-2 grid h-7 w-7 place-items-center rounded-lg bg-brand-fill text-brand-ink">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <h4 className="mb-1 text-[13px] font-bold tracking-tight">Upgrade to Business</h4>
            <p className="mb-2.5 text-[11px] leading-snug text-muted-foreground">
              Unlimited automations and dedicated IP warm-up.
            </p>
            <Link
              to="/billing"
              onClick={onNavigate}
              className="flex items-center justify-center gap-1.5 rounded-md bg-brand-fill px-3 py-1.5 text-[11.5px] font-bold text-brand-ink hover:brightness-105"
            >
              Compare plans <ArrowRight className="h-3 w-3 flex-none" />
            </Link>
          </div>
        )}

        <Link
          to="/profile"
          onClick={onNavigate}
          title={collapsed ? organization?.name ?? 'Profile' : undefined}
          className={cn(
            'flex items-center gap-2.5 rounded-md py-1 hover:bg-card',
            collapsed ? 'justify-center px-0' : 'px-1.5'
          )}
        >
          <span className="grid h-8 w-8 flex-none place-items-center rounded-full bg-brand-fill text-[13px] font-extrabold text-brand-ink">
            {user ? getInitials(user.first_name, user.last_name) : '—'}
          </span>
          {!collapsed && (
            <>
              <span className="min-w-0 flex-1">
                <b className="block truncate text-[13px] font-semibold tracking-tight">
                  {organization?.name ?? 'Workspace'}
                </b>
                <span className="block truncate text-[11px] capitalize text-subtle-foreground">
                  {organization?.plan ? `${organization.plan} plan` : user?.email ?? ''}
                </span>
              </span>
              <ChevronDown className="h-3.5 w-3.5 flex-none text-subtle-foreground" />
            </>
          )}
        </Link>
      </div>
    </aside>
  );
};
