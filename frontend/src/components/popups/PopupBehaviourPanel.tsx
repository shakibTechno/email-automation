import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  PopupDesign, PopupFrequency, PopupPosition, PopupTargeting, PopupTrigger,
  PopupTriggers, PopupType, popupTriggerLabels,
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

export const PopupBehaviourPanel = ({
  popupType, triggers, targeting, frequency, design,
  onTriggersChange, onTargetingChange, onFrequencyChange, onDesignChange,
}: Props) => {
  const setTrigger = (partial: Partial<PopupTriggers>) =>
    onTriggersChange({ ...triggers, ...partial });
  const setTargeting = (partial: Partial<PopupTargeting>) =>
    onTargetingChange({ ...targeting, ...partial });
  const setDesign = (partial: Partial<PopupDesign>) =>
    onDesignChange({ ...design, ...partial });

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
