import { useEffect, useRef, useState } from 'react';
import { Loader2, FileText } from 'lucide-react';
import { HtmlPreview } from '@/components/landing-pages/HtmlPreview';
import { useLandingPageTemplate } from '@/hooks/useLandingPageTemplates';

/**
 * A template's own markup, rendered as the gallery card.
 *
 * The list endpoint deliberately omits `html_content` — a full page runs to a
 * hundred kilobytes and more — so each card fetches its own template detail,
 * and only once it is near the viewport.
 */
interface TemplatePreviewProps {
  templateId: string;
  height?: number;
  className?: string;
}

export const TemplatePreview = ({
  templateId,
  height = 150,
  className,
}: TemplatePreviewProps) => {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node || visible) return;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setVisible(true),
      { rootMargin: '200px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [visible]);

  const { template, isLoading } = useLandingPageTemplate(visible ? templateId : '');

  return (
    <div ref={sentinelRef}>
      <HtmlPreview
        html={template?.html_content}
        css={template?.css_content}
        height={height}
        className={className}
        placeholder={
          isLoading || !visible ? (
            <Loader2 className="h-5 w-5 animate-spin text-subtle-foreground" />
          ) : (
            <FileText className="h-8 w-8 text-subtle-foreground" />
          )
        }
      />
    </div>
  );
};
