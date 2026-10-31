import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Monitor, Smartphone, Play, Pause } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { usePopup, usePopups } from '@/hooks/usePopups';
import { useForms } from '@/hooks/useForms';
import { PopupStatusBadge } from '@/components/popups/PopupStatusBadge';
import { PopupPreview } from '@/components/popups/PopupPreview';
import { PopupBehaviourPanel } from '@/components/popups/PopupBehaviourPanel';
import {
  defaultPopupDesign, defaultPopupFrequency, defaultPopupTargeting,
  defaultPopupTriggers, popupTypeLabels, PopupDesign, PopupFrequency,
  PopupTargeting, PopupTriggers, PopupType, UpdatePopupData,
} from '@/types/popup';

export const PopupBuilderPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { popup, isLoading } = usePopup(id || '');
  const { updatePopup, publishPopup, pausePopup, isUpdating } = usePopups();
  // Only this organization's forms, and only to pick one to embed.
  const { forms } = useForms({ page_size: 100 });

  const [name, setName] = useState('');
  const [popupType, setPopupType] = useState<PopupType>('modal');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [ctaText, setCtaText] = useState('');
  const [ctaUrl, setCtaUrl] = useState('');
  const [formId, setFormId] = useState<string>('');
  const [design, setDesign] = useState<PopupDesign>(defaultPopupDesign);
  const [triggers, setTriggers] = useState<PopupTriggers>(defaultPopupTriggers);
  const [targeting, setTargeting] = useState<PopupTargeting>(defaultPopupTargeting);
  const [frequency, setFrequency] = useState<PopupFrequency>(defaultPopupFrequency);
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [device, setDevice] = useState<'desktop' | 'mobile'>('desktop');

  useEffect(() => {
    if (!popup) return;
    setName(popup.name);
    setPopupType(popup.popup_type);
    setTitle(popup.title);
    setDescription(popup.description);
    setImageUrl(popup.image_url);
    setCtaText(popup.cta_text);
    setCtaUrl(popup.cta_url);
    // '' is not a usable Select value in Radix, so "no form" is a sentinel.
    setFormId(popup.form || '_none');
    setDesign({ ...defaultPopupDesign, ...popup.design });
    setTriggers({ ...defaultPopupTriggers, ...popup.triggers });
    setTargeting({ ...defaultPopupTargeting, ...popup.targeting });
    setFrequency({ ...defaultPopupFrequency, ...popup.frequency });
    setStartsAt(popup.starts_at ? popup.starts_at.slice(0, 16) : '');
    setEndsAt(popup.ends_at ? popup.ends_at.slice(0, 16) : '');
  }, [popup]);

  const payload = (): UpdatePopupData => ({
    name,
    popup_type: popupType,
    title,
    description,
    image_url: imageUrl,
    cta_text: ctaText,
    cta_url: ctaUrl,
    form: formId && formId !== '_none' ? formId : null,
    design,
    triggers,
    targeting,
    frequency,
    starts_at: startsAt ? new Date(startsAt).toISOString() : null,
    ends_at: endsAt ? new Date(endsAt).toISOString() : null,
  });

  const save = async () => {
    if (!id) return;
    await updatePopup(id, payload());
  };

  if (isLoading || !popup) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
      </div>
    );
  }

  const live = popup.status === 'published' || popup.status === 'scheduled';

  return (
    <div className="w-full space-y-3.5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/popups')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{name || 'Pop-up'}</h1>
            <div className="mt-0.5">
              <PopupStatusBadge status={popup.status} isLive={popup.is_live} />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={save} disabled={isUpdating}>
            {isUpdating ? 'Saving...' : 'Save'}
          </Button>
          {live ? (
            <Button size="sm" variant="secondary" onClick={() => pausePopup(popup.id)}>
              <Pause className="h-3.5 w-3.5" /> Pause
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={async () => { await save(); publishPopup(popup.id); }}
            >
              <Play className="h-3.5 w-3.5" /> Publish
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="space-y-3.5 lg:col-span-3">
          <Tabs defaultValue="content">
            <TabsList>
              <TabsTrigger value="content">Content</TabsTrigger>
              <TabsTrigger value="behaviour">Behaviour</TabsTrigger>
              <TabsTrigger value="schedule">Schedule</TabsTrigger>
            </TabsList>

            <TabsContent value="content" className="mt-3.5 space-y-3.5">
              <Card className="space-y-3 p-4">
                <div>
                  <Label>Name</Label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="mt-1"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    For your list only — visitors never see it.
                  </p>
                </div>
                <div>
                  <Label>Display as</Label>
                  <Select
                    value={popupType}
                    onValueChange={(v) => setPopupType(v as PopupType)}
                  >
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {(Object.keys(popupTypeLabels) as PopupType[]).map((key) => (
                        <SelectItem key={key} value={key}>
                          {popupTypeLabels[key]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </Card>

              <Card className="space-y-3 p-4">
                <h3 className="text-sm font-semibold">What it says</h3>
                <div>
                  <Label>Headline</Label>
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Get the good stuff"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Body</Label>
                  <Textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="One email a month. Unsubscribe whenever you like."
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Image URL</Label>
                  <Input
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    placeholder="https://..."
                    className="mt-1"
                  />
                </div>
              </Card>

              <Card className="space-y-3 p-4">
                <h3 className="text-sm font-semibold">What the visitor does</h3>
                <div>
                  <Label>Capture with a form</Label>
                  <Select value={formId} onValueChange={setFormId}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="No form" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_none">No form — just a button</SelectItem>
                      {forms.map((form) => (
                        <SelectItem key={form.id} value={form.id}>
                          {form.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="mt-1 text-xs text-muted-foreground">
                    With a form, submissions become contacts and fire your
                    workflows. Without one, the pop-up records clicks.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Button text</Label>
                    <Input
                      value={ctaText}
                      onChange={(e) => setCtaText(e.target.value)}
                      placeholder="Subscribe"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>Button links to</Label>
                    <Input
                      value={ctaUrl}
                      onChange={(e) => setCtaUrl(e.target.value)}
                      placeholder="https://..."
                      className="mt-1"
                      disabled={!!formId && formId !== '_none'}
                    />
                  </div>
                </div>
                {formId && formId !== '_none' && (
                  <p className="text-xs text-muted-foreground">
                    With a form, the button submits it rather than linking away.
                  </p>
                )}
              </Card>
            </TabsContent>

            <TabsContent value="behaviour" className="mt-3.5">
              <PopupBehaviourPanel
                popupType={popupType}
                triggers={triggers}
                targeting={targeting}
                frequency={frequency}
                design={design}
                onTriggersChange={setTriggers}
                onTargetingChange={setTargeting}
                onFrequencyChange={setFrequency}
                onDesignChange={setDesign}
              />
            </TabsContent>

            <TabsContent value="schedule" className="mt-3.5">
              <Card className="space-y-3 p-4">
                <h3 className="text-sm font-semibold">When it runs</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Starts</Label>
                    <Input
                      type="datetime-local"
                      value={startsAt}
                      onChange={(e) => setStartsAt(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>Ends</Label>
                    <Input
                      type="datetime-local"
                      value={endsAt}
                      onChange={(e) => setEndsAt(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Leave either empty to run without that bound. Publishing a
                  pop-up whose start is in the future schedules it instead.
                  Boundaries are accurate to within a few minutes, because the
                  website snippet is cached.
                </p>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="lg:col-span-2">
          <div className="sticky top-6 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Preview</span>
              <div className="flex gap-1">
                <Button
                  variant={device === 'desktop' ? 'secondary' : 'ghost'}
                  size="icon" className="h-7 w-7"
                  onClick={() => setDevice('desktop')}
                  aria-label="Desktop preview"
                >
                  <Monitor className="h-4 w-4" />
                </Button>
                <Button
                  variant={device === 'mobile' ? 'secondary' : 'ghost'}
                  size="icon" className="h-7 w-7"
                  onClick={() => setDevice('mobile')}
                  aria-label="Mobile preview"
                >
                  <Smartphone className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <PopupPreview
              device={device}
              popupType={popupType}
              title={title}
              description={description}
              imageUrl={imageUrl}
              ctaText={ctaText}
              hasForm={!!formId && formId !== '_none'}
              design={design}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
