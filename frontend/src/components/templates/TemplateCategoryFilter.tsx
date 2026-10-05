import { cn } from '@/lib/utils';
import { TemplateCategory } from '@/types/template';

const categories: { value: TemplateCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'welcome', label: 'Welcome' },
  { value: 'transactional', label: 'Transactional' },
  { value: 'notification', label: 'Notification' },
  { value: 'custom', label: 'Custom' },
];

interface TemplateCategoryFilterProps {
  value: TemplateCategory | 'all';
  onChange: (value: TemplateCategory | 'all') => void;
}

export const TemplateCategoryFilter = ({
  value,
  onChange,
}: TemplateCategoryFilterProps) => {
  return (
    <div className="flex gap-2 flex-wrap">
      {categories.map((cat) => (
        <button
          key={cat.value}
          onClick={() => onChange(cat.value)}
          className={cn(
            'px-3 py-1.5 text-sm font-medium rounded-full border transition-colors',
            value === cat.value
              ? 'bg-primary text-primary-foreground border-primary'
              : 'bg-background text-muted-foreground border-border hover:bg-accent hover:text-accent-foreground'
          )}
        >
          {cat.label}
        </button>
      ))}
    </div>
  );
};
