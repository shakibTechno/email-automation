/**
 * The backend stores a tag's colour as one of eight names (`Tag.COLOR_CHOICES`),
 * not as a hex value. Rendering that string straight into CSS — which TagChip
 * did — resolves to the browser's own `blue`, `red`, `purple`: fully saturated
 * primaries that are far louder than anything else in the palette and read as
 * unrelated to the product.
 *
 * So the names map to hues tuned for this palette once, here, and every surface
 * that paints a tag reads from this map. Values are mid-tone on purpose: each
 * one has to stay distinguishable as a 8px dot on both the light ground and the
 * near-black dark card, so very light and very dark hues are out.
 */
export const TAG_COLORS = [
  { value: 'blue', label: 'Blue', hex: '#3E7BD6' },
  { value: 'green', label: 'Green', hex: '#3E9D6B' },
  { value: 'yellow', label: 'Yellow', hex: '#D4A72C' },
  { value: 'orange', label: 'Orange', hex: '#DD7A3B' },
  { value: 'red', label: 'Red', hex: '#D25A52' },
  { value: 'pink', label: 'Pink', hex: '#CE5E96' },
  { value: 'purple', label: 'Purple', hex: '#8A6AD1' },
  { value: 'gray', label: 'Gray', hex: '#7C8578' },
] as const;

export type TagColorName = (typeof TAG_COLORS)[number]['value'];

export const DEFAULT_TAG_COLOR: TagColorName = 'blue';

const HEX_BY_NAME = new Map<string, string>(TAG_COLORS.map((c) => [c.value, c.hex]));

/**
 * Resolve a stored colour to something paintable. Anything unrecognised is
 * passed through, so a raw hex written directly to the database still renders
 * rather than disappearing.
 */
export const tagColorHex = (color?: string | null): string => {
  if (!color) return HEX_BY_NAME.get(DEFAULT_TAG_COLOR)!;
  return HEX_BY_NAME.get(color) ?? color;
};

export const tagColorLabel = (color?: string | null): string =>
  TAG_COLORS.find((c) => c.value === color)?.label ?? 'Custom';
