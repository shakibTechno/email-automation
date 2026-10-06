import { useNavigate } from 'react-router-dom';
import {
  MoreVertical,
  Edit,
  Trash2,
  Eye,
  Mail,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { Contact } from '@/types/contact';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { formatDate, getEngagementLevel, getSubscriptionStatusColor } from '@/lib/utils';
import { TagChip } from '@/components/contacts/TagChip';

interface ContactTableProps {
  contacts: Contact[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onDelete: (id: string) => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (field: string) => void;
}

export const ContactTable = ({
  contacts,
  selectedIds,
  onSelectionChange,
  onDelete,
  sortBy,
  sortOrder,
  onSort,
}: ContactTableProps) => {
  const navigate = useNavigate();

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(contacts.map((c) => c.id));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedIds, id]);
    } else {
      onSelectionChange(selectedIds.filter((selectedId) => selectedId !== id));
    }
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return null;
    return sortOrder === 'asc' ? (
      <ChevronUp className="h-4 w-4" />
    ) : (
      <ChevronDown className="h-4 w-4" />
    );
  };

  return (
    <div className="border rounded-lg overflow-hidden bg-card">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-secondary/50 border-b">
            <tr>
              <th className="w-12 px-4 py-3">
                <Checkbox
                  checked={selectedIds.length === contacts.length && contacts.length > 0}
                  onCheckedChange={handleSelectAll}
                />
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-secondary"
                onClick={() => onSort?.('email')}
              >
                <div className="flex items-center gap-1">
                  Email
                  <SortIcon field="email" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-secondary"
                onClick={() => onSort?.('first_name')}
              >
                <div className="flex items-center gap-1">
                  Name
                  <SortIcon field="first_name" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Company
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-secondary"
                onClick={() => onSort?.('is_subscribed')}
              >
                <div className="flex items-center gap-1">
                  Status
                  <SortIcon field="is_subscribed" />
                </div>
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-secondary"
                onClick={() => onSort?.('lead_score')}
              >
                <div className="flex items-center gap-1">
                  Engagement
                  <SortIcon field="lead_score" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Assigned To
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Tags
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-secondary"
                onClick={() => onSort?.('created_at')}
              >
                <div className="flex items-center gap-1">
                  Created
                  <SortIcon field="created_at" />
                </div>
              </th>
              <th className="w-12 px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {contacts.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-muted-foreground">
                  No contacts found
                </td>
              </tr>
            ) : (
              contacts.map((contact) => {
                const engagement = getEngagementLevel(contact.lead_score);
                const tags = contact.tags || [];
                return (
                  <tr
                    key={contact.id}
                    className="hover:bg-secondary/50 cursor-pointer"
                    onClick={() => navigate(`/contacts/${contact.id}`)}
                  >
                    <td
                      className="px-4 py-3"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Checkbox
                        checked={selectedIds.includes(contact.id)}
                        onCheckedChange={(checked) =>
                          handleSelectOne(contact.id, checked as boolean)
                        }
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-subtle-foreground" />
                        <span className="text-sm font-medium">{contact.email}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {contact.first_name || contact.last_name
                        ? `${contact.first_name || ''} ${contact.last_name || ''}`.trim()
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {contact.company || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant="outline"
                        className={getSubscriptionStatusColor(contact.is_subscribed ? 'active' : 'unsubscribed')}
                      >
                        {contact.is_subscribed ? 'Subscribed' : 'Unsubscribed'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline" className={engagement.color}>
                        {engagement.label} ({contact.lead_score})
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {contact.assigned_to_name ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {tags.slice(0, 2).map((tag) => (
                          <TagChip key={tag.id} tag={tag} size="sm" />
                        ))}
                        {tags.length > 2 && (
                          <Badge variant="outline" className="text-xs">
                            +{tags.length - 2}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatDate(contact.created_at)}
                    </td>
                    <td
                      className="px-4 py-3"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => navigate(`/contacts/${contact.id}`)}
                          >
                            <Eye className="mr-2 h-4 w-4" />
                            View
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => navigate(`/contacts/${contact.id}/edit`)}
                          >
                            <Edit className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => onDelete(contact.id)}
                            className="text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
