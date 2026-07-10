'use client';

// Global language state for the whole app.
// The chosen language is saved to localStorage so every screen — including
// login/signup — renders in the farmer's language from that point on.

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { STRINGS, LANG_TAGS, t as translate } from './i18n';

const LANG_KEY = 'agri_lang';

// Native-script labels so a non-English-reading farmer can recognise their
// own language immediately, without needing to read English first.
export const LANGUAGES = [
  { code: 'hi', label: 'हिंदी', sub: 'Hindi' },
  { code: 'te', label: 'తెలుగు', sub: 'Telugu' },
  { code: 'en', label: 'English', sub: 'English' },
];

export function getStoredLanguage() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(LANG_KEY);
}

export function setStoredLanguage(code) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(LANG_KEY, code);
  window.dispatchEvent(new Event('agri-lang-change'));
}

const LanguageContext = createContext({
  lang: 'en',
  setLang: () => {},
  ready: false,
});

const PUBLIC_PATHS = ['/language'];

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState('en');
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const stored = getStoredLanguage();
    if (stored && STRINGS[stored]) {
      setLangState(stored);
    } else if (!PUBLIC_PATHS.includes(pathname)) {
      // First-ever visit: ask for a language before anything else,
      // including before login/signup.
      router.replace(`/language?next=${encodeURIComponent(pathname || '/')}`);
    }
    setReady(true);

    function onChange() {
      const next = getStoredLanguage();
      if (next && STRINGS[next]) setLangState(next);
    }
    window.addEventListener('agri-lang-change', onChange);
    return () => window.removeEventListener('agri-lang-change', onChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setLang = useCallback((code) => {
    if (!STRINGS[code]) return;
    setStoredLanguage(code);
    setLangState(code);
  }, []);

  return (
    <LanguageContext.Provider value={{ lang, setLang, ready, speechTag: LANG_TAGS[lang] || 'en-IN' }}>
      {children}
    </LanguageContext.Provider>
  );
}

// Convenience hook: const { lang, setLang, tr } = useLanguage();
export function useLanguage() {
  const ctx = useContext(LanguageContext);
  const tr = useCallback((key) => translate(ctx.lang, key), [ctx.lang]);
  return { ...ctx, tr };
}
