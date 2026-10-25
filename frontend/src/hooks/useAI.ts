import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { aiApi } from '@/api/ai';
import type {
  GenerateRequest,
  GenerationJob,
  GenerationKind,
  UpdateAIConfigData,
} from '@/types/ai';

const describeFailure = (error: any, fallback: string): string => {
  const data = error?.errors;
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const first = Object.values(data).flat()[0];
    if (typeof first === 'string') return first;
  }
  if (error?.message && !/status code/i.test(error.message)) return error.message;
  return fallback;
};

export const useAIConfig = () => {
  const query = useQuery({
    queryKey: ['ai-config'],
    queryFn: aiApi.getConfig,
    staleTime: 60 * 1000,
  });

  return {
    config: query.data,
    isLoading: query.isLoading,
    error: query.error,
  };
};

export const useUpdateAIConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpdateAIConfigData) => aiApi.updateConfig(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-config'] });
      toast.success('AI settings saved');
    },
    onError: (error: any) => {
      toast.error(describeFailure(error, 'Failed to save AI settings'));
    },
  });
};

export const useTestAIConnection = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: aiApi.testConnection,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['ai-config'] });
      toast.success(result.message || 'Connection successful');
    },
    onError: (error: any) => {
      // A rejected key is an answer, not a crash — the message from the
      // provider is the useful part, so surface it rather than a generic one.
      toast.error(describeFailure(error, 'Could not reach the provider'));
      queryClient.invalidateQueries({ queryKey: ['ai-config'] });
    },
  });
};

/** How long to wait between polls, and how long before giving up. */
const POLL_INTERVAL_MS = 2500;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

/**
 * Runs a generation of any kind and follows it to completion.
 *
 * Generation takes tens of seconds, so the request only queues a job; this
 * polls until it resolves. The timeout exists so a worker that never picks the
 * job up leaves the user with an explanation rather than a spinner.
 */
export const useGenerate = (kind: GenerationKind) => {
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startedAtRef = useRef(0);

  const stop = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    setIsPolling(false);
  };

  useEffect(() => stop, []);

  const poll = (jobId: string) => {
    timerRef.current = setTimeout(async () => {
      try {
        const next = await aiApi.getJob(jobId);
        setJob(next);

        if (next.status === 'succeeded' || next.status === 'failed') {
          stop();
          return;
        }
        if (Date.now() - startedAtRef.current > POLL_TIMEOUT_MS) {
          stop();
          setJob({
            ...next,
            status: 'failed',
            error_message:
              'Generation is taking longer than expected. Check that the background worker is running.',
          });
          return;
        }
        poll(jobId);
      } catch (error: any) {
        stop();
        setJob((current) =>
          current
            ? {
                ...current,
                status: 'failed',
                error_message: describeFailure(error, 'Lost track of the generation.'),
              }
            : current
        );
      }
    }, POLL_INTERVAL_MS);
  };

  const generate = async (payload: GenerateRequest) => {
    stop();
    setJob(null);
    try {
      const created = await aiApi.generate(kind, payload);
      setJob(created);
      setIsPolling(true);
      startedAtRef.current = Date.now();
      poll(created.id);
      return created;
    } catch (error: any) {
      const message = describeFailure(error, 'Could not start generation');
      toast.error(message);
      throw error;
    }
  };

  const reset = () => {
    stop();
    setJob(null);
  };

  return {
    generate,
    reset,
    job,
    isGenerating: isPolling || job?.status === 'queued' || job?.status === 'running',
  };
};
