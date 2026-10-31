import { PopupDesign, PopupType } from '@/types/popup';

interface Props {
  device: 'desktop' | 'mobile';
  popupType: PopupType;
  title: string;
  description: string;
  imageUrl: string;
  ctaText: string;
  hasForm: boolean;
  design: PopupDesign;
}

/**
 * The real overlay at both widths, not a mock of it.
 *
 * Drawn from the same design blob the website snippet reads, so what a
 * marketer approves here is what a visitor gets. The one thing it cannot show
 * is the embedded form, which renders in an iframe on the live site; that is
 * stated rather than faked, because a fake form is how a preview starts
 * lying.
 */
export const PopupPreview = ({
  device, popupType, title, description, imageUrl, ctaText, hasForm, design,
}: Props) => {
  const mobile = device === 'mobile';
  const bar = popupType === 'floating_bar';
  const full = popupType === 'full_screen';

  const frame = mobile
    ? 'w-[320px] h-[560px]'
    : 'w-full aspect-[16/10]';

  const placement = bar
    ? 'absolute inset-x-0 top-0'
    : full
      ? 'absolute inset-0 flex items-center justify-center'
      : mobile
        ? 'absolute inset-x-0 bottom-0'
        : {
            center: 'absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            bottom_right: 'absolute right-4 bottom-4',
            bottom_left: 'absolute left-4 bottom-4',
            top: 'absolute left-1/2 top-4 -translate-x-1/2',
          }[design.position];

  const card = (
    <div
      style={{
        background: design.backgroundColor,
        color: design.textColor,
        borderRadius: bar ? 0 : mobile ? '16px 16px 0 0' : design.borderRadius,
        padding: bar ? '10px 14px' : '18px',
        fontFamily: design.fontFamily,
        maxWidth: bar || full || mobile ? '100%' : '280px',
        width: bar || full || mobile ? '100%' : undefined,
      }}
      className="shadow-lg"
    >
      {imageUrl && !bar && design.image.position !== 'none' && (
        <img
          src={imageUrl}
          alt=""
          className="mb-2 w-full rounded object-cover"
          style={{ height: '72px' }}
        />
      )}
      <div className={bar ? 'flex items-center justify-between gap-3' : ''}>
        <div>
          {title && (
            <p
              className="text-sm font-semibold leading-tight"
              style={{ color: design.headingColor }}
            >
              {title}
            </p>
          )}
          {description && !bar && (
            <p className="mt-1 text-xs opacity-80">{description}</p>
          )}
        </div>
        <div className={bar ? '' : 'mt-3'}>
          {hasForm && !bar && (
            <div
              className="mb-2 rounded border border-dashed px-2 py-3 text-center text-[11px] opacity-60"
              style={{ borderColor: design.textColor }}
            >
              your form renders here
            </div>
          )}
          {ctaText && (
            <span
              className="inline-block rounded px-3 py-1.5 text-xs font-medium"
              style={{
                background: design.primaryButton.backgroundColor,
                color: design.primaryButton.textColor,
                borderRadius: design.primaryButton.borderRadius,
                width: design.primaryButton.fullWidth && !bar ? '100%' : undefined,
                textAlign: 'center',
              }}
            >
              {ctaText}
            </span>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className={`relative mx-auto overflow-hidden rounded-lg border bg-secondary/40 ${frame}`}>
      {/* A stand-in for the customer's own page, so position reads correctly. */}
      <div className="space-y-2 p-4 opacity-30">
        <div className="h-2.5 w-1/3 rounded bg-foreground/30" />
        <div className="h-2 w-full rounded bg-foreground/20" />
        <div className="h-2 w-5/6 rounded bg-foreground/20" />
        <div className="h-2 w-4/6 rounded bg-foreground/20" />
      </div>

      {design.backdrop && !bar && (
        <div className="absolute inset-0" style={{ background: design.backdropColor }} />
      )}

      <div className={placement}>{card}</div>

      {mobile && !bar && (
        <p className="absolute inset-x-0 bottom-0 translate-y-full pt-1 text-center text-[11px] text-muted-foreground">
          Phones always get a bottom sheet — a centred box sits behind the keyboard.
        </p>
      )}
    </div>
  );
};
