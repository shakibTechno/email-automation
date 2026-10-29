import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authApi } from '@/api/auth';
import { ArrowLeft } from 'lucide-react';

const resetSchema = z
  .object({
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    new_password_confirm: z.string(),
  })
  .refine((data) => data.new_password === data.new_password_confirm, {
    message: "Passwords don't match",
    path: ['new_password_confirm'],
  });

type ResetFormData = z.infer<typeof resetSchema>;

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetFormData>({ resolver: zodResolver(resetSchema) });

  const resetMutation = useMutation({
    mutationFn: authApi.resetPassword,
    onSuccess: () => {
      toast.success('Password updated. Sign in with your new password.');
      navigate('/login');
    },
    // Without this the form looks like an unwired button: the request fails,
    // nothing moves, and the reader is left guessing whether they mistyped.
    onError: (error: any) => {
      toast.error(
        error?.message || 'This link is invalid or has expired. Request a new one.',
      );
    },
  });

  // A reset link with no token is a link someone truncated when copying it out
  // of a mail client, which is common enough to answer properly.
  if (!token) {
    return (
      <AuthLayout
        title="That link is incomplete"
        description="The reset link was missing its token"
      >
        <p className="text-sm text-muted-foreground">
          Mail clients sometimes break long links across lines. Open the link
          from the email again, or request a new one.
        </p>
        <Link
          to="/forgot-password"
          className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-primary"
        >
          <ArrowLeft className="h-4 w-4" /> Request a new link
        </Link>
      </AuthLayout>
    );
  }

  const onSubmit = (data: ResetFormData) =>
    resetMutation.mutate({ token, ...data });

  return (
    <AuthLayout
      title="Choose a new password"
      description="This link can only be used once"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="new_password">New password</Label>
          <Input
            id="new_password"
            type="password"
            autoComplete="new-password"
            {...register('new_password')}
            disabled={resetMutation.isPending}
          />
          {errors.new_password && (
            <p className="text-sm text-destructive">{errors.new_password.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="new_password_confirm">Confirm new password</Label>
          <Input
            id="new_password_confirm"
            type="password"
            autoComplete="new-password"
            {...register('new_password_confirm')}
            disabled={resetMutation.isPending}
          />
          {errors.new_password_confirm && (
            <p className="text-sm text-destructive">
              {errors.new_password_confirm.message}
            </p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={resetMutation.isPending}>
          {resetMutation.isPending ? 'Saving...' : 'Set new password'}
        </Button>

        <Link
          to="/login"
          className="inline-flex items-center gap-2 text-sm font-medium text-primary"
        >
          <ArrowLeft className="h-4 w-4" /> Back to sign in
        </Link>
      </form>
    </AuthLayout>
  );
};

export default ResetPasswordPage;
