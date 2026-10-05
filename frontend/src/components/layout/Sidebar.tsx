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
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Contacts', href: '/contacts', icon: Users },
  { name: 'Tags', href: '/contacts/tags', icon: Tags },
  { name: 'Segments', href: '/segments', icon: Filter },
  { name: 'Templates', href: '/templates', icon: LayoutTemplate },
  { name: 'Campaigns', href: '/campaigns', icon: Mail },
  { name: 'Sequences', href: '/sequences', icon: ListOrdered },
  { name: 'CRM', href: '/crm', icon: HeartHandshake },
  { name: 'Companies', href: '/crm/companies', icon: Building2 },
  { name: 'Workflows', href: '/workflows', icon: Zap },
  { name: 'Forms', href: '/forms', icon: FileText },
  { name: 'Landing Pages', href: '/landing-pages', icon: Layout },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Billing', href: '/billing', icon: CreditCard },
  { name: 'Integrations', href: '/integrations', icon: Puzzle },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export const Sidebar = () => {
  const location = useLocation();

  return (
    <div className="flex h-full w-64 flex-col bg-gray-900 text-white">
      <div className="flex h-16 items-center justify-center border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
            <span className="text-lg font-bold">E</span>
          </div>
          <span className="text-lg font-semibold">Email Marketing</span>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href ||
                          location.pathname.startsWith(item.href + '/');
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon
                className={cn(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'
                )}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </div>
  );
};
