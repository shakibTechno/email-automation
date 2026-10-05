import { Search, SlidersHorizontal, Sun, Moon, User } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/hooks/useAuth';
import { cn, getInitials } from '@/lib/utils';
import { useTheme } from '@/lib/theme';
import { NotificationBell } from '@/components/notifications/NotificationBell';

/**
 * Page titles live here rather than in each page so the topbar stays one
 * component. Longest prefix wins, so detail routes inherit their section.
 */
const PAGE_TITLES: Array<[string, string, string]> = [
  ['/dashboard', 'Overview', 'Audience growth, sending health and pipeline at a glance.'],
  ['/contacts/tags', 'Tags', 'The shared labels forms, workflows and segments all read.'],
  ['/contacts', 'Contacts', 'Everyone in your organization, with score and engagement.'],
  ['/segments', 'Segments', 'Saved audiences — dynamic rules or a curated list.'],
  ['/campaigns', 'Campaigns', 'One message to many people, now or scheduled.'],
  ['/sequences', 'Sequences', 'Fixed series of emails spaced over days.'],
  ['/workflows', 'Workflows', 'Branching automations that react to behaviour.'],
  ['/templates', 'Email templates', 'Reusable designs for campaigns and sequences.'],
  ['/forms', 'Forms', 'Lead capture, hosted or embedded on your own site.'],
  ['/landing-pages', 'Landing pages', 'The pages your ads and posts point at.'],
  ['/crm/companies', 'Companies', 'Accounts, their people and open deals.'],
  ['/crm', 'Pipeline', 'Deals from first conversation to won.'],
  ['/analytics', 'Analytics', 'Every period compared against the one before it.'],
  ['/integrations', 'Integrations', 'Lead sources, pixels, webhooks and API keys.'],
  ['/billing', 'Billing', 'Plan, usage against limits, payment and invoices.'],
  ['/settings', 'Settings', 'Sending identity, provider, domain auth and limits.'],
  ['/profile', 'Your profile', 'Personal details, password and sessions.'],
];

const usePageMeta = () => {
  const { pathname } = useLocation();
  const match = PAGE_TITLES.find(([prefix]) => pathname.startsWith(prefix));
  return { title: match?.[1] ?? 'Cadence', subtitle: match?.[2] ?? '' };
};

export const Header = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { title, subtitle } = usePageMeta();
  const { theme, setTheme } = useTheme();

  const iconBtn =
    'grid h-8 w-8 place-items-center rounded-md border bg-card text-muted-foreground transition-colors hover:text-foreground';

  return (
    <header className="flex flex-wrap items-center gap-2.5 px-0.5 pt-0.5">
      <div className="min-w-0">
        <h1 className="truncate text-[19px] font-bold tracking-tight">{title}</h1>
      </div>

      <div className="flex-1" />

      <label className="hidden min-w-[200px] items-center gap-2 rounded-md border bg-card px-3 py-1.5 text-[12.5px] text-subtle-foreground sm:flex">
        <Search className="h-3.5 w-3.5 flex-none" />
        <input
          id="global-search"
          type="search"
          placeholder="Search contacts, campaigns…"
          className="w-full bg-transparent outline-none placeholder:text-subtle-foreground"
        />
      </label>

      <button type="button" className="hidden items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-[12.5px] text-muted-foreground hover:text-foreground md:flex">
        <SlidersHorizontal className="h-3.5 w-3.5" /> Filter
      </button>

      <NotificationBell />

      <button
        type="button"
        onClick={() => setTheme('light')}
        aria-label="Light theme"
        aria-pressed={theme === 'light'}
        className={cn(iconBtn, theme === 'light' && 'border-transparent bg-brand-fill text-brand-ink')}
      >
        <Sun className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        onClick={() => setTheme('dark')}
        aria-label="Dark theme"
        aria-pressed={theme === 'dark'}
        className={cn(iconBtn, theme === 'dark' && 'border-transparent bg-brand-fill text-brand-ink')}
      >
        <Moon className="h-3.5 w-3.5" />
      </button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2 rounded-md border bg-card py-1 pl-1 pr-2.5 hover:bg-accent"
          >
            <span className="grid h-7 w-7 flex-none place-items-center rounded-full bg-brand-fill text-[11.5px] font-extrabold text-brand-ink">
              {user ? getInitials(user.first_name, user.last_name) : <User className="h-3.5 w-3.5" />}
            </span>
            <span className="hidden text-left md:block">
              <span className="block text-[12.5px] font-semibold leading-tight">
                {user ? `${user.first_name} ${user.last_name}` : 'User'}
              </span>
              <span className="block text-[10.5px] leading-tight text-subtle-foreground">
                {user?.email}
              </span>
            </span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>My Account</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate('/profile')}>Profile</DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate('/settings')}>Settings</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => logout()}>Log out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {subtitle && (
        <p className="order-last -mt-0.5 w-full text-[12.5px] text-muted-foreground">{subtitle}</p>
      )}
    </header>
  );
};
