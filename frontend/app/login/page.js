'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Sprout, Loader2, Eye, EyeOff, Phone } from 'lucide-react';
import { toast, Toaster } from 'sonner';
import { saveSession, getToken } from '@/lib/auth';
import { LOGIN } from '@/lib/constants/testIds/auth';
import { useLanguage } from '@/lib/language';

const SUPPORT_TEL = 'tel:1800000000';

export default function LoginPage() {
  const router = useRouter();
  const { tr } = useLanguage();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Already logged in? Skip straight to the app.
  useEffect(() => {
    if (getToken()) router.replace('/');
  }, [router]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!phone.trim() || !password) {
      setError(tr('errFillBoth'));
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phone.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || tr('errGeneric'));
      }
      saveSession(data.token, data.user);
      toast.success(`${tr('welcome')}, ${data.user.name.split(' ')[0]}!`);
      router.replace('/');
    } catch (err) {
      setError(err.message || tr('errGeneric'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-secondary px-4 py-10">
      <Toaster richColors position="top-center" />

      <Link
        href="/language"
        className="mb-6 flex items-center gap-1.5 rounded-full bg-white px-4 py-2 text-sm font-semibold text-primary shadow-sm"
      >
        🌐 {tr('changeLanguage')}
      </Link>

      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md">
            <Sprout className="h-9 w-9" />
          </div>
          <h1 className="text-2xl font-extrabold text-primary">AgriSarthi</h1>
          <p className="text-base text-muted-foreground">{tr('tagline')}</p>
        </div>

        <div className="rounded-3xl bg-card p-6 shadow-lg">
          <h2 className="text-xl font-bold text-foreground">{tr('loginTitle')}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{tr('loginSub')}</p>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="phone" className="text-base font-semibold text-foreground">
                {tr('phoneNumber')}
              </label>
              <input
                id="phone"
                type="tel"
                inputMode="tel"
                autoComplete="username"
                placeholder="98765 43210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                data-testid={LOGIN.phoneInput}
                className="w-full rounded-xl border-2 border-border bg-white px-4 py-3 text-lg outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-base font-semibold text-foreground">
                {tr('passwordLabel')}
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid={LOGIN.passwordInput}
                  className="w-full rounded-xl border-2 border-border bg-white px-4 py-3 text-lg outline-none focus:border-primary"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 flex items-center px-4 text-muted-foreground"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {error && <p className="text-sm font-medium text-destructive">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              data-testid={LOGIN.submitButton}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-4 text-lg font-bold text-primary-foreground shadow-md disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
              {loading ? tr('loginLoading') : tr('loginButton')}
            </button>
          </form>

          <p className="mt-5 text-center text-base text-muted-foreground">
            {tr('noAccount')}{' '}
            <Link href="/register" className="font-bold text-primary underline" data-testid={LOGIN.registerLink}>
              {tr('createAccount')}
            </Link>
          </p>
        </div>

        <a
          href={SUPPORT_TEL}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-primary bg-white py-3 text-base font-bold text-primary"
        >
          <Phone className="h-5 w-5" /> {tr('needHelp')} — {tr('callUsShort')}
        </a>
      </div>
    </div>
  );
}
