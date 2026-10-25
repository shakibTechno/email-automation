import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

/**
 * Shows page markup as it will actually render, scaled to fit its container.
 *
 * Landing pages and templates were both represented by a generic icon, so
 * neither could be told apart at a glance. Rather than a screenshot pipeline
 * (a headless browser in the stack, images that go stale the moment the page
 * is edited), this renders the real markup in a sandboxed frame at desktop
 * width and scales it down. Nothing to store, and it cannot drift.
 */

/** Width the content is laid out at before scaling, so previews read as desktop. */
const LAYOUT_WIDTH = 1280;

interface HtmlPreviewProps {
  html?: string | null;
  css?: string | null;
  /** Height of the preview box in px; width comes from the container. */
  height?: number;
  className?: string;
  /** Rendered instead of the frame when there is nothing to show. */
  placeholder?: React.ReactNode;
}

export const HtmlPreview = ({
  html,
  css,
  height = 150,
  className,
  placeholder,
}: HtmlPreviewProps) => {
  const boxRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.2);

  useEffect(() => {
    const node = boxRef.current;
    if (!node) return;
    const measure = () => setScale(node.clientWidth / LAYOUT_WIDTH);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  // Mirrors the <head> that LandingPageService.render_page_html builds, so the
  // preview and the published page agree on how blocks are styled.
  const srcDoc = html
    ? `<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fff}
  img{max-width:100%;height:auto}
  ${css || ''}
</style></head><body>${html}</body></html>`
    : null;

  return (
    <div
      ref={boxRef}
      className={cn('relative overflow-hidden bg-white', className)}
      style={{ height }}
    >
      {srcDoc ? (
        <iframe
          title="Page preview"
          srcDoc={srcDoc}
          // allow-scripts without allow-same-origin puts the frame in an opaque
          // origin: Tailwind's CDN can style it exactly as it styles the
          // published page, while the markup cannot reach this document, its
          // storage or its cookies.
          sandbox="allow-scripts"
          referrerPolicy="no-referrer"
          scrolling="no"
          aria-hidden="true"
          className="pointer-events-none border-0 bg-white"
          style={{
            width: LAYOUT_WIDTH,
            height: height / scale,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
        />
      ) : (
        <div className="flex h-full items-center justify-center bg-secondary/50">
          {placeholder}
        </div>
      )}
    </div>
  );
};
