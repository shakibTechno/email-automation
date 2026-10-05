import { Send } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  description?: string;
}

/**
 * Signed-out shell. No sidebar, no topbar — just the brand mark over the same
 * lime wash the app ground uses, so sign-in feels like the same product.
 */
export const AuthLayout = ({ children, title, description }: AuthLayoutProps) => {
  return (
    <div className="app-ground grid min-h-screen place-items-center px-4 py-7">
      <div className="w-full max-w-[400px]">
        <div className="mb-5 flex items-center justify-center gap-2.5">
          <span className="grid h-[30px] w-[30px] place-items-center rounded-lg bg-brand-fill text-brand-ink">
            <Send className="h-3.5 w-3.5" />
          </span>
          <b className="text-[17px] font-extrabold tracking-tight">Cadence</b>
        </div>

        <div className="rounded-2xl border bg-card p-6 shadow-card">
          <h2 className="mb-1.5 text-[21px] font-bold tracking-tight">{title}</h2>
          {description && (
            <p className="mb-5 text-[13px] text-muted-foreground">{description}</p>
          )}
          {children}
        </div>
      </div>
    </div>
  );
};
