import {
  Sun,
  Moon,
  User,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
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
import logoUrl from '@/assets/logo.png';

interface HeaderProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onToggleDrawer: () => void;
}

export const Header = ({ collapsed, onToggleCollapsed, onToggleDrawer }: HeaderProps) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();

  const iconBtn =
    'grid h-8 w-8 flex-none place-items-center rounded-md border bg-card text-muted-foreground transition-colors hover:text-foreground';

  return (
    <header className="fixed inset-x-0 top-0 z-50 flex h-14 items-center gap-2.5 border-b bg-sidebar px-3">
      {/* brand — sits over the rail, so it survives a collapse */}
      <Link
        to="/dashboard"
        className={cn(
          'flex flex-none items-center justify-center transition-[width] duration-200',
          collapsed ? 'lg:w-[52px]' : 'lg:w-[222px] lg:justify-start'
        )}
        aria-label="MailFlow home"
      >
        <img
          src={logoUrl}
          alt="MailFlow"
          width={32}
          height={32}
          className="h-8 w-8 flex-none object-contain"
        />
      </Link>

      {/* rail controls: collapse on desktop, drawer below lg */}
      <button
        type="button"
        onClick={onToggleCollapsed}
        className={cn(iconBtn, 'hidden lg:grid')}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-pressed={collapsed}
      >
        {collapsed ? <PanelLeftOpen className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
      </button>
      <button
        type="button"
        onClick={onToggleDrawer}
        className={cn(iconBtn, 'lg:hidden')}
        aria-label="Open navigation"
      >
        <Menu className="h-3.5 w-3.5" />
      </button>

      {/* Pushes the account controls right. The global search box and Filter
          button that used to sit here were removed: neither was wired to
          anything — no state, no handler, no form — so they invited people to
          type a query that went nowhere. Each list screen has its own working
          search and filters. */}
      <div className="flex-1" />

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
            className="flex flex-none items-center gap-2 rounded-md border bg-card py-1 pl-1 pr-1 hover:bg-accent sm:pr-2.5"
          >
            <span className="grid h-7 w-7 flex-none place-items-center rounded-full bg-brand-fill text-[11.5px] font-extrabold text-brand-ink">
              {user ? getInitials(user.first_name, user.last_name) : <User className="h-3.5 w-3.5" />}
            </span>
            <span className="hidden text-left lg:block">
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
    </header>
  );
};
