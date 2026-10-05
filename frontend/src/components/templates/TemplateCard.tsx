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
  marketing: 'bg-blue-100 text-blue-800',
  transactional: 'bg-green-100 text-green-800',
  newsletter: 'bg-purple-100 text-purple-800',
  welcome: 'bg-yellow-100 text-yellow-800',
  notification: 'bg-orange-100 text-orange-800',
  custom: 'bg-gray-100 text-gray-800',
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
        className="h-40 bg-gray-100 flex items-center justify-center cursor-pointer border-b"
        onClick={() => navigate(`/templates/${template.id}/edit`)}
      >
        {template.thumbnail_url ? (
          <img
            src={template.thumbnail_url}
            alt={template.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <Mail className="h-12 w-12 text-gray-300" />
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
