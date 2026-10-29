import { useEffect, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { Button } from '@/components/ui/button';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { ArrowRight, CheckCircle2, Loader2, XCircle } from 'lucide-react';

export const VerifyEmailPage = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);

  const verifyMutation = useMutation({
    mutationFn: authApi.verifyEmail,
    onSuccess: () => {
      // Keep the signed-in session in step, or the profile goes on claiming
      // the address is unconfirmed until the next full reload.
      if (user) updateUser({ ...user, is_email_verified: true });
    },
  });

  const resendMutation = useMutation({ mutationFn: authApi.resendVerification });

  // React runs effects twice in StrictMode, and a verification token is spent
  // on first use: without this guard the second call reports the link as
  // already used and the reader sees a failure for a confirmation that worked.
  const attempted = useRef(false);
  const { mutate: verify } = verifyMutation;
  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;
    verify(token);
  }, [token, verify]);

  if (!token) {
    return (
      <AuthLayout
        title="That link is incomplete"
        description="The confirmation link was missing its token"
      >
        <p className="text-sm text-muted-foreground">
          Mail clients sometimes break long links across lines. Open the link
          from the email again, or sign in and request a new one.
        </p>
        <Link
          to="/login"
          className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-primary"
        >
          Go to sign in <ArrowRight className="h-4 w-4" />
        </Link>
      </AuthLayout>
    );
  }

  if (verifyMutation.isPending || verifyMutation.isIdle) {
    return (
      <AuthLayout title="Confirming your address" description="One moment">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Checking the link...
        </div>
      </AuthLayout>
    );
  }

  if (verifyMutation.isSuccess) {
    return (
      <AuthLayout
        title="Address confirmed"
        description="You can now be reached about your account"
      >
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-5 w-5 text-[hsl(var(--success,142_71%_45%))]" />
          <p className="text-sm text-muted-foreground">
            Thanks. We can now reach you about password resets, billing and any
            warning that your sending has been paused.
          </p>
        </div>
        <Button asChild className="mt-6 w-full">
          <Link to={user ? '/dashboard' : '/login'}>
            {user ? 'Go to dashboard' : 'Sign in'}
          </Link>
        </Button>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="That link did not work"
      description="It may have expired or already been used"
    >
      <div className="flex items-start gap-3">
        <XCircle className="mt-0.5 h-5 w-5 text-destructive" />
        <p className="text-sm text-muted-foreground">
          Confirmation links expire, and each one can only be used once. Sign in
          and send yourself a fresh link.
        </p>
      </div>

      {user ? (
        <Button
          className="mt-6 w-full"
          onClick={() => resendMutation.mutate()}
          disabled={resendMutation.isPending || resendMutation.isSuccess}
        >
          {resendMutation.isSuccess
            ? 'Sent — check your inbox'
            : resendMutation.isPending
              ? 'Sending...'
              : 'Send me a new link'}
        </Button>
      ) : (
        <Button asChild className="mt-6 w-full">
          <Link to="/login">Sign in</Link>
        </Button>
      )}

      {resendMutation.isError && (
        <p className="mt-3 text-sm text-destructive">
          {(resendMutation.error as any)?.message ||
            'The confirmation email could not be sent. Try again shortly.'}
        </p>
      )}
    </AuthLayout>
  );
};

export default VerifyEmailPage;
