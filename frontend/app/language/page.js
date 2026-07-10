'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sprout, Check } from 'lucide-react';
import { LANGUAGES, useLanguage } from '@/lib/language';

function LanguagePickerInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { lang, setLang, tr } = useLanguage();
  const [selected, setSelected] = useState(lang || null);

  function confirm() {
    if (!selected) return;
    setLang(selected);
    const next = params.get('next') || '/login';
    router.replace(next);
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-secondary px-5 py-10">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md">
          <Sprout className="h-9 w-9" />
        </div>
        <h1 className="text-2xl font-extrabold text-primary">AgriSarthi</h1>
      </div>

      <div className="w-full max-w-sm rounded-3xl bg-card p-6 shadow-lg">
        <h2 className="text-center text-xl font-bold text-foreground">{tr('chooseLanguage')}</h2>
        <p className="mt-1 text-center text-sm text-muted-foreground">{tr('chooseLanguageSub')}</p>

        <div className="mt-6 flex flex-col gap-3">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => setSelected(l.code)}
              className={`flex items-center justify-between rounded-2xl border-2 px-5 py-4 text-left transition
                ${selected === l.code
                  ? 'border-primary bg-secondary'
                  : 'border-border bg-white hover:border-primary/40'}`}
            >
              <span>
                <span className="block text-2xl font-bold text-foreground">{l.label}</span>
                <span className="block text-sm text-muted-foreground">{l.sub}</span>
              </span>
              {selected === l.code && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Check className="h-5 w-5" />
                </span>
              )}
            </button>
          ))}
        </div>

        <button
          type="button"
          disabled={!selected}
          onClick={confirm}
          className="mt-7 w-full rounded-2xl bg-primary py-4 text-lg font-bold text-primary-foreground shadow-md disabled:opacity-40"
        >
          {selected ? LANGUAGES.find((l) => l.code === selected)?.label : ''}
          {selected ? ' — ' : ''}
          {selected
            ? (selected === 'hi' ? 'आगे बढ़ें' : selected === 'te' ? 'ముందుకు వెళ్ళండి' : 'Continue')
            : 'Choose a language / भाषा चुनें / భాష ఎంచుకోండి'}
        </button>
      </div>
    </div>
  );
}

export default function LanguagePage() {
  return (
    <Suspense fallback={null}>
      <LanguagePickerInner />
    </Suspense>
  );
}
