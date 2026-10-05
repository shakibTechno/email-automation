import { useState } from 'react';
import { ArrowLeft, Plus, Edit, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useTags } from '@/hooks/useTags';
import { CreateTagData, UpdateTagData } from '@/types/contact';

const COLOR_OPTIONS: { value: string; hex: string }[] = [
  { value: 'blue', hex: '#3B82F6' },
  { value: 'green', hex: '#10B981' },
  { value: 'yellow', hex: '#F59E0B' },
  { value: 'red', hex: '#EF4444' },
  { value: 'purple', hex: '#8B5CF6' },
  { value: 'pink', hex: '#EC4899' },
  { value: 'orange', hex: '#F97316' },
  { value: 'gray', hex: '#6B7280' },
];

const getColorHex = (colorName: string): string => {
  return COLOR_OPTIONS.find((c) => c.value === colorName)?.hex || colorName;
};

export const TagManagementPage = () => {
  const navigate = useNavigate();
  const { tags, createTag, updateTag, deleteTag, isCreating, isUpdating, isDeleting } = useTags();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [selectedTag, setSelectedTag] = useState<{ id: string; name: string; color: string } | null>(null);
  const [formData, setFormData] = useState({ name: '', color: COLOR_OPTIONS[0].value });

  const handleCreate = () => {
    if (formData.name.trim()) {
      createTag(formData as CreateTagData);
      setIsCreateOpen(false);
      setFormData({ name: '', color: COLOR_OPTIONS[0].value });
    }
  };

  const handleEdit = () => {
    if (selectedTag && formData.name.trim()) {
      updateTag(selectedTag.id, formData as UpdateTagData);
      setIsEditOpen(false);
      setSelectedTag(null);
      setFormData({ name: '', color: COLOR_OPTIONS[0].value });
    }
  };

  const handleDelete = () => {
    if (selectedTag) {
      deleteTag(selectedTag.id);
      setIsDeleteOpen(false);
      setSelectedTag(null);
    }
  };

  const openEditDialog = (tag: { id: string; name: string; color: string }) => {
    setSelectedTag(tag);
    setFormData({ name: tag.name, color: tag.color });
    setIsEditOpen(true);
  };

  const openDeleteDialog = (tag: { id: string; name: string; color: string }) => {
    setSelectedTag(tag);
    setIsDeleteOpen(true);
  };

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/contacts')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Tag Management</h1>
            <p className="text-muted-foreground">
              Create and manage tags for organizing contacts
            </p>
          </div>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Tag
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Tags</CardTitle>
        </CardHeader>
        <CardContent>
          {tags.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">
                No tags created yet. Create your first tag to get started.
              </p>
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Tag
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-secondary/50"
                >
                  <Badge
                    style={{ backgroundColor: getColorHex(tag.color) }}
                    className="text-white px-3 py-1"
                  >
                    {tag.name}
                  </Badge>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditDialog(tag)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openDeleteDialog(tag)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Tag</DialogTitle>
            <DialogDescription>
              Add a new tag to organize your contacts
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Tag Name</Label>
              <Input
                id="name"
                placeholder="Enter tag name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="flex flex-wrap gap-2">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`w-8 h-8 rounded-full border-2 ${
                      formData.color === opt.value ? 'border-foreground' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: opt.hex }}
                    onClick={() => setFormData({ ...formData, color: opt.value })}
                  />
                ))}
              </div>
              <Badge
                style={{ backgroundColor: getColorHex(formData.color) }}
                className="text-white mt-2"
              >
                {formData.name || 'Preview'}
              </Badge>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={isCreating || !formData.name.trim()}>
              {isCreating ? 'Creating...' : 'Create Tag'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Tag</DialogTitle>
            <DialogDescription>Update tag information</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Tag Name</Label>
              <Input
                id="edit-name"
                placeholder="Enter tag name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="flex flex-wrap gap-2">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`w-8 h-8 rounded-full border-2 ${
                      formData.color === opt.value ? 'border-foreground' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: opt.hex }}
                    onClick={() => setFormData({ ...formData, color: opt.value })}
                  />
                ))}
              </div>
              <Badge
                style={{ backgroundColor: getColorHex(formData.color) }}
                className="text-white mt-2"
              >
                {formData.name || 'Preview'}
              </Badge>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleEdit} disabled={isUpdating || !formData.name.trim()}>
              {isUpdating ? 'Updating...' : 'Update Tag'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Tag</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this tag? This will remove it from all contacts.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
