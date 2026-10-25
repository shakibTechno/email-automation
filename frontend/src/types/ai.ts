export type AIProvider = 'anthropic' | 'openai' | 'google' | 'local';

export const aiProviderLabels: Record<AIProvider, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI',
  google: 'Google (Gemini)',
  local: 'Local server (llama.cpp / Ollama)',
};

export interface AIConfig {
  id: string;
  provider: AIProvider;
  /** Blank when the organization has not pinned one. */
  model: string;
  /** What the provider will actually be called with. */
  effective_model: string;
  /** Where a self-hosted server lives. Empty for hosted providers. */
  base_url: string;
  /** The key itself is never returned — only whether one is stored. */
  api_key_set: boolean;
  /** False for self-hosted providers, which are usually unauthenticated. */
  requires_api_key: boolean;
  is_enabled: boolean;
  /** Enabled *and* holding a key: generation can be attempted. */
  is_ready: boolean;
  last_validated_at: string | null;
  last_error: string;
  created_at: string;
  updated_at: string;
}

export interface UpdateAIConfigData {
  provider?: AIProvider;
  model?: string;
  base_url?: string;
  /** Omit or send blank to keep the stored key. */
  api_key?: string;
  is_enabled?: boolean;
}

export type GenerationStatus = 'queued' | 'running' | 'succeeded' | 'failed';

/** What a generation produces. Matches GenerationJob.KIND_CHOICES. */
export type GenerationKind = 'landing_page' | 'form' | 'email_template' | 'campaign';

export interface GenerationJob {
  id: string;
  kind: GenerationKind;
  status: GenerationStatus;
  prompt: string;
  audience: string;
  /** Id of whatever was produced, whichever kind it was. */
  result_id: string | null;
  landing_page: string | null;
  form: string | null;
  email_template: string | null;
  campaign: string | null;
  error_message: string;
  /** True when the sanitizer removed something from the model's output. */
  was_sanitized: boolean;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface GenerateRequest {
  prompt: string;
  audience?: string;
}
