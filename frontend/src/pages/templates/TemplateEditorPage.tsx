import { useRef, useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import EmailEditor, { EditorRef, Editor } from 'react-email-editor';
import { ArrowLeft, Save, Monitor, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTemplate, useTemplates } from '@/hooks/useTemplates';
import { TemplateCategory } from '@/types/template';
import { toast } from 'sonner';
import apiClient from '@/api/client';

const MERGE_TAGS = {
  first_name: { name: 'First Name', value: '{{first_name}}' },
  last_name: { name: 'Last Name', value: '{{last_name}}' },
  email: { name: 'Email', value: '{{email}}' },
  company: { name: 'Company', value: '{{company}}' },
  unsubscribe_url: {
    name: 'Unsubscribe URL',
    value: '{{unsubscribe_url}}',
  },
};

export const TemplateEditorPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const emailEditorRef = useRef<EditorRef>(null);
  const isEditMode = !!id;

  const [templateName, setTemplateName] = useState('Untitled Template');
  const [category, setCategory] = useState<TemplateCategory>('custom');
  const [subject, setSubject] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [editorReady, setEditorReady] = useState(false);
  const [devicePreview, setDevicePreview] = useState<'desktop' | 'mobile'>(
    'desktop'
  );

  const { template, isLoading: isLoadingTemplate } = useTemplate(id || '');
  const { createTemplate, updateTemplate } = useTemplates();

  // Load template data when available
  useEffect(() => {
    if (template && editorReady && emailEditorRef.current?.editor) {
      setTemplateName(template.name);
      setCategory(template.category);
      setSubject(template.subject || '');

      if (
        template.design_json &&
        Object.keys(template.design_json).length > 0
      ) {
        emailEditorRef.current.editor.loadDesign(template.design_json as any);
      }
    }
  }, [template, editorReady]);

  const handleReady = useCallback((unlayer: Editor) => {
    setEditorReady(true);

    // Register image upload handler
    unlayer.registerCallback('image', (file: any, done: any) => {
      const formData = new FormData();
      formData.append('image', file.attachments[0]);

      apiClient
        .post('/template-images/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        .then((response) => {
          done({ progress: 100, url: response.data.image });
        })
        .catch(() => {
          toast.error('Failed to upload image');
        });
    });
  }, []);

  const handleSave = useCallback(async () => {
    if (!emailEditorRef.current?.editor) return;

    setIsSaving(true);

    try {
      // Get design JSON and HTML from editor
      const [designJson, htmlData] = await Promise.all([
        new Promise<Record<string, any>>((resolve) => {
          emailEditorRef.current!.editor!.saveDesign((design: any) => {
            resolve(design);
          });
        }),
        new Promise<string>((resolve) => {
          emailEditorRef.current!.editor!.exportHtml((data: any) => {
            resolve(data.html);
          });
        }),
      ]);

      const templateData = {
        name: templateName,
        category,
        subject,
        design_json: designJson,
        html_content: htmlData,
      };

      if (isEditMode && id) {
        await updateTemplate(id, templateData);
      } else {
        const created = await createTemplate(templateData);
        // Navigate to edit mode with the new ID
        navigate(`/templates/${created.id}/edit`, { replace: true });
      }
    } catch (error: any) {
      // Error toast is handled by the hook
    } finally {
      setIsSaving(false);
    }
  }, [
    templateName,
    category,
    subject,
    isEditMode,
    id,
    createTemplate,
    updateTemplate,
    navigate,
  ]);

  const toggleDevice = useCallback(() => {
    if (!emailEditorRef.current?.editor) return;
    const newDevice = devicePreview === 'desktop' ? 'mobile' : 'desktop';
    setDevicePreview(newDevice);
    emailEditorRef.current.editor.setAppearance({
      panels: {
        tools: {
          dock: newDevice === 'desktop' ? 'right' : 'right',
        },
      },
    });
    // Use setDevice for mobile preview
    (emailEditorRef.current.editor as any).setDevice(newDevice);
  }, [devicePreview]);

  if (isEditMode && isLoadingTemplate) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-white shrink-0">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/templates')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>

          <Input
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            className="w-64 h-8 text-sm font-medium"
            placeholder="Template name"
          />

          <Select
            value={category}
            onValueChange={(val) => setCategory(val as TemplateCategory)}
          >
            <SelectTrigger className="w-40 h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="marketing">Marketing</SelectItem>
              <SelectItem value="transactional">Transactional</SelectItem>
              <SelectItem value="newsletter">Newsletter</SelectItem>
              <SelectItem value="welcome">Welcome</SelectItem>
              <SelectItem value="notification">Notification</SelectItem>
              <SelectItem value="custom">Custom</SelectItem>
            </SelectContent>
          </Select>

          <Input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-64 h-8 text-sm"
            placeholder="Email subject line"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleDevice}
            title={
              devicePreview === 'desktop'
                ? 'Switch to mobile preview'
                : 'Switch to desktop preview'
            }
          >
            {devicePreview === 'desktop' ? (
              <Smartphone className="h-4 w-4" />
            ) : (
              <Monitor className="h-4 w-4" />
            )}
          </Button>

          <Button size="sm" onClick={handleSave} disabled={isSaving}>
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      {/* Email Editor */}
      <div className="flex-1 min-h-0">
        <EmailEditor
          ref={emailEditorRef}
          onReady={handleReady}
          minHeight="100%"
          options={{
            mergeTags: MERGE_TAGS,
            features: {
              textEditor: {
                spellChecker: true,
              },
            },
            appearance: {
              theme: 'light',
            },
          }}
        />
      </div>
    </div>
  );
};
