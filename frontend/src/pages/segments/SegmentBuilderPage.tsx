import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, Users, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { RuleBuilder } from '@/components/segments/RuleBuilder';
import {
  useSegment,
  useCreateSegment,
  useUpdateSegment,
  useFieldDefinitions,
  useTagOptions,
  usePreviewRules,
} from '@/hooks/useSegments';
import type { SegmentType, SegmentRules, CreateSegmentRequest, UpdateSegmentRequest } from '@/types/segment';
import { v4 as uuidv4 } from 'uuid';

const defaultRules: SegmentRules = {
  match_type: 'all',
  conditions: [],
  groups: [],
};

export default function SegmentBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id && id !== 'new';

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [segmentType, setSegmentType] = useState<SegmentType>('dynamic');
  const [rules, setRules] = useState<SegmentRules>(defaultRules);
  const [showPreview, setShowPreview] = useState(false);

  // Queries
  const { data: segment, isLoading: segmentLoading } = useSegment(isEditing ? id : '');
  const { data: fields = [] } = useFieldDefinitions();
  const { data: tags = [] } = useTagOptions();

  // Mutations
  const createSegment = useCreateSegment();
  const updateSegment = useUpdateSegment();
  const previewRules = usePreviewRules();

  // Load existing segment data
  useEffect(() => {
    if (segment) {
      setName(segment.name);
      setDescription(segment.description || '');
      setSegmentType(segment.segment_type);
      if (segment.rules && Object.keys(segment.rules).length > 0) {
        setRules(segment.rules);
      }
    }
  }, [segment]);

  // Initialize with one condition if creating new dynamic segment
  useEffect(() => {
    if (!isEditing && segmentType === 'dynamic' && rules.conditions.length === 0 && fields.length > 0) {
      const defaultField = fields[0];
      const defaultOperator = defaultField?.operators[0]?.value || 'equals';
      setRules({
        match_type: 'all',
        conditions: [
          {
            id: uuidv4(),
            field: defaultField?.field || 'email',
            operator: defaultOperator,
            value: null,
          },
        ],
        groups: [],
      });
    }
  }, [isEditing, segmentType, fields, rules.conditions.length]);

  const handlePreview = () => {
    if (segmentType === 'dynamic' && rules.conditions.length > 0) {
      previewRules.mutate({ rules, limit: 50 });
      setShowPreview(true);
    }
  };

  const handleSave = () => {
    if (isEditing) {
      const data: UpdateSegmentRequest = {
        name,
        description,
      };
      if (segmentType === 'dynamic') {
        data.rules = rules;
      }
      updateSegment.mutate(
        { id, data },
        {
          onSuccess: () => navigate(`/segments/${id}`),
        }
      );
    } else {
      const data: CreateSegmentRequest = {
        name,
        description,
        segment_type: segmentType,
      };
      if (segmentType === 'dynamic') {
        data.rules = rules;
      }
      createSegment.mutate(data, {
        onSuccess: (created) => navigate(`/segments/${created.id}`),
      });
    }
  };

  const isSaving = createSegment.isPending || updateSegment.isPending;
  const canSave = name.trim() && (segmentType === 'static' || rules.conditions.length > 0);

  if (segmentLoading && isEditing) {
    return (
      <div className="w-full">
        <div className="text-center py-12">Loading segment...</div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/segments')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">
            {isEditing ? 'Edit Segment' : 'Create Segment'}
          </h1>
          <p className="text-muted-foreground">
            {isEditing
              ? 'Update your segment configuration'
              : 'Define criteria to group your contacts'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {segmentType === 'dynamic' && rules.conditions.length > 0 && (
            <Button variant="outline" onClick={handlePreview}>
              <Eye className="mr-2 h-4 w-4" />
              Preview
            </Button>
          )}
          <Button onClick={handleSave} disabled={!canSave || isSaving}>
            <Save className="mr-2 h-4 w-4" />
            {isSaving ? 'Saving...' : 'Save Segment'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Name and describe your segment</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Segment Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Active Subscribers"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what this segment is for..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>
              {!isEditing && (
                <div className="space-y-2">
                  <Label htmlFor="type">Segment Type</Label>
                  <Select
                    value={segmentType}
                    onValueChange={(v) => setSegmentType(v as SegmentType)}
                  >
                    {/* Radix renders the selected item's children in the
                        trigger. These items carry a two-line description, so
                        the trigger was showing the label and the explanation
                        squashed onto one clamped line, sitting at a different
                        height and offset from every other control. Giving
                        SelectValue its own child keeps the descriptions in the
                        dropdown and the trigger to a single aligned line.
                        `id` also makes the Label's htmlFor actually resolve. */}
                    <SelectTrigger id="type">
                      <SelectValue>
                        {segmentType === 'dynamic' ? 'Dynamic' : 'Static'}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dynamic">
                        <div>
                          <div className="font-medium">Dynamic</div>
                          <div className="text-xs text-muted-foreground">
                            Contacts matching rules are automatically included
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="static">
                        <div>
                          <div className="font-medium">Static</div>
                          <div className="text-xs text-muted-foreground">
                            Manually add/remove contacts from the segment
                          </div>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Rules (Dynamic segments only) */}
          {segmentType === 'dynamic' && (
            <Card>
              <CardHeader>
                <CardTitle>Segment Rules</CardTitle>
                <CardDescription>
                  Define conditions to automatically include contacts
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RuleBuilder
                  rules={rules}
                  fields={fields}
                  tags={tags}
                  onChange={setRules}
                />
              </CardContent>
            </Card>
          )}

          {/* Static segment info */}
          {segmentType === 'static' && (
            <Card>
              <CardHeader>
                <CardTitle>Static Segment</CardTitle>
                <CardDescription>
                  After creating, you can manually add contacts to this segment
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                  <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>
                    Create the segment first, then add contacts from the segment detail page.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Preview Stats */}
          {segmentType === 'dynamic' && previewRules.data && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Preview Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {previewRules.data.total_count.toLocaleString()}
                </div>
                <p className="text-sm text-muted-foreground">contacts match these rules</p>
              </CardContent>
            </Card>
          )}

          {/* Tips */}
          <Card>
            <CardHeader>
              <CardTitle>Tips</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-3">
              <p>
                <strong>Dynamic segments</strong> automatically update when contacts match
                or no longer match your rules.
              </p>
              <p>
                <strong>Static segments</strong> give you full control - contacts only
                change when you manually add or remove them.
              </p>
              <p>
                Use <strong>AND (All)</strong> to require all conditions to match.
                Use <strong>OR (Any)</strong> when any condition is sufficient.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Preview Matching Contacts</DialogTitle>
            <DialogDescription>
              {previewRules.data?.total_count.toLocaleString()} contacts match your rules
              {previewRules.data?.has_more && ' (showing first 50)'}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-96 overflow-y-auto">
            {previewRules.isPending ? (
              <div className="text-center py-8">Loading preview...</div>
            ) : previewRules.data?.sample_contacts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No contacts match these rules
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2 px-2">Email</th>
                    <th className="text-left py-2 px-2">Name</th>
                  </tr>
                </thead>
                <tbody>
                  {previewRules.data?.sample_contacts.map((contact) => (
                    <tr key={contact.id} className="border-b">
                      <td className="py-2 px-2">{contact.email}</td>
                      <td className="py-2 px-2">
                        {contact.first_name || contact.last_name
                          ? `${contact.first_name || ''} ${contact.last_name || ''}`.trim()
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
