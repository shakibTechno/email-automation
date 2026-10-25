import logoUrl from '@/assets/logo.png';

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
        <div className="mb-5 flex justify-center">
          <img
            src={logoUrl}
            alt="MailFlow"
            width={44}
            height={44}
            className="h-11 w-11 object-contain"
          />
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
