import { useState, useCallback, useRef, lazy, Suspense } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LandingPageStatusBadge } from '@/components/landing-pages/LandingPageStatusBadge';
import { SettingsPanel } from '@/components/landing-pages/SettingsPanel';
import { SaveAsTemplateDialog } from '@/components/landing-pages/SaveAsTemplateDialog';
import type { GrapesJSEditorRef } from '@/components/landing-pages/GrapesJSEditor';
import {
  useLandingPage,
  useSaveDesign,
  useUpdateLandingPage,
  usePublishLandingPage,
  useUnpublishLandingPage,
} from '@/hooks/useLandingPages';
import { useSaveAsTemplate } from '@/hooks/useLandingPageTemplates';
import { useForms } from '@/hooks/useForms';
import {
  ArrowLeft,
  Settings,
  Eye,
  Save,
  Globe,
  CircleSlash,
  Monitor,
  Tablet,
  Smartphone,
  MoreHorizontal,
  FileText,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

// Lazy load GrapesJS editor to avoid SSR issues
const GrapesJSEditor = lazy(
  () => import('@/components/landing-pages/GrapesJSEditor')
);

export const LandingPageBuilderPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = !id;
  const editorRef = useRef<GrapesJSEditorRef>(null);

  const { landingPage, isLoading } = useLandingPage(id || '');
  const { forms: activeForms } = useForms({ status: 'active' });
  const saveDesignMutation = useSaveDesign();
  const updateMutation = useUpdateLandingPage();
  const publishMutation = usePublishLandingPage();
  const unpublishMutation = useUnpublishLandingPage();
  const saveAsTemplateMutation = useSaveAsTemplate();

  const [showSettings, setShowSettings] = useState(false);
  const [showSaveAsTemplate, setShowSaveAsTemplate] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeDevice, setActiveDevice] = useState<'Desktop' | 'Tablet' | 'Mobile'>('Desktop');

  const handleDeviceChange = (device: 'Desktop' | 'Tablet' | 'Mobile') => {
    setActiveDevice(device);
    editorRef.current?.setDevice(device);
  };

  const handleSave = useCallback(
    async (data: { html: string; css: string; designJson: Record<string, any> }) => {
      if (!id) return;

      setIsSaving(true);
      try {
        await saveDesignMutation.mutateAsync({
          id,
          data: {
            html_content: data.html,
            css_content: data.css,
            design_json: data.designJson,
          },
        });
        toast.success('Design saved');
      } catch (error) {
        toast.error('Failed to save design');
      } finally {
        setIsSaving(false);
      }
    },
    [id, saveDesignMutation]
  );

  const handleSaveClick = () => {
    if (editorRef.current) {
      editorRef.current.save();
    }
  };

  const handleSettingsSave = async (data: any) => {
    if (!id) return;
    await updateMutation.mutateAsync({ id, data });
    setShowSettings(false);
  };

  const handleSaveAsTemplate = async (data: {
    name: string;
    description: string;
    category: any;
  }) => {
    if (!id) return;
    await saveAsTemplateMutation.mutateAsync({
      landing_page_id: id,
      ...data,
    });
    setShowSaveAsTemplate(false);
  };

  const handlePreview = () => {
    if (landingPage) {
      window.open(`/landing-pages/${id}/preview`, '_blank');
    }
  };

  if (isNew) {
    navigate('/landing-pages');
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!landingPage) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Landing page not found</p>
      </div>
    );
  }

  const deviceOptions = [
    { device: 'Desktop' as const, icon: Monitor },
    { device: 'Tablet' as const, icon: Tablet },
    { device: 'Mobile' as const, icon: Smartphone },
  ];

  return (
    <div className="flex flex-col h-screen bg-card">
      {/* ── Toolbar ─────────────────────────────────────────────────────── */}
      <div className="h-12 shrink-0 border-b bg-card flex items-center px-3 gap-2">

        {/* Left zone: back + name + status */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => navigate('/landing-pages')}
            title="Back to landing pages"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="w-px h-4 bg-secondary shrink-0" />
          <span className="font-medium text-sm truncate max-w-[200px]">
            {landingPage.name}
          </span>
          <LandingPageStatusBadge status={landingPage.status} />
          {isSaving && (
            <span className="hidden sm:flex items-center gap-1 text-xs text-subtle-foreground ml-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Saving
            </span>
          )}
        </div>

        {/* Center zone: device toggle pill */}
        <div className="flex items-center bg-secondary rounded-lg p-0.5 gap-0.5 shrink-0">
          {deviceOptions.map(({ device, icon: Icon }) => (
            <button
              key={device}
              title={device}
              onClick={() => handleDeviceChange(device)}
              className={`h-7 w-8 flex items-center justify-center rounded-md transition-colors ${
                activeDevice === device
                  ? 'bg-card shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
            </button>
          ))}
        </div>

        {/* Right zone: action buttons */}
        <div className="flex items-center gap-1 flex-1 justify-end">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handlePreview}
            title="Preview page"
          >
            <Eye className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setShowSettings(true)}
            title="Page settings"
          >
            <Settings className="h-4 w-4" />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" title="More options">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setShowSaveAsTemplate(true)}>
                <FileText className="h-4 w-4 mr-2" />
                Save as Template
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <div className="w-px h-5 bg-secondary mx-1 shrink-0" />

          {landingPage.status === 'draft' ? (
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs"
              onClick={() => publishMutation.mutate(landingPage.id)}
              disabled={publishMutation.isPending}
            >
              <Globe className="h-3.5 w-3.5 mr-1.5" />
              Publish
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs"
              onClick={() => unpublishMutation.mutate(landingPage.id)}
              disabled={unpublishMutation.isPending}
            >
              <CircleSlash className="h-3.5 w-3.5 mr-1.5" />
              Unpublish
            </Button>
          )}

          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={handleSaveClick}
            disabled={isSaving}
          >
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
            ) : (
              <Save className="h-3.5 w-3.5 mr-1.5" />
            )}
            Save
          </Button>
        </div>
      </div>

      {/* ── Editor ──────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-subtle-foreground" />
            </div>
          }
        >
          <GrapesJSEditor
            ref={editorRef}
            initialHtml={landingPage.html_content || ''}
            initialCss={landingPage.css_content || ''}
            initialData={landingPage.design_json}
            onSave={handleSave}
            forms={activeForms || []}
          />
        </Suspense>
      </div>

      {/* Settings Panel */}
      <SettingsPanel
        open={showSettings}
        onOpenChange={setShowSettings}
        landingPage={landingPage}
        onSave={handleSettingsSave}
        isSaving={updateMutation.isPending}
      />

      {/* Save as Template Dialog */}
      <SaveAsTemplateDialog
        open={showSaveAsTemplate}
        onOpenChange={setShowSaveAsTemplate}
        onSave={handleSaveAsTemplate}
        isLoading={saveAsTemplateMutation.isPending}
        defaultName={`${landingPage.name} Template`}
      />
    </div>
  );
};
