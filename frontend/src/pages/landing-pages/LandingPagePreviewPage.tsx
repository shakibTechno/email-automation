import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { usePreviewLandingPage } from '@/hooks/useLandingPages';
import { ArrowLeft, Monitor, Tablet, Smartphone } from 'lucide-react';
import { useState } from 'react';

type Device = 'desktop' | 'tablet' | 'mobile';

const deviceWidths: Record<Device, string> = {
  desktop: '100%',
  tablet: '768px',
  mobile: '375px',
};

export const LandingPagePreviewPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [device, setDevice] = useState<Device>('desktop');

  const { data, isLoading, error } = usePreviewLandingPage(id || '');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Failed to load preview</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-secondary">
      {/* Toolbar */}
      <div className="h-14 border-b bg-white flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(`/landing-pages/${id}/edit`)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="font-medium">Preview</span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center border rounded-md">
            <Button
              variant={device === 'desktop' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-r-none"
              onClick={() => setDevice('desktop')}
            >
              <Monitor className="h-4 w-4" />
            </Button>
            <Button
              variant={device === 'tablet' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-none border-x"
              onClick={() => setDevice('tablet')}
            >
              <Tablet className="h-4 w-4" />
            </Button>
            <Button
              variant={device === 'mobile' ? 'default' : 'ghost'}
              size="sm"
              className="rounded-l-none"
              onClick={() => setDevice('mobile')}
            >
              <Smartphone className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Preview Frame */}
      <div className="flex-1 flex items-start justify-center p-4 overflow-auto">
        <div
          className="bg-white shadow-lg transition-all duration-300"
          style={{
            width: deviceWidths[device],
            maxWidth: '100%',
            minHeight: device === 'desktop' ? 'calc(100vh - 6rem)' : 'auto',
          }}
        >
          <iframe
            srcDoc={data.html}
            title="Landing Page Preview"
            className="w-full h-full min-h-[600px]"
            style={{
              border: 'none',
              display: 'block',
            }}
          />
        </div>
      </div>
    </div>
  );
};
