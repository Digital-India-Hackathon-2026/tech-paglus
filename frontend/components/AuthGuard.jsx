'use client';

import { Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';

// Wrap any page's content with <AuthGuard> to require a logged-in session.
// Shows a small loading state while the token is verified, then redirects
// to /login if there is no valid session.
export default function AuthGuard({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="text-sm">Checking your session…</p>
        </div>
      </div>
    );
  }

  if (!user) {
    // useAuth already triggered a redirect to /login; render nothing meanwhile.
    return null;
  }

  return children;
}
