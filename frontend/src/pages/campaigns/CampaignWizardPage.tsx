import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Settings,
  FileText,
  Users,
  Send,
  Mail,
  Eye,
  FlaskConical,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { useCampaign, useCampaigns, useABTest } from '@/hooks/useCampaigns';
import { useTemplates } from '@/hooks/useTemplates';
import { useTags } from '@/hooks/useTags';
import { CampaignPreviewDialog } from '@/components/campaigns/CampaignPreviewDialog';
import { TestEmailDialog } from '@/components/campaigns/TestEmailDialog';
import { ABTestConfigPanel } from '@/components/campaigns/ABTestConfigPanel';
import {
  CreateCampaignData,
  RecipientType,
  ABTestConfig,
} from '@/types/campaign';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const STEPS = [
  { id: 1, label: 'Settings', icon: Settings },
  { id: 2, label: 'Template', icon: FileText },
  { id: 3, label: 'Recipients', icon: Users },
  { id: 4, label: 'Review & Send', icon: Send },
];

export const CampaignWizardPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = !!id;

  const [currentStep, setCurrentStep] = useState(1);
  const [campaignId, setCampaignId] = useState<string | null>(id || null);

  // Form state
  const [name, setName] = useState('');
  const [subject, setSubject] = useState('');
  const [preheaderText, setPreheaderText] = useState('');
  const [senderName, setSenderName] = useState('');
  const [senderEmail, setSenderEmail] = useState('');
  const [replyToEmail, setReplyToEmail] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [recipientType, setRecipientType] = useState<RecipientType>('all_subscribed');
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [scheduledAt, setScheduledAt] = useState('');

  // A/B test state
  const [abEnabled, setAbEnabled] = useState(false);
  const [abConfig, setAbConfig] = useState<ABTestConfig>({
    test_type: 'subject',
    test_percentage: 20,
    winner_criteria: 'open_rate',
    winner_selection: 'auto',
    test_duration_hours: 4,
    variant_b_subject: '',
    variant_b_sender_name: '',
    variant_b_template: null,
  });

  // Dialogs
  const [previewOpen, setPreviewOpen] = useState(false);
  const [testEmailOpen, setTestEmailOpen] = useState(false);

  // Hooks
  const { campaign, isLoading: isLoadingCampaign } = useCampaign(id || '');
  const {
    createCampaign,
    updateCampaign,
    sendCampaign,
    sendTestEmail,
    isCreating,
    isUpdating,
    isSending,
    isSendingTest,
  } = useCampaigns();
  const { saveABTest, deleteABTest, isSaving: isSavingAB } = useABTest(campaignId || '');
  const { templates, isLoading: isLoadingTemplates } = useTemplates({ page_size: 100 });
  const { tags, isLoading: isLoadingTags } = useTags();

  // Load campaign data in edit mode
  useEffect(() => {
    if (campaign) {
      setName(campaign.name || '');
      setSubject(campaign.subject || '');
      setPreheaderText(campaign.preheader_text || '');
      setSenderName(campaign.sender_name || '');
      setSenderEmail(campaign.sender_email || '');
      setReplyToEmail(campaign.reply_to_email || '');
      setSelectedTemplateId(campaign.template_data?.id || campaign.template || null);
      setRecipientType(campaign.recipient_type || 'all_subscribed');
      setSelectedTagIds(
        campaign.recipient_tags_detail?.map((t) => t.id) || []
      );
      if (campaign.scheduled_at) {
        setScheduledAt(campaign.scheduled_at.slice(0, 16));
      }
      // Load AB test if it exists
      if (campaign.ab_test && campaign.ab_test.status === 'draft') {
        setAbEnabled(true);
        const ab = campaign.ab_test;
        const vb = ab.variants.find((v) => v.variant === 'b');
        setAbConfig({
          test_type: ab.test_type,
          test_percentage: ab.test_percentage,
          winner_criteria: ab.winner_criteria,
          winner_selection: ab.winner_selection,
          test_duration_hours: ab.test_duration_hours,
          variant_b_subject: vb?.subject ?? '',
          variant_b_sender_name: vb?.sender_name ?? '',
          variant_b_template: vb?.template ?? null,
        });
      }
    }
  }, [campaign]);

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  const getFormData = (): CreateCampaignData => ({
    name,
    subject,
    preheader_text: preheaderText,
    sender_name: senderName,
    sender_email: senderEmail,
    reply_to_email: replyToEmail || undefined,
    template: selectedTemplateId || undefined,
    recipient_type: recipientType,
    recipient_tag_ids: recipientType === 'by_tags' ? selectedTagIds : undefined,
    scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
  });

  const saveDraft = async () => {
    try {
      if (campaignId) {
        await updateCampaign(campaignId, getFormData());
      } else {
        const created = await createCampaign(getFormData());
        setCampaignId(created.id);
      }
      navigate('/campaigns');
    } catch {
      // Error handled by hook
    }
  };

  const handleSendNow = async () => {
    try {
      // Save first
      if (campaignId) {
        await updateCampaign(campaignId, getFormData());
      } else {
        const created = await createCampaign(getFormData());
        setCampaignId(created.id);
        await sendCampaign(created.id, { send_now: true });
        navigate('/campaigns');
        return;
      }
      await sendCampaign(campaignId, { send_now: true });
      navigate('/campaigns');
    } catch {
      // Error handled by hook
    }
  };

  const handleSchedule = async () => {
    if (!scheduledAt) {
      toast.error('Please select a date and time for scheduling.');
      return;
    }
    try {
      if (campaignId) {
        await updateCampaign(campaignId, getFormData());
      } else {
        const created = await createCampaign(getFormData());
        setCampaignId(created.id);
        await sendCampaign(created.id, {
          send_now: false,
          scheduled_at: new Date(scheduledAt).toISOString(),
        });
        navigate('/campaigns');
        return;
      }
      await sendCampaign(campaignId, {
        send_now: false,
        scheduled_at: new Date(scheduledAt).toISOString(),
      });
      navigate('/campaigns');
    } catch {
      // Error handled by hook
    }
  };

  const handleTestEmail = async (emails: string[]) => {
    if (!campaignId) {
      toast.error('Please save the campaign first.');
      return;
    }
    await sendTestEmail(campaignId, { test_emails: emails });
  };

  // Validation per step
  const canProceed = (step: number): boolean => {
    switch (step) {
      case 1:
        return (
          !!name.trim() &&
          !!subject.trim() &&
          !!senderName.trim() &&
          !!senderEmail.trim()
        );
      case 2:
        return true; // Template is optional
      case 3:
        return recipientType === 'all_subscribed' || selectedTagIds.length > 0;
      default:
        return true;
    }
  };

  const goNext = async () => {
    if (!canProceed(currentStep)) {
      toast.error('Please fill in the required fields.');
      return;
    }
    // Auto-save when advancing from step 1
    let savedId = campaignId;
    if (currentStep === 1 && !campaignId) {
      try {
        const created = await createCampaign(getFormData());
        setCampaignId(created.id);
        savedId = created.id;
      } catch {
        return;
      }
    } else if (campaignId) {
      try {
        await updateCampaign(campaignId, getFormData());
      } catch {
        return;
      }
    }
    // Save or remove AB test config when leaving step 1
    if (currentStep === 1 && savedId) {
      try {
        if (abEnabled) {
          await saveABTest(abConfig);
        } else if (campaign?.ab_test) {
          deleteABTest();
        }
      } catch {
        return;
      }
    }
    setCurrentStep((s) => Math.min(s + 1, 4));
  };

  const goBack = () => {
    setCurrentStep((s) => Math.max(s - 1, 1));
  };

  if (isEditMode && isLoadingCampaign) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/campaigns')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">
            {isEditMode ? 'Edit Campaign' : 'Create Campaign'}
          </h1>
          {campaignId && (
            <p className="text-sm text-muted-foreground">
              Auto-saved as draft
            </p>
          )}
        </div>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          const isActive = currentStep === step.id;
          const isComplete = currentStep > step.id;
          return (
            <div key={step.id} className="flex items-center">
              <button
                onClick={() => {
                  if (isComplete || isActive) setCurrentStep(step.id);
                }}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive && 'bg-primary text-primary-foreground',
                  isComplete && 'bg-primary/10 text-primary cursor-pointer',
                  !isActive && !isComplete && 'text-muted-foreground'
                )}
              >
                {isComplete ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
                {step.label}
              </button>
              {index < STEPS.length - 1 && (
                <div className="w-8 h-px bg-border mx-1" />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <div className="min-h-[400px]">
        {/* Step 1: Settings */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <Card className="p-6 space-y-4">
              <h2 className="text-lg font-semibold">Campaign Settings</h2>
              <div className="grid gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Campaign Name *</Label>
                  <Input
                    id="name"
                    placeholder="e.g. Monthly Newsletter - February"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="subject">Email Subject Line *</Label>
                  <Input
                    id="subject"
                    placeholder="e.g. Your February Newsletter is here!"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="preheader">Preheader Text</Label>
                  <Input
                    id="preheader"
                    placeholder="Preview text shown in inbox"
                    value={preheaderText}
                    onChange={(e) => setPreheaderText(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    This text appears after the subject line in most email clients
                  </p>
                </div>
              </div>
            </Card>
            <Card className="p-6 space-y-4">
              <h2 className="text-lg font-semibold">Sender Information</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="sender-name">Sender Name *</Label>
                  <Input
                    id="sender-name"
                    placeholder="e.g. Acme Marketing"
                    value={senderName}
                    onChange={(e) => setSenderName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sender-email">Sender Email *</Label>
                  <Input
                    id="sender-email"
                    type="email"
                    placeholder="e.g. marketing@acme.com"
                    value={senderEmail}
                    onChange={(e) => setSenderEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="reply-to">Reply-To Email (optional)</Label>
                  <Input
                    id="reply-to"
                    type="email"
                    placeholder="e.g. support@acme.com"
                    value={replyToEmail}
                    onChange={(e) => setReplyToEmail(e.target.value)}
                  />
                </div>
              </div>
            </Card>

            {/* A/B Test toggle */}
            <Card className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FlaskConical className="h-5 w-5 text-primary" />
                  <div>
                    <p className="font-semibold">A/B Testing</p>
                    <p className="text-sm text-muted-foreground">
                      Send two variants to a portion of your audience and send the winner to the rest
                    </p>
                  </div>
                </div>
                <Switch
                  checked={abEnabled}
                  onCheckedChange={setAbEnabled}
                />
              </div>

              {abEnabled && (
                <ABTestConfigPanel
                  config={abConfig}
                  onChange={setAbConfig}
                  onRemove={() => setAbEnabled(false)}
                  campaignSubject={subject}
                  campaignSenderName={senderName}
                  templates={templates}
                />
              )}
            </Card>
          </div>
        )}

        {/* Step 2: Template Selection */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Select a Template</h2>
              {isLoadingTemplates ? (
                <div className="flex justify-center items-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : templates.length === 0 ? (
                <div className="text-center py-8">
                  <Mail className="h-12 w-12 text-subtle-foreground mx-auto mb-3" />
                  <p className="text-muted-foreground">No templates available.</p>
                  <Button
                    variant="outline"
                    className="mt-3"
                    onClick={() => navigate('/templates/new')}
                  >
                    Create a Template
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {templates.map((template) => (
                    <Card
                      key={template.id}
                      className={cn(
                        'cursor-pointer overflow-hidden transition-all hover:shadow-md',
                        selectedTemplateId === template.id &&
                          'ring-2 ring-primary'
                      )}
                      onClick={() => setSelectedTemplateId(template.id)}
                    >
                      <div className="h-32 bg-secondary flex items-center justify-center border-b">
                        {template.thumbnail_url ? (
                          <img
                            src={template.thumbnail_url}
                            alt={template.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <Mail className="h-10 w-10 text-subtle-foreground" />
                        )}
                      </div>
                      <div className="p-3">
                        <div className="flex items-center justify-between">
                          <h3 className="font-medium text-sm truncate">
                            {template.name}
                          </h3>
                          {selectedTemplateId === template.id && (
                            <Check className="h-4 w-4 text-primary shrink-0" />
                          )}
                        </div>
                        <Badge variant="secondary" className="mt-1 text-xs">
                          {template.category}
                        </Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* Step 3: Recipients */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <Card className="p-6 space-y-6">
              <h2 className="text-lg font-semibold">Select Recipients</h2>

              <div className="space-y-4">
                <label
                  className={cn(
                    'flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors',
                    recipientType === 'all_subscribed' &&
                      'border-primary bg-primary/5'
                  )}
                >
                  <input
                    type="radio"
                    name="recipientType"
                    value="all_subscribed"
                    checked={recipientType === 'all_subscribed'}
                    onChange={() => setRecipientType('all_subscribed')}
                    className="mt-0.5"
                  />
                  <div>
                    <div className="font-medium">All Subscribed Contacts</div>
                    <p className="text-sm text-muted-foreground">
                      Send to all contacts who are subscribed and have not bounced
                    </p>
                  </div>
                </label>

                <label
                  className={cn(
                    'flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors',
                    recipientType === 'by_tags' &&
                      'border-primary bg-primary/5'
                  )}
                >
                  <input
                    type="radio"
                    name="recipientType"
                    value="by_tags"
                    checked={recipientType === 'by_tags'}
                    onChange={() => setRecipientType('by_tags')}
                    className="mt-0.5"
                  />
                  <div>
                    <div className="font-medium">Contacts with Specific Tags</div>
                    <p className="text-sm text-muted-foreground">
                      Only send to contacts that match selected tags
                    </p>
                  </div>
                </label>
              </div>

              {recipientType === 'by_tags' && (
                <div className="space-y-3 pl-7">
                  <Label>Select Tags</Label>
                  {isLoadingTags ? (
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
                  ) : tags.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No tags available. Create tags in the Contacts section.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-60 overflow-auto">
                      {tags.map((tag) => (
                        <label
                          key={tag.id}
                          className="flex items-center gap-2 cursor-pointer"
                        >
                          <Checkbox
                            checked={selectedTagIds.includes(tag.id)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setSelectedTagIds([...selectedTagIds, tag.id]);
                              } else {
                                setSelectedTagIds(
                                  selectedTagIds.filter((id) => id !== tag.id)
                                );
                              }
                            }}
                          />
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-xs',
                              `border-${tag.color}-300 text-${tag.color}-700`
                            )}
                          >
                            {tag.name}
                          </Badge>
                        </label>
                      ))}
                    </div>
                  )}
                  {selectedTagIds.length > 0 && (
                    <p className="text-sm text-muted-foreground">
                      {selectedTagIds.length} tag(s) selected
                    </p>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* Step 4: Review & Send */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <Card className="p-6 space-y-4">
              <h2 className="text-lg font-semibold">Review Campaign</h2>

              <div className="grid gap-4 text-sm">
                <div className="grid grid-cols-3 gap-2 border-b pb-3">
                  <span className="text-muted-foreground">Campaign Name</span>
                  <span className="col-span-2 font-medium">{name || '(Not set)'}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 border-b pb-3">
                  <span className="text-muted-foreground">Subject</span>
                  <span className="col-span-2">{subject || '(Not set)'}</span>
                </div>
                {preheaderText && (
                  <div className="grid grid-cols-3 gap-2 border-b pb-3">
                    <span className="text-muted-foreground">Preheader</span>
                    <span className="col-span-2">{preheaderText}</span>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 border-b pb-3">
                  <span className="text-muted-foreground">Sender</span>
                  <span className="col-span-2">
                    {senderName && senderEmail
                      ? `${senderName} <${senderEmail}>`
                      : '(Not set)'}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 border-b pb-3">
                  <span className="text-muted-foreground">Template</span>
                  <span className="col-span-2">
                    {selectedTemplate?.name || '(No template)'}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 border-b pb-3">
                  <span className="text-muted-foreground">Recipients</span>
                  <span className="col-span-2">
                    {recipientType === 'all_subscribed'
                      ? 'All subscribed contacts'
                      : `Contacts with tags: ${
                          tags
                            .filter((t) => selectedTagIds.includes(t.id))
                            .map((t) => t.name)
                            .join(', ') || '(None)'
                        }`}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 pb-2">
                  <span className="text-muted-foreground">A/B Test</span>
                  <span className="col-span-2">
                    {campaign?.ab_test
                      ? `Enabled — ${campaign.ab_test.test_percentage}% split, testing ${campaign.ab_test.test_type.replace('_', ' ')}`
                      : 'Not configured'}
                  </span>
                </div>
              </div>
            </Card>

            {/* Actions */}
            <Card className="p-6 space-y-4">
              <h2 className="text-lg font-semibold">Send Options</h2>

              <div className="flex flex-wrap gap-3">
                {campaignId && (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => setPreviewOpen(true)}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      Preview
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setTestEmailOpen(true)}
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Send Test Email
                    </Button>
                  </>
                )}
              </div>

              <div className="border-t pt-4 space-y-4">
                <div className="flex items-end gap-3">
                  <div className="space-y-2 flex-1">
                    <Label htmlFor="schedule-at">Schedule for</Label>
                    <Input
                      id="schedule-at"
                      type="datetime-local"
                      value={scheduledAt}
                      onChange={(e) => setScheduledAt(e.target.value)}
                    />
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleSchedule}
                    disabled={!scheduledAt || isSending}
                  >
                    {isSending ? 'Scheduling...' : 'Schedule'}
                  </Button>
                </div>

                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={saveDraft}
                    disabled={isCreating || isUpdating}
                  >
                    Save as Draft
                  </Button>
                  <Button
                    onClick={handleSendNow}
                    disabled={isSending}
                  >
                    <Send className="h-4 w-4 mr-2" />
                    {isSending ? 'Sending...' : 'Send Now'}
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4 border-t">
        <Button variant="outline" onClick={goBack} disabled={currentStep === 1}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        {currentStep < 4 ? (
          <Button onClick={goNext} disabled={!canProceed(currentStep) || isCreating || isUpdating || isSavingAB}>
            Next
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        ) : (
          <Button variant="outline" onClick={() => navigate('/campaigns')}>
            Back to Campaigns
          </Button>
        )}
      </div>

      {/* Dialogs */}
      {campaignId && (
        <>
          <CampaignPreviewDialog
            campaignId={campaignId}
            open={previewOpen}
            onOpenChange={setPreviewOpen}
          />
          <TestEmailDialog
            open={testEmailOpen}
            onOpenChange={setTestEmailOpen}
            onSend={(emails) => handleTestEmail(emails)}
            isSending={isSendingTest}
          />
        </>
      )}
    </div>
  );
};
