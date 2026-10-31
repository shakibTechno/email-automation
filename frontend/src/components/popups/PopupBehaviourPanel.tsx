import { Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { useTags } from '@/hooks/useTags';
import { useSegments } from '@/hooks/useSegments';
import {
  PopupAudienceTargeting, PopupContactFieldRule, PopupDesign, PopupFrequency,
  PopupPosition, PopupTargeting, PopupTrigger, PopupTriggers, PopupType,
  popupTriggerLabels,
} from '@/types/popup';

interface Props {
  popupType: PopupType;
  triggers: PopupTriggers;
  targeting: PopupTargeting;
  frequency: PopupFrequency;
  design: PopupDesign;
  onTriggersChange: (value: PopupTriggers) => void;
  onTargetingChange: (value: PopupTargeting) => void;
  onFrequencyChange: (value: PopupFrequency) => void;
  onDesignChange: (value: PopupDesign) => void;
}

const toList = (value: string) =>
  value.split('\n').map((line) => line.trim()).filter(Boolean);

const toCodes = (value: string) =>
  value.split(',').map((part) => part.trim().toUpperCase()).filter(Boolean);

/** Fields a marketer plausibly segments a pop-up on, not all forty of them. */
const CONTACT_FIELDS = [
  { value: 'company', label: 'Company' },
  { value: 'job_title', label: 'Job title' },
  { value: 'city', label: 'City' },
  { value: 'country', label: 'Country (on the contact)' },
  { value: 'lifecycle_stage', label: 'Lifecycle stage' },
  { value: 'lead_source', label: 'Lead source' },
  { value: 'phone', label: 'Phone' },
];

const OPERATORS: { value: PopupContactFieldRule['operator']; label: string }[] = [
  { value: 'is_not_empty', label: 'is set' },
  { value: 'is_empty', label: 'is empty' },
  { value: 'equals', label: 'is' },
  { value: 'not_equals', label: 'is not' },
  { value: 'contains', label: 'contains' },
];

/** Needs no value box: the operator is the whole rule. */
const VALUELESS = ['is_not_empty', 'is_empty'];

const emptyAudience: PopupAudienceTargeting = {
  segments: [], tags: [], contactFields: [],
};


export const PopupBehaviourPanel = ({
  popupType, triggers, targeting, frequency, design,
  onTriggersChange, onTargetingChange, onFrequencyChange, onDesignChange,
}: Props) => {
  const { tags } = useTags();
  const { data: segmentData } = useSegments();
  const segments = segmentData?.results || [];

  const setTrigger = (partial: Partial<PopupTriggers>) =>
    onTriggersChange({ ...triggers, ...partial });
  const setTargeting = (partial: Partial<PopupTargeting>) =>
    onTargetingChange({ ...targeting, ...partial });
  const setDesign = (partial: Partial<PopupDesign>) =>
    onDesignChange({ ...design, ...partial });

  // Pop-ups saved before audience targeting existed have no audience key.
  const audience = targeting.audience || emptyAudience;
  const setAudience = (partial: Partial<PopupAudienceTargeting>) =>
    setTargeting({ audience: { ...audience, ...partial } });
  const setRule = (index: number, partial: Partial<PopupContactFieldRule>) =>
    setAudience({
      contactFields: audience.contactFields.map((rule, i) =>
        (i === index ? { ...rule, ...partial } : rule)),
    });

  return (
    <div className="space-y-3.5">
      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-semibold">When it appears</h3>
        <div>
          <Label>Trigger</Label>
          <Select
            value={triggers.type}
            onValueChange={(v) => setTrigger({ type: v as PopupTrigger })}
          >
            <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
            <SelectContent>
              {(Object.keys(popupTriggerLabels) as PopupTrigger[]).map((key) => (
                <SelectItem key={key} value={key}>{popupTriggerLabels[key]}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {triggers.type === 'time' && (
          <div>
            <Label>Delay (seconds)</Label>
            <Input
              type="number" min={0} className="mt-1"
              value={triggers.delaySeconds}
              onChange={(e) => setTrigger({ delaySeconds: Number(e.target.value) })}
            />
          </div>
        )}

        {triggers.type === 'scroll' && (
          <div>
            <Label>Show after scrolling (%)</Label>
            <Input
              type="number" min={1} max={100} className="mt-1"
              value={triggers.scrollPercent}
              onChange={(e) => setTrigger({ scrollPercent: Number(e.target.value) })}
            />
          </div>
        )}

        {triggers.type === 'page_visit' && (
          <div>
            <Label>Show on page number</Label>
            <Input
              type="number" min={1} className="mt-1"
              value={triggers.pageVisitCount}
              onChange={(e) => setTrigger({ pageVisitCount: Number(e.target.value) })}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Counted across this visit, so 2 means the second page they open.
            </p>
          </div>
        )}

        {triggers.type === 'inactivity' && (
          <div>
            <Label>Idle for (seconds)</Label>
            <Input
              type="number" min={5} className="mt-1"
              value={triggers.inactivitySeconds}
              onChange={(e) => setTrigger({ inactivitySeconds: Number(e.target.value) })}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              No pointer, key or scroll for that long.
            </p>
          </div>
        )}

        {triggers.type === 'click' && (
          <div>
            <Label>CSS selector</Label>
            <Input
              className="mt-1" placeholder="#newsletter-button"
              value={triggers.clickSelector}
              onChange={(e) => setTrigger({ clickSelector: e.target.value })}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              A click anywhere inside a matching element opens it.
            </p>
          </div>
        )}

        {triggers.type === 'exit_intent' && (
          <div>
            <Label>Mobile fallback delay (seconds)</Label>
            <Input
              type="number" min={0} className="mt-1"
              value={triggers.delaySeconds}
              onChange={(e) => setTrigger({ delaySeconds: Number(e.target.value) })}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Exit intent needs a mouse, so phones use this instead — otherwise
              mobile visitors would never see it.
            </p>
          </div>
        )}
      </Card>

      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-semibold">Who sees it</h3>

        <div>
          <Label>Only on these pages</Label>
          <Textarea
            rows={2} className="mt-1" placeholder={'/pricing\n/blog/*'}
            value={targeting.includeUrls.join('\n')}
            onChange={(e) => setTargeting({ includeUrls: toList(e.target.value) })}
          />
          <p className="mt-1 text-xs text-muted-foreground">
            One path per line, empty for every page. A trailing * matches
            anything below it.
          </p>
        </div>

        <div>
          <Label>Never on these pages</Label>
          <Textarea
            rows={2} className="mt-1" placeholder="/checkout/*"
            value={targeting.excludeUrls.join('\n')}
            onChange={(e) => setTargeting({ excludeUrls: toList(e.target.value) })}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Visitor</Label>
            <Select
              value={targeting.visitorType}
              onValueChange={(v) =>
                setTargeting({ visitorType: v as PopupTargeting['visitorType'] })
              }
            >
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Anyone</SelectItem>
                <SelectItem value="new">First-time visitors</SelectItem>
                <SelectItem value="returning">Returning visitors</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Came from</Label>
            <Input
              className="mt-1" placeholder="google.com"
              value={targeting.referrers.join(', ')}
              onChange={(e) =>
                setTargeting({
                  referrers: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
            />
          </div>
        </div>

        <div className="flex gap-4">
          {(['desktop', 'mobile'] as const).map((item) => (
            <div key={item} className="flex items-center space-x-2">
              <Checkbox
                id={`popup-device-${item}`}
                checked={targeting.devices.includes(item)}
                onCheckedChange={(checked) =>
                  setTargeting({
                    devices: checked
                      ? [...targeting.devices.filter((d) => d !== item), item]
                      : targeting.devices.filter((d) => d !== item),
                  })
                }
              />
              <Label htmlFor={`popup-device-${item}`} className="capitalize">{item}</Label>
            </div>
          ))}
        </div>

        <div>
          <Label>Countries</Label>
          <Input
            className="mt-1" placeholder="IE, GB, US"
            value={(targeting.country || []).join(', ')}
            onChange={(e) => setTargeting({ country: toCodes(e.target.value) })}
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Two-letter codes, empty for everywhere. A visitor whose country we
            cannot work out does <strong>not</strong> see it &mdash; an
            Ireland-only offer shown to the whole world is the worse mistake.
          </p>
        </div>
      </Card>

      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-semibold">Only people you already know</h3>
        <p className="text-xs text-muted-foreground">
          These match the contact behind the visit, so they only show to
          someone who has already submitted a form on your site. Leave them
          empty to reach everybody.
        </p>

        <div>
          <Label>In these segments</Label>
          <div className="mt-1 max-h-32 space-y-1.5 overflow-y-auto rounded-md border p-2">
            {segments.length === 0 && (
              <p className="text-xs text-muted-foreground">No segments yet.</p>
            )}
            {segments.map((segment) => (
              <div key={segment.id} className="flex items-center space-x-2">
                <Checkbox
                  id={`popup-segment-${segment.id}`}
                  checked={audience.segments.includes(segment.id)}
                  onCheckedChange={(checked) =>
                    setAudience({
                      segments: checked
                        ? [...audience.segments, segment.id]
                        : audience.segments.filter((s) => s !== segment.id),
                    })
                  }
                />
                <Label htmlFor={`popup-segment-${segment.id}`} className="font-normal">
                  {segment.name}
                </Label>
              </div>
            ))}
          </div>
        </div>

        <div>
          <Label>With all of these tags</Label>
          <div className="mt-1 max-h-32 space-y-1.5 overflow-y-auto rounded-md border p-2">
            {tags.length === 0 && (
              <p className="text-xs text-muted-foreground">No tags yet.</p>
            )}
            {tags.map((tag) => (
              <div key={tag.id} className="flex items-center space-x-2">
                <Checkbox
                  id={`popup-tag-${tag.id}`}
                  checked={audience.tags.includes(tag.id)}
                  onCheckedChange={(checked) =>
                    setAudience({
                      tags: checked
                        ? [...audience.tags, tag.id]
                        : audience.tags.filter((t) => t !== tag.id),
                    })
                  }
                />
                <Label htmlFor={`popup-tag-${tag.id}`} className="font-normal">
                  {tag.name}
                </Label>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <Label>Contact properties</Label>
          {audience.contactFields.map((rule, index) => (
            <div key={index} className="flex gap-2">
              <Select
                value={rule.field}
                onValueChange={(v) => setRule(index, { field: v })}
              >
                <SelectTrigger className="flex-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CONTACT_FIELDS.map((field) => (
                    <SelectItem key={field.value} value={field.value}>
                      {field.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={rule.operator}
                onValueChange={(v) =>
                  setRule(index, { operator: v as PopupContactFieldRule['operator'] })
                }
              >
                <SelectTrigger className="w-[120px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {OPERATORS.map((op) => (
                    <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!VALUELESS.includes(rule.operator) && (
                <Input
                  className="w-[130px]" placeholder="Value"
                  value={rule.value}
                  onChange={(e) => setRule(index, { value: e.target.value })}
                />
              )}
              <Button
                type="button" variant="ghost" size="icon"
                onClick={() =>
                  setAudience({
                    contactFields: audience.contactFields.filter((_, i) => i !== index),
                  })
                }
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button
            type="button" variant="outline" size="sm"
            onClick={() =>
              setAudience({
                contactFields: [
                  ...audience.contactFields,
                  { field: 'company', operator: 'is_not_empty', value: '' },
                ],
              })
            }
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add a property rule
          </Button>
        </div>
      </Card>

      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-semibold">How often</h3>
        <Select
          value={frequency.mode}
          onValueChange={(v) =>
            onFrequencyChange({ ...frequency, mode: v as PopupFrequency['mode'] })
          }
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="once_per_visitor">Once per visitor</SelectItem>
            <SelectItem value="once_per_session">Once per session</SelectItem>
            <SelectItem value="every_n_days">Every few days</SelectItem>
            <SelectItem value="every_visit">Every visit</SelectItem>
          </SelectContent>
        </Select>
        {frequency.mode === 'every_n_days' && (
          <div>
            <Label>Days between</Label>
            <Input
              type="number" min={1} className="mt-1"
              value={frequency.days}
              onChange={(e) =>
                onFrequencyChange({ ...frequency, days: Number(e.target.value) })
              }
            />
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          Remembered in the visitor&rsquo;s own browser, so clearing site data
          resets it.
        </p>
      </Card>

      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-semibold">Appearance</h3>
        {popupType !== 'floating_bar' && popupType !== 'full_screen' && (
          <div>
            <Label>Position</Label>
            <Select
              value={design.position}
              onValueChange={(v) => setDesign({ position: v as PopupPosition })}
            >
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="center">Centre of the screen</SelectItem>
                <SelectItem value="bottom_right">Bottom right</SelectItem>
                <SelectItem value="bottom_left">Bottom left</SelectItem>
                <SelectItem value="top">Top</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Width</Label>
            <Input
              className="mt-1" value={design.maxWidth}
              onChange={(e) => setDesign({ maxWidth: e.target.value })}
            />
          </div>
          <div>
            <Label>Corner radius</Label>
            <Input
              className="mt-1" value={design.borderRadius}
              onChange={(e) => setDesign({ borderRadius: e.target.value })}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Background</Label>
            <Input
              type="color" className="mt-1 h-9"
              value={design.backgroundColor}
              onChange={(e) => setDesign({ backgroundColor: e.target.value })}
            />
          </div>
          <div>
            <Label>Button</Label>
            <Input
              type="color" className="mt-1 h-9"
              value={design.primaryButton.backgroundColor}
              onChange={(e) =>
                setDesign({
                  primaryButton: {
                    ...design.primaryButton,
                    backgroundColor: e.target.value,
                  },
                })
              }
            />
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="popup-backdrop"
            checked={design.backdrop}
            onCheckedChange={(checked) => setDesign({ backdrop: !!checked })}
          />
          <Label htmlFor="popup-backdrop">Dim the page behind it</Label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="popup-close"
            checked={design.closeButton.show}
            onCheckedChange={(checked) =>
              setDesign({
                closeButton: { ...design.closeButton, show: !!checked },
              })
            }
          />
          <Label htmlFor="popup-close">Show a close button</Label>
        </div>
        {!design.closeButton.show && (
          <p className="text-xs text-destructive">
            A pop-up that cannot be dismissed is the fastest way to have your
            site reported. Pressing Escape still closes it.
          </p>
        )}
      </Card>
    </div>
  );
};
