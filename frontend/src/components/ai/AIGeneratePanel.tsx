import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { AlertTriangle, Loader2, Settings, Sparkles } from 'lucide-react';
import { useAIConfig, useGenerate } from '@/hooks/useAI';
import type { GenerationKind } from '@/types/ai';

interface AIGeneratePanelProps {
  /** What to build. Decides the copy as well as the endpoint. */
  kind: GenerationKind;
  /** Called with the id of whatever was produced, once generation succeeds. */
  onGenerated: (resultId: string) => void;
  onCancel: () => void;
}

/** Per-kind wording, so the panel reads like it belongs wherever it is used. */
const COPY: Record<GenerationKind, {
  action: string;
  question: string;
  placeholder: string;
  progress: string;
  note: string;
  examples: string[];
}> = {
  landing_page: {
    action: 'Generate page',
    question: 'What is this page for?',
    placeholder: 'Describe the offer, what the visitor gets, and what you want them to do.',
    progress: 'Writing your page…',
    note: "You'll get an editable draft, not a finished page — it opens in the builder so you can change anything. Add your lead capture form there; the draft marks where it belongs.",
    examples: [
      'A free trial signup page for a project management tool aimed at small agencies',
      'A webinar registration page about cutting email bounce rates, for B2B marketers',
      'An ebook download page for a guide to first-time home buying',
    ],
  },
  form: {
    action: 'Generate form',
    question: 'What should this form capture?',
    placeholder: 'Describe what you are offering and what you need to know about the person.',
    progress: 'Designing your form…',
    note: 'The form arrives inactive so you can review it before anyone can submit. Fields that match a contact field are mapped automatically, which is what turns a submission into a lead.',
    examples: [
      'A form to download a guide on reducing email bounce rates',
      'A demo request form for a logistics platform, qualifying by fleet size',
      'A newsletter signup asking only for an email address',
    ],
  },
  email_template: {
    action: 'Generate email',
    question: 'What is this email about?',
    placeholder: 'Describe the message, who it is for, and what you want them to do next.',
    progress: 'Writing your email…',
    note: 'You get an editable template — each heading, paragraph and button is a separate block you can restyle or drag in the editor. Add images there.',
    examples: [
      'A webinar invitation about cutting email bounce rates',
      'A welcome email for people who just started a free trial',
      'A re-engagement email for subscribers who have not opened in 90 days',
    ],
  },
  campaign: {
    action: 'Generate campaign',
    question: 'What do you want to send?',
    placeholder: 'Describe the message, who it is for, and what you want them to do next.',
    progress: 'Writing your campaign…',
    note: 'You get a draft campaign with its email written and attached. Choosing the audience and the send time is still yours.',
    examples: [
      'A product launch announcement for a new deliverability dashboard',
      'A last-chance reminder for a webinar happening on Thursday',
      'A monthly newsletter rounding up three new features',
    ],
  },
};

export const AIGeneratePanel = ({ kind, onGenerated, onCancel }: AIGeneratePanelProps) => {
  const { config, isLoading } = useAIConfig();
  const { generate, job, isGenerating, reset } = useGenerate(kind);
  const copy = COPY[kind];
  const [prompt, setPrompt] = useState('');
  const [audience, setAudience] = useState('');

  // Handing off is a side effect, so it belongs here rather than in the render
  // path where it would fire on every re-render.
  const generatedId = job?.status === 'succeeded' ? job.result_id : null;
  useEffect(() => {
    if (generatedId) onGenerated(generatedId);
  }, [generatedId, onGenerated]);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center py-16">
        <Loader2 className="h-5 w-5 animate-spin text-subtle-foreground" />
      </div>
    );
  }

  // Visible but inert rather than hidden: otherwise nobody discovers the
  // feature exists, and "why can't I see it" is a worse problem than "I need
  // to connect a provider first".
  if (!config?.is_ready) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-14 text-center">
        <Sparkles className="h-6 w-6 text-subtle-foreground" />
        <div>
          <h3 className="text-[14px] font-semibold">Connect an AI provider first</h3>
          <p className="mx-auto mt-1 max-w-sm text-[12.5px] text-muted-foreground">
            Add your own Anthropic, OpenAI or Google key in Settings and generation runs on
            your account — nothing is sent anywhere until you do.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to="/settings">
            <Settings className="h-3.5 w-3.5" /> Open Settings
          </Link>
        </Button>
      </div>
    );
  }

  if (job?.status === 'failed') {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-14 text-center">
        <AlertTriangle className="h-6 w-6 text-destructive" />
        <div>
          <h3 className="text-[14px] font-semibold">Generation failed</h3>
          <p className="mx-auto mt-1 max-w-md text-[12.5px] text-muted-foreground">
            {job.error_message || 'Something went wrong. Try again.'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={reset}>
          Try again
        </Button>
      </div>
    );
  }

  if (isGenerating) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-14 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand" />
        <div>
          <h3 className="text-[14px] font-semibold">{copy.progress}</h3>
          <p className="mx-auto mt-1 max-w-sm text-[12.5px] text-muted-foreground">
            This usually takes a minute or so on a local model. You can keep this open —
            it opens as soon as it's ready.
          </p>
        </div>
      </div>
    );
  }

  if (generatedId) {
    // The effect above is taking us to the builder; show the spinner rather
    // than flashing the empty form on the way out.
    return (
      <div className="flex flex-1 items-center justify-center py-16">
        <Loader2 className="h-5 w-5 animate-spin text-brand" />
      </div>
    );
  }

  const canSubmit = prompt.trim().length >= 10;

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
      <div className="space-y-1.5">
        <Label htmlFor="ai-prompt">{copy.question}</Label>
        <Textarea
          id="ai-prompt"
          rows={4}
          autoFocus
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={copy.placeholder}
        />
        <div className="flex flex-wrap gap-1.5 pt-1">
          {copy.examples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setPrompt(example)}
              className="rounded-md border bg-secondary/50 px-2 py-1 text-left text-[11.5px] text-muted-foreground transition-colors hover:text-foreground"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ai-audience">
          Audience <span className="text-subtle-foreground">(optional)</span>
        </Label>
        <Input
          id="ai-audience"
          value={audience}
          onChange={(e) => setAudience(e.target.value)}
          placeholder="e.g. operations managers at mid-size logistics firms"
        />
      </div>

      <p className="text-[12px] text-muted-foreground">{copy.note}</p>

      <div className="mt-auto flex justify-end gap-2 border-t pt-4">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          onClick={() =>
            generate({ prompt: prompt.trim(), audience: audience.trim() }).catch(() => {})
          }
          disabled={!canSubmit}
        >
          <Sparkles className="h-3.5 w-3.5" /> {copy.action}
        </Button>
      </div>
    </div>
  );
};
