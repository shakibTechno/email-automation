import { Palette, Type, Layout, Image, Code } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  FormStyling,
  FormBranding,
  FormLayout,
  defaultFormStyling,
  defaultFormBranding,
  defaultFormLayout,
} from '@/types/form';

interface ColorInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

const ColorInput = ({ label, value, onChange }: ColorInputProps) => (
  <div className="space-y-1">
    <Label className="text-xs">{label}</Label>
    <div className="flex gap-2">
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-10 h-9 rounded border cursor-pointer"
      />
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 font-mono text-xs"
        placeholder="#000000"
      />
    </div>
  </div>
);

interface FormDesignPanelProps {
  styling: FormStyling;
  branding: FormBranding;
  layout: FormLayout;
  onStylingChange: (styling: FormStyling) => void;
  onBrandingChange: (branding: FormBranding) => void;
  onLayoutChange: (layout: FormLayout) => void;
}

export const FormDesignPanel = ({
  styling,
  branding,
  layout,
  onStylingChange,
  onBrandingChange,
  onLayoutChange,
}: FormDesignPanelProps) => {
  const s = { ...defaultFormStyling, ...styling };
  const b = { ...defaultFormBranding, ...branding };
  const l = { ...defaultFormLayout, ...layout };

  const updateStyling = (partial: Partial<FormStyling>) => {
    onStylingChange({ ...s, ...partial });
  };

  const updateButtonStyle = (partial: Partial<FormStyling['buttonStyle']>) => {
    onStylingChange({
      ...s,
      buttonStyle: { ...s.buttonStyle, ...partial },
    });
  };

  const updateInputStyle = (partial: Partial<FormStyling['inputStyle']>) => {
    onStylingChange({
      ...s,
      inputStyle: { ...s.inputStyle, ...partial },
    });
  };

  const updateBranding = (partial: Partial<FormBranding>) => {
    onBrandingChange({ ...b, ...partial });
  };

  const updateLayout = (partial: Partial<FormLayout>) => {
    onLayoutChange({ ...l, ...partial });
  };

  return (
    <Tabs defaultValue="colors" className="w-full">
      <TabsList className="grid w-full grid-cols-4">
        <TabsTrigger value="colors" className="text-xs">
          <Palette className="h-3 w-3 mr-1" /> Colors
        </TabsTrigger>
        <TabsTrigger value="typography" className="text-xs">
          <Type className="h-3 w-3 mr-1" /> Type
        </TabsTrigger>
        <TabsTrigger value="layout" className="text-xs">
          <Layout className="h-3 w-3 mr-1" /> Layout
        </TabsTrigger>
        <TabsTrigger value="branding" className="text-xs">
          <Image className="h-3 w-3 mr-1" /> Brand
        </TabsTrigger>
      </TabsList>

      {/* Colors Tab */}
      <TabsContent value="colors" className="space-y-4 mt-4">
        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Form Colors</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <ColorInput
              label="Primary Color"
              value={s.primaryColor}
              onChange={(v) => updateStyling({ primaryColor: v })}
            />
            <ColorInput
              label="Background"
              value={s.backgroundColor}
              onChange={(v) => updateStyling({ backgroundColor: v })}
            />
            <ColorInput
              label="Text Color"
              value={s.textColor}
              onChange={(v) => updateStyling({ textColor: v })}
            />
            <ColorInput
              label="Label Color"
              value={s.labelColor}
              onChange={(v) => updateStyling({ labelColor: v })}
            />
            <ColorInput
              label="Border Color"
              value={s.borderColor}
              onChange={(v) => updateStyling({ borderColor: v })}
            />
            <ColorInput
              label="Error Color"
              value={s.errorColor}
              onChange={(v) => updateStyling({ errorColor: v })}
            />
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Button Colors</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <ColorInput
              label="Button Background"
              value={s.buttonStyle.backgroundColor}
              onChange={(v) => updateButtonStyle({ backgroundColor: v })}
            />
            <ColorInput
              label="Button Text"
              value={s.buttonStyle.textColor}
              onChange={(v) => updateButtonStyle({ textColor: v })}
            />
            <ColorInput
              label="Button Hover"
              value={s.buttonStyle.hoverBackgroundColor}
              onChange={(v) => updateButtonStyle({ hoverBackgroundColor: v })}
            />
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Input Focus</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <ColorInput
              label="Focus Border"
              value={s.inputStyle.focusBorderColor}
              onChange={(v) => updateInputStyle({ focusBorderColor: v })}
            />
            <ColorInput
              label="Focus Ring"
              value={s.inputStyle.focusRingColor}
              onChange={(v) => updateInputStyle({ focusRingColor: v })}
            />
          </div>
        </Card>
      </TabsContent>

      {/* Typography Tab */}
      <TabsContent value="typography" className="space-y-4 mt-4">
        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Font Settings</h3>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Font Family</Label>
              <Select
                value={s.fontFamily}
                onValueChange={(v) => updateStyling({ fontFamily: v })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Inter, system-ui, sans-serif">Inter</SelectItem>
                  <SelectItem value="system-ui, sans-serif">System UI</SelectItem>
                  <SelectItem value="'Roboto', sans-serif">Roboto</SelectItem>
                  <SelectItem value="'Open Sans', sans-serif">Open Sans</SelectItem>
                  <SelectItem value="'Lato', sans-serif">Lato</SelectItem>
                  <SelectItem value="Georgia, serif">Georgia</SelectItem>
                  <SelectItem value="'Times New Roman', serif">Times New Roman</SelectItem>
                  <SelectItem value="monospace">Monospace</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label className="text-xs">Base Font Size</Label>
                <Input
                  value={s.fontSize}
                  onChange={(e) => updateStyling({ fontSize: e.target.value })}
                  placeholder="14px"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Label Font Size</Label>
                <Input
                  value={s.labelFontSize}
                  onChange={(e) => updateStyling({ labelFontSize: e.target.value })}
                  placeholder="14px"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Label Font Weight</Label>
                <Select
                  value={s.labelFontWeight}
                  onValueChange={(v) => updateStyling({ labelFontWeight: v })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="400">Normal (400)</SelectItem>
                    <SelectItem value="500">Medium (500)</SelectItem>
                    <SelectItem value="600">Semibold (600)</SelectItem>
                    <SelectItem value="700">Bold (700)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Border & Spacing</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label className="text-xs">Border Radius</Label>
              <Input
                value={s.borderRadius}
                onChange={(e) => updateStyling({ borderRadius: e.target.value })}
                placeholder="6px"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">Field Spacing</Label>
              <Input
                value={s.fieldSpacing}
                onChange={(e) => updateStyling({ fieldSpacing: e.target.value })}
                placeholder="16px"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">Form Padding</Label>
              <Input
                value={s.padding}
                onChange={(e) => updateStyling({ padding: e.target.value })}
                placeholder="24px"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">Input Padding</Label>
              <Input
                value={s.inputStyle.padding}
                onChange={(e) => updateInputStyle({ padding: e.target.value })}
                placeholder="10px 12px"
                className="mt-1"
              />
            </div>
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Button Style</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label className="text-xs">Button Border Radius</Label>
              <Input
                value={s.buttonStyle.borderRadius}
                onChange={(e) => updateButtonStyle({ borderRadius: e.target.value })}
                placeholder="6px"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">Button Padding</Label>
              <Input
                value={s.buttonStyle.padding}
                onChange={(e) => updateButtonStyle({ padding: e.target.value })}
                placeholder="10px 20px"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">Button Font Size</Label>
              <Input
                value={s.buttonStyle.fontSize}
                onChange={(e) => updateButtonStyle({ fontSize: e.target.value })}
                placeholder="14px"
                className="mt-1"
              />
            </div>
            <div className="flex items-end">
              <div className="flex items-center space-x-2 pb-2">
                <Checkbox
                  id="fullWidthBtn"
                  checked={s.buttonStyle.fullWidth}
                  onCheckedChange={(c) => updateButtonStyle({ fullWidth: c === true })}
                />
                <Label htmlFor="fullWidthBtn" className="text-xs">Full Width Button</Label>
              </div>
            </div>
          </div>
        </Card>
      </TabsContent>

      {/* Layout Tab */}
      <TabsContent value="layout" className="space-y-4 mt-4">
        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Form Dimensions</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label className="text-xs">Form Width</Label>
              <Input
                value={l.formWidth}
                onChange={(e) => updateLayout({ formWidth: e.target.value })}
                placeholder="100%"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">Max Width</Label>
              <Input
                value={l.maxWidth}
                onChange={(e) => updateLayout({ maxWidth: e.target.value })}
                placeholder="480px"
                className="mt-1"
              />
            </div>
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Grid Layout</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label className="text-xs">Columns</Label>
              <Select
                value={String(l.columns)}
                onValueChange={(v) => updateLayout({ columns: parseInt(v) as 1 | 2 | 3 })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 Column</SelectItem>
                  <SelectItem value="2">2 Columns</SelectItem>
                  <SelectItem value="3">3 Columns</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Alignment</Label>
              <Select
                value={l.alignment}
                onValueChange={(v: 'left' | 'center' | 'right') => updateLayout({ alignment: v })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="left">Left</SelectItem>
                  <SelectItem value="center">Center</SelectItem>
                  <SelectItem value="right">Right</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Field Gap (horizontal)</Label>
              <Input
                value={l.fieldGap}
                onChange={(e) => updateLayout({ fieldGap: e.target.value })}
                placeholder="16px"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">Row Gap (vertical)</Label>
              <Input
                value={l.rowGap}
                onChange={(e) => updateLayout({ rowGap: e.target.value })}
                placeholder="16px"
                className="mt-1"
              />
            </div>
          </div>
        </Card>
      </TabsContent>

      {/* Branding Tab */}
      <TabsContent value="branding" className="space-y-4 mt-4">
        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Logo</h3>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Logo URL</Label>
              <Input
                value={b.logoUrl}
                onChange={(e) => updateBranding({ logoUrl: e.target.value })}
                placeholder="https://example.com/logo.png"
                className="mt-1"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label className="text-xs">Logo Position</Label>
                <Select
                  value={b.logoPosition}
                  onValueChange={(v: 'left' | 'center' | 'right') => updateBranding({ logoPosition: v })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="left">Left</SelectItem>
                    <SelectItem value="center">Center</SelectItem>
                    <SelectItem value="right">Right</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Logo Max Height</Label>
                <Input
                  value={b.logoMaxHeight}
                  onChange={(e) => updateBranding({ logoMaxHeight: e.target.value })}
                  placeholder="48px"
                  className="mt-1"
                />
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Header</h3>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Header Text</Label>
              <Input
                value={b.headerText}
                onChange={(e) => updateBranding({ headerText: e.target.value })}
                placeholder="Join our newsletter"
                className="mt-1"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <Label className="text-xs">Font Size</Label>
                <Input
                  value={b.headerFontSize}
                  onChange={(e) => updateBranding({ headerFontSize: e.target.value })}
                  placeholder="24px"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Font Weight</Label>
                <Select
                  value={b.headerFontWeight}
                  onValueChange={(v) => updateBranding({ headerFontWeight: v })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="400">Normal</SelectItem>
                    <SelectItem value="500">Medium</SelectItem>
                    <SelectItem value="600">Semibold</SelectItem>
                    <SelectItem value="700">Bold</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Alignment</Label>
                <Select
                  value={b.headerAlignment}
                  onValueChange={(v: 'left' | 'center' | 'right') => updateBranding({ headerAlignment: v })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="left">Left</SelectItem>
                    <SelectItem value="center">Center</SelectItem>
                    <SelectItem value="right">Right</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm">Footer</h3>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Footer Text</Label>
              <Textarea
                value={b.footerText}
                onChange={(e) => updateBranding({ footerText: e.target.value })}
                placeholder="We respect your privacy. Unsubscribe at any time."
                rows={2}
                className="mt-1"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label className="text-xs">Footer Font Size</Label>
                <Input
                  value={b.footerFontSize}
                  onChange={(e) => updateBranding({ footerFontSize: e.target.value })}
                  placeholder="12px"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Footer Alignment</Label>
                <Select
                  value={b.footerAlignment}
                  onValueChange={(v: 'left' | 'center' | 'right') => updateBranding({ footerAlignment: v })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="left">Left</SelectItem>
                    <SelectItem value="center">Center</SelectItem>
                    <SelectItem value="right">Right</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="showPoweredBy"
                checked={b.showPoweredBy}
                onCheckedChange={(c) => updateBranding({ showPoweredBy: c === true })}
              />
              <Label htmlFor="showPoweredBy" className="text-xs">Show "Powered by" branding</Label>
            </div>
          </div>
        </Card>

        <Card className="p-4 space-y-4">
          <h3 className="font-medium text-sm flex items-center gap-2">
            <Code className="h-4 w-4" /> Custom CSS
          </h3>
          <div>
            <Label className="text-xs">Additional CSS (advanced)</Label>
            <Textarea
              value={b.customCss}
              onChange={(e) => updateBranding({ customCss: e.target.value })}
              placeholder=".form-container { /* your styles */ }"
              rows={4}
              className="mt-1 font-mono text-xs"
            />
          </div>
        </Card>
      </TabsContent>
    </Tabs>
  );
};
