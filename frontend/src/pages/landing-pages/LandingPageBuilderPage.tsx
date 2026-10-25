import { useState, useCallback, useRef, useEffect, lazy, Suspense } from 'react';
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
import type { GrapesJSEditorRef, EditorStatus } from '@/components/landing-pages/GrapesJSEditor';
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
  Undo2,
  Redo2,
  Check,
  AlertCircle,
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
  const [status, setStatus] = useState<EditorStatus>({
    isDirty: false,
    canUndo: false,
    canRedo: false,
  });
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  // Re-renders the relative "Saved 2m ago" label without touching save logic.
  const [, setNow] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setNow((n) => n + 1), 30000);
    return () => clearInterval(t);
  }, []);

  // Closing the tab mid-edit should cost a prompt, not the work. React Router
  // navigation is already a deliberate click on our own back arrow, which the
  // toolbar guards separately.
  useEffect(() => {
    if (!status.isDirty) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [status.isDirty]);

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
        // No success toast: autosave fires on a timer, and a toast every time
        // it lands turns a quiet background action into a notification queue.
        // The toolbar carries the state instead. Failures still shout.
        setLastSavedAt(new Date());
      } catch (error) {
        toast.error('Failed to save design');
        setStatus((s) => ({ ...s, isDirty: true }));
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

  const handleBack = () => {
    if (
      status.isDirty &&
      !window.confirm('You have unsaved changes. Leave the builder anyway?')
    ) {
      return;
    }
    navigate('/landing-pages');
  };

  const savedLabel = () => {
    if (isSaving) return 'Saving…';
    if (status.isDirty) return 'Unsaved changes';
    if (!lastSavedAt) return 'All changes saved';
    const mins = Math.floor((Date.now() - lastSavedAt.getTime()) / 60000);
    if (mins < 1) return 'Saved just now';
    if (mins === 1) return 'Saved 1 min ago';
    return `Saved ${mins} mins ago`;
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
            onClick={handleBack}
            title="Back to landing pages"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="w-px h-4 bg-secondary shrink-0" />
          <span className="font-medium text-sm truncate max-w-[200px]">
            {landingPage.name}
          </span>
          <LandingPageStatusBadge status={landingPage.status} />

          {/* Persistent save state. This was a "Saving" flash that appeared for
              a few hundred milliseconds every 30 seconds and told you nothing
              the rest of the time. */}
          <span className="ml-1 hidden items-center gap-1 text-xs text-subtle-foreground sm:flex">
            {isSaving ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : status.isDirty ? (
              <AlertCircle className="h-3 w-3 text-warning" />
            ) : (
              <Check className="h-3 w-3 text-success" />
            )}
            {savedLabel()}
          </span>
        </div>

        {/* Undo/redo. GrapesJS tracked history all along, but the only way to
            reach it was a keyboard shortcut nobody was told about. */}
        <div className="flex shrink-0 items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            title="Undo (Ctrl+Z)"
            aria-label="Undo"
            disabled={!status.canUndo}
            onClick={() => editorRef.current?.undo()}
          >
            <Undo2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            title="Redo (Ctrl+Shift+Z)"
            aria-label="Redo"
            disabled={!status.canRedo}
            onClick={() => editorRef.current?.redo()}
          >
            <Redo2 className="h-4 w-4" />
          </Button>
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

          {/* On a published page, saving *is* publishing — the public URL
              serves this content directly. The button says so rather than
              letting the user discover it. */}
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={handleSaveClick}
            disabled={isSaving}
            title={
              landingPage.status === 'published'
                ? 'This page is live. Saving updates it for visitors immediately.'
                : 'Save your changes'
            }
          >
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
            ) : (
              <Save className="h-3.5 w-3.5 mr-1.5" />
            )}
            {landingPage.status === 'published' ? 'Save to live page' : 'Save'}
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
            onStatusChange={setStatus}
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
