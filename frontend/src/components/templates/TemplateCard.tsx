import { MoreVertical, Pencil, Copy, Trash2, Mail } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { EmailTemplate } from '@/types/template';

interface TemplateCardProps {
  template: EmailTemplate;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => void;
}

const categoryColors: Record<string, string> = {
  marketing: 'bg-info/[.14] text-info',
  transactional: 'bg-success/[.14] text-success',
  newsletter: 'bg-info/[.14] text-info',
  welcome: 'bg-warning/[.14] text-warning',
  notification: 'bg-warning/[.14] text-warning',
  custom: 'bg-secondary text-muted-foreground',
};

export const TemplateCard = ({
  template,
  onDuplicate,
  onDelete,
}: TemplateCardProps) => {
  const navigate = useNavigate();

  const formattedDate = new Date(template.updated_at).toLocaleDateString(
    'en-US',
    { month: 'short', day: 'numeric', year: 'numeric' }
  );

  return (
    <Card className="group overflow-hidden hover:shadow-md transition-shadow">
      {/* Thumbnail / Placeholder */}
      <div
        className="h-40 bg-secondary flex items-center justify-center cursor-pointer border-b"
        onClick={() => navigate(`/templates/${template.id}/edit`)}
      >
        {template.thumbnail_url ? (
          <img
            src={template.thumbnail_url}
            alt={template.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <Mail className="h-12 w-12 text-subtle-foreground" />
        )}
      </div>

      {/* Card Info */}
      <div className="p-4 space-y-2">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h3
              className="font-medium text-sm truncate cursor-pointer hover:text-primary"
              onClick={() => navigate(`/templates/${template.id}/edit`)}
            >
              {template.name}
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Updated {formattedDate}
            </p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => navigate(`/templates/${template.id}/edit`)}
              >
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDuplicate(template.id)}>
                <Copy className="h-4 w-4 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => onDelete(template.id)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Badge
          variant="secondary"
          className={categoryColors[template.category] || categoryColors.custom}
        >
          {template.category}
        </Badge>
      </div>
    </Card>
  );
};
