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
  Send,
  ArrowRight,
  ChevronDown,
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
      return pathname === href || /^\/(crm|contacts)\/(?!companies|tags)/.test(pathname)
        ? pathname.startsWith(href)
        : pathname === href;
    }
    return pathname === href || pathname.startsWith(href + '/');
  };
};

export const Sidebar = () => {
  const isActive = useIsActive();
  const { user, organization } = useAuth();

  return (
    <aside className="flex w-full flex-none flex-row flex-wrap items-center gap-3 rounded-[var(--radius)] border bg-sidebar p-3 lg:sticky lg:top-3.5 lg:max-h-[calc(100vh-1.75rem)] lg:w-[238px] lg:flex-col lg:items-stretch lg:gap-[18px] lg:overflow-y-auto lg:pt-4">
      {/* brand */}
      <div className="flex items-center gap-2.5 px-1.5">
        <span className="grid h-7 w-7 flex-none place-items-center rounded-lg bg-brand-fill text-brand-ink">
          <Send className="h-3.5 w-3.5" />
        </span>
        <b className="text-[15px] font-extrabold tracking-tight">Cadence</b>
        <ChevronDown className="ml-auto h-3.5 w-3.5 text-subtle-foreground" />
      </div>

      {/* grouped navigation */}
      {navigation.map((group) => (
        <div key={group.label} className="flex flex-row flex-wrap gap-1 lg:flex-col lg:gap-0.5">
          <p className="eyebrow mb-1.5 hidden px-2 lg:block">{group.label}</p>
          {group.items.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md border border-transparent px-2.5 py-2 text-[13.5px] font-medium transition-colors',
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
                {item.name}
              </Link>
            );
          })}
        </div>
      ))}

      {/* upgrade promo */}
      <div className="hidden lg:mt-auto lg:block rounded-[var(--radius)] border bg-secondary/60 p-4 text-center [background-image:radial-gradient(130%_90%_at_50%_0%,hsl(var(--brand-dim)/.20),transparent_62%)]">
        <span className="mx-auto mb-2.5 grid h-[30px] w-[30px] place-items-center rounded-lg bg-brand-fill text-brand-ink">
          <Sparkles className="h-3.5 w-3.5" />
        </span>
        <h4 className="mb-1 text-sm font-bold">Upgrade to Business</h4>
        <p className="mb-3 text-[11.5px] leading-snug text-muted-foreground">
          Unlimited automations, predictive send times and dedicated IP warm-up.
        </p>
        <Link
          to="/billing"
          className="flex w-full items-center justify-center gap-1.5 rounded-md bg-brand-fill px-3 py-1.5 text-xs font-bold text-brand-ink hover:brightness-105"
        >
          Compare plans <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {/* account */}
      <Link to="/profile" className="ml-auto flex items-center gap-2.5 rounded-md px-1.5 py-1 hover:bg-card lg:ml-0">
        <span className="grid h-8 w-8 flex-none place-items-center rounded-full bg-brand-fill text-[13px] font-extrabold text-brand-ink">
          {user ? getInitials(user.first_name, user.last_name) : '—'}
        </span>
        <span className="min-w-0">
          <b className="block truncate text-[13px] font-semibold tracking-tight">
            {organization?.name ?? 'Workspace'}
          </b>
          <span className="block truncate text-[11px] capitalize text-subtle-foreground">
            {organization?.plan ? `${organization.plan} plan` : user?.email ?? ''}
          </span>
        </span>
        <ChevronDown className="ml-auto h-3.5 w-3.5 flex-none text-subtle-foreground" />
      </Link>
    </aside>
  );
};
