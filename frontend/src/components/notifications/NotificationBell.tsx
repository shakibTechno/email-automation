import { useNavigate } from 'react-router-dom';
import {
  Bell,
  CheckCheck,
  Mail,
  FlaskConical,
  AlertTriangle,
  CreditCard,
  UserPlus,
  FileText,
  Zap,
  Trophy,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useNotifications } from '@/hooks/useNotifications';
import { Notification, NotificationType } from '@/types/notification';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

const TYPE_CONFIG: Record<
  NotificationType,
  { icon: React.ElementType; color: string; path?: (data: Record<string, string>) => string }
> = {
  campaign_sent:                { icon: Mail,          color: 'text-success',  path: (d) => d.campaign_id ? `/campaigns/${d.campaign_id}` : '/campaigns' },
  campaign_failed:              { icon: AlertTriangle,  color: 'text-destructive',    path: (d) => d.campaign_id ? `/campaigns/${d.campaign_id}` : '/campaigns' },
  ab_test_winner_needed:        { icon: Trophy,         color: 'text-warning',  path: (d) => d.campaign_id ? `/campaigns/${d.campaign_id}` : '/campaigns' },
  ab_test_completed:            { icon: FlaskConical,   color: 'text-brand',   path: (d) => d.campaign_id ? `/campaigns/${d.campaign_id}` : '/campaigns' },
  form_submission:              { icon: FileText,       color: 'text-info', path: (d) => d.form_id ? `/forms/${d.form_id}` : '/forms' },
  workflow_failed:              { icon: Zap,            color: 'text-destructive',    path: (d) => d.workflow_id ? `/workflows/${d.workflow_id}` : '/workflows' },
  billing_trial_expiring:       { icon: Clock,          color: 'text-warning',  path: () => '/settings?tab=billing' },
  billing_payment_failed:       { icon: CreditCard,     color: 'text-destructive',    path: () => '/settings?tab=billing' },
  billing_subscription_renewed: { icon: CreditCard,     color: 'text-success',  path: () => '/settings?tab=billing' },
  team_member_joined:           { icon: UserPlus,       color: 'text-brand',   path: () => '/settings?tab=team' },
  lead_score_threshold:         { icon: Zap,            color: 'text-warning', path: () => '/contacts' },
};

interface NotificationItemProps {
  notification: Notification;
  onRead: (id: string) => void;
  onNavigate: (path: string) => void;
}

const NotificationItem = ({ notification, onRead, onNavigate }: NotificationItemProps) => {
  const config = TYPE_CONFIG[notification.notification_type] ?? { icon: Bell, color: 'text-muted-foreground' };
  const Icon = config.icon;
  const path = config.path?.(notification.data);

  const handleClick = () => {
    if (!notification.is_read) onRead(notification.id);
    if (path) onNavigate(path);
  };

  return (
    <div
      onClick={handleClick}
      className={cn(
        'flex gap-3 px-4 py-3 cursor-pointer hover:bg-muted/50 transition-colors',
        !notification.is_read && 'bg-primary/5'
      )}
    >
      <div className={cn('mt-0.5 shrink-0', config.color)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className={cn('text-sm leading-snug', !notification.is_read && 'font-semibold')}>
            {notification.title}
          </p>
          {!notification.is_read && (
            <span className="mt-1.5 shrink-0 h-2 w-2 rounded-full bg-primary" />
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
          {notification.message}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
        </p>
      </div>
    </div>
  );
};

export const NotificationBell = () => {
  const navigate = useNavigate();
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();

  const handleNavigate = (path: string) => {
    navigate(path);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-white leading-none">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-80 p-0 shadow-lg" sideOffset={8}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h3 className="font-semibold text-sm">Notifications</h3>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground hover:text-foreground"
              onClick={(e) => { e.stopPropagation(); markAllRead(); }}
            >
              <CheckCheck className="h-3.5 w-3.5 mr-1" />
              Mark all read
            </Button>
          )}
        </div>

        {/* List */}
        <div className="max-h-[420px] overflow-y-auto divide-y">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
              <Bell className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-sm">No notifications yet</p>
            </div>
          ) : (
            notifications.map((n) => (
              <NotificationItem
                key={n.id}
                notification={n}
                onRead={markRead}
                onNavigate={handleNavigate}
              />
            ))
          )}
        </div>

        {/* Footer */}
        {notifications.length > 0 && (
          <div className="border-t px-4 py-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-xs text-muted-foreground"
              onClick={() => handleNavigate('/notifications')}
            >
              View all notifications
            </Button>
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
