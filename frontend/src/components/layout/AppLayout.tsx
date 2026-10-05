import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

/**
 * The shell is a padded ground with two floating panels rather than full-bleed
 * columns — the gap between sidebar and content is what lets the lime wash on
 * the ground show through, which is the signature of the design.
 */
export const AppLayout = () => {
  return (
    <div className="app-ground min-h-screen p-3.5">
      <div className="flex w-full flex-col items-stretch gap-3.5 lg:flex-row lg:items-start">
        <Sidebar />

        <div className="flex min-w-0 flex-1 flex-col gap-3.5">
          <Header />
          <main className="min-w-0">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};
