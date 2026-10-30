import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FormDisplayRules, FormType, defaultFormDisplayRules } from '@/types/form';

interface Props {
  formType: FormType;
  rules: FormDisplayRules;
  onChange: (rules: FormDisplayRules) => void;
}

/**
 * When and where a popup shows.
 *
 * Controlled and merged over the defaults locally, the same shape as
 * FormDesignPanel, so a form saved before a key existed still renders.
 */
export const PopupRulesPanel = ({ formType, rules, onChange }: Props) => {
  const r = { ...defaultFormDisplayRules, ...rules };
  const update = (partial: Partial<FormDisplayRules>) => onChange({ ...r, ...partial });
  const updateOverlay = (partial: Partial<FormDisplayRules['overlay']>) =>
    update({ overlay: { ...r.overlay, ...partial } });

  const toList = (value: string) =>
    value.split('\n').map((line) => line.trim()).filter(Boolean);

  return (
    <div className="space-y-4">
      <Card className="p-4 space-y-3">
        <h3 className="font-semibold text-sm">When it appears</h3>

        <div>
          <Label>Trigger</Label>
          <Select
            value={r.trigger}
            onValueChange={(v) => update({ trigger: v as FormDisplayRules['trigger'] })}
          >
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="time">After a delay</SelectItem>
              <SelectItem value="scroll">After scrolling</SelectItem>
              <SelectItem value="exit_intent">On exit intent</SelectItem>
              <SelectItem value="click">When an element is clicked</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {r.trigger === 'time' && (
          <div>
            <Label>Delay (seconds)</Label>
            <Input
              type="number"
              min={0}
              value={r.delaySeconds}
              onChange={(e) => update({ delaySeconds: Number(e.target.value) })}
              className="mt-1"
            />
          </div>
        )}

        {r.trigger === 'scroll' && (
          <div>
            <Label>Show after scrolling (%)</Label>
            <Input
              type="number"
              min={1}
              max={100}
              value={r.scrollPercent}
              onChange={(e) => update({ scrollPercent: Number(e.target.value) })}
              className="mt-1"
            />
          </div>
        )}

        {r.trigger === 'click' && (
          <div>
            <Label>CSS selector</Label>
            <Input
              value={r.clickSelector}
              onChange={(e) => update({ clickSelector: e.target.value })}
              placeholder="#newsletter-button"
              className="mt-1"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Any click inside a matching element opens the form.
            </p>
          </div>
        )}

        {r.trigger === 'exit_intent' && (
          <p className="text-xs text-muted-foreground">
            Exit intent needs a mouse, so phones and tablets fall back to the
            delay below &mdash; otherwise mobile visitors would never see it.
          </p>
        )}

        {r.trigger === 'exit_intent' && (
          <div>
            <Label>Mobile fallback delay (seconds)</Label>
            <Input
              type="number"
              min={0}
              value={r.delaySeconds}
              onChange={(e) => update({ delaySeconds: Number(e.target.value) })}
              className="mt-1"
            />
          </div>
        )}
      </Card>

      <Card className="p-4 space-y-3">
        <h3 className="font-semibold text-sm">How often</h3>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="popup-show-once"
            checked={r.showOnce}
            onCheckedChange={(v) => update({ showOnce: !!v })}
          />
          <Label htmlFor="popup-show-once">Only once per visitor</Label>
        </div>
        {!r.showOnce && (
          <div>
            <Label>Days before showing again</Label>
            <Input
              type="number"
              min={0}
              value={r.cooldownDays}
              onChange={(e) => update({ cooldownDays: Number(e.target.value) })}
              className="mt-1"
            />
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          Remembered in the visitor&rsquo;s own browser, so clearing site data
          resets it.
        </p>
      </Card>

      <Card className="p-4 space-y-3">
        <h3 className="font-semibold text-sm">Where</h3>

        {formType !== 'top_bar' && (
          <div>
            <Label>Position</Label>
            <Select
              value={r.position}
              onValueChange={(v) => update({ position: v as FormDisplayRules['position'] })}
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="center">Centre of the screen</SelectItem>
                <SelectItem value="bottom_right">Bottom right</SelectItem>
                <SelectItem value="bottom_left">Bottom left</SelectItem>
                <SelectItem value="top">Top</SelectItem>
              </SelectContent>
            </Select>
            <p className="mt-1 text-xs text-muted-foreground">
              On phones it is always a bottom sheet &mdash; a centred box sits
              behind the keyboard.
            </p>
          </div>
        )}

        <div>
          <Label>Only on these pages</Label>
          <Textarea
            rows={2}
            value={r.includeUrls.join('\n')}
            onChange={(e) => update({ includeUrls: toList(e.target.value) })}
            placeholder={'/pricing\n/blog/*'}
            className="mt-1"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            One path per line, empty for every page. A trailing * matches
            anything below it.
          </p>
        </div>

        <div>
          <Label>Never on these pages</Label>
          <Textarea
            rows={2}
            value={r.excludeUrls.join('\n')}
            onChange={(e) => update({ excludeUrls: toList(e.target.value) })}
            placeholder="/checkout/*"
            className="mt-1"
          />
        </div>

        <div className="flex gap-4">
          {(['desktop', 'mobile'] as const).map((device) => (
            <div key={device} className="flex items-center space-x-2">
              <Checkbox
                id={`popup-device-${device}`}
                checked={r.devices.includes(device)}
                onCheckedChange={(v) =>
                  update({
                    devices: v
                      ? [...r.devices.filter((d) => d !== device), device]
                      : r.devices.filter((d) => d !== device),
                  })
                }
              />
              <Label htmlFor={`popup-device-${device}`} className="capitalize">
                {device}
              </Label>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4 space-y-3">
        <h3 className="font-semibold text-sm">Overlay</h3>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="popup-backdrop"
            checked={r.overlay.backdrop}
            onCheckedChange={(v) => updateOverlay({ backdrop: !!v })}
          />
          <Label htmlFor="popup-backdrop">Dim the page behind it</Label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Width</Label>
            <Input
              value={r.overlay.width}
              onChange={(e) => updateOverlay({ width: e.target.value })}
              className="mt-1"
            />
          </div>
          <div>
            <Label>Corner radius</Label>
            <Input
              value={r.overlay.borderRadius}
              onChange={(e) => updateOverlay({ borderRadius: e.target.value })}
              className="mt-1"
            />
          </div>
        </div>
      </Card>
    </div>
  );
};
