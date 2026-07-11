'use client';
import { memo, use, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Sprout,
  Droplets,
  Sun,
  Bug,
  Wheat,
  Layers,
  PartyPopper,
  X,
} from 'lucide-react';
import { getCropStages, getStorageKey } from '@/lib/crop_stages';
import AuthGuard from '@/components/AuthGuard';

const STAGE_ICONS = { seed: Sprout, landprep: Layers, water: Droplets, nutrition: Sun, pest: Bug, harvest: Wheat };

// How long we wait after the last checklist item is ticked before
// automatically moving on to the next stage. Gives the person a moment to
// see the "stage complete" state before the page advances.
const AUTO_ADVANCE_DELAY_MS = 1400;

function getSessionId() {
  if (typeof window === 'undefined') return 'srv';
  return localStorage.getItem('agri_session') || 'default';
}

const StepRow = memo(function StepRow({ index, text, checked, onToggle }) {
  const handleToggle = () => onToggle(index);
  return (
    <li
      onClick={(e) => {
        if (e.target.closest('[data-check-btn]')) return;
        handleToggle();
      }}
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
      className={`group flex items-start gap-3 rounded-xl border p-3.5 cursor-pointer transition-all duration-200 animate-in fade-in slide-in-from-bottom-1 fill-mode-backwards ${
        checked
          ? 'border-emerald-300 bg-emerald-50/70'
          : 'border-slate-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/30'
      }`}
    >
      <button
        type="button"
        data-check-btn
        onClick={handleToggle}
        aria-pressed={checked}
        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200 ${
          checked
            ? 'border-emerald-600 bg-emerald-600 scale-100'
            : 'border-slate-300 bg-white group-hover:border-emerald-400'
        }`}
      >
        <Check
          className={`h-3.5 w-3.5 text-white transition-all duration-200 ${checked ? 'scale-100 opacity-100' : 'scale-50 opacity-0'}`}
          strokeWidth={3}
        />
      </button>
      <span
        className={`text-sm leading-snug transition-colors duration-200 ${
          checked ? 'text-emerald-900/70 line-through decoration-emerald-400 decoration-2' : 'text-slate-800'
        }`}
      >
        {text}
      </span>
    </li>
  );
});

function CropPlan({ cropId }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Which wizard step on the home page to return to when this plan is
  // exited (e.g. 4 = Plan & Schemes / Mandi Prices). Falls back to the
  // home page's default (step 0) if not provided.
  const returnStep = searchParams.get('returnStep');
  const goHome = () => router.push(returnStep ? `/?step=${returnStep}` : '/');
  const plan = useMemo(() => getCropStages(cropId), [cropId]);
  const [sessionId, setSessionId] = useState('default');
  const [stageIndex, setStageIndex] = useState(0);
  const [completed, setCompleted] = useState({});
  const [autoAdvancing, setAutoAdvancing] = useState(false);
  const autoAdvanceTimer = useRef(null);
  const lastAutoAdvancedStage = useRef(-1);

  useEffect(() => {
    const sid = getSessionId();
    setSessionId(sid);
    try {
      const saved = JSON.parse(localStorage.getItem(getStorageKey(cropId, sid)) || '{}');
      setCompleted(saved.completed || {});
      if (typeof saved.stageIndex === 'number') setStageIndex(saved.stageIndex);
    } catch {}
  }, [cropId]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(getStorageKey(cropId, sessionId), JSON.stringify({ completed, stageIndex }));
  }, [completed, stageIndex, cropId, sessionId]);

  const stage = plan.stages[stageIndex];
  const totalSteps = plan.stages.reduce((n, s) => n + s.steps.length, 0);
  const doneSteps = Object.values(completed).filter(Boolean).length;
  const progressPct = totalSteps ? Math.round((doneSteps / totalSteps) * 100) : 0;
  const stageDone = stage.steps.every((_, i) => completed[`${stage.key}_${i}`]);
  const isLastStage = stageIndex === plan.stages.length - 1;
  const stageDoneCount = stage.steps.filter((_, i) => completed[`${stage.key}_${i}`]).length;

  const toggleStep = useCallback((i) => {
    const key = `${stage.key}_${i}`;
    setCompleted((c) => ({ ...c, [key]: !c[key] }));
  }, [stage.key]);

  function goNext() {
    cancelAutoAdvance();
    if (stageIndex < plan.stages.length - 1) setStageIndex(stageIndex + 1);
  }
  function goPrev() {
    cancelAutoAdvance();
    if (stageIndex > 0) setStageIndex(stageIndex - 1);
  }

  function cancelAutoAdvance() {
    if (autoAdvanceTimer.current) {
      clearTimeout(autoAdvanceTimer.current);
      autoAdvanceTimer.current = null;
    }
    setAutoAdvancing(false);
  }

  // Details filled in (checklist complete) -> automatically move to the next
  // stage instead of requiring a manual "Next" click. Only fires once per
  // stage so unchecking/rechecking an item doesn't re-trigger it.
  useEffect(() => {
    if (stageDone && !isLastStage && lastAutoAdvancedStage.current !== stageIndex) {
      lastAutoAdvancedStage.current = stageIndex;
      setAutoAdvancing(true);
      autoAdvanceTimer.current = setTimeout(() => {
        setStageIndex((idx) => Math.min(idx + 1, plan.stages.length - 1));
        setAutoAdvancing(false);
        autoAdvanceTimer.current = null;
      }, AUTO_ADVANCE_DELAY_MS);
    }
    if (!stageDone) {
      lastAutoAdvancedStage.current = -1;
    }
    return () => {
      if (autoAdvanceTimer.current) {
        clearTimeout(autoAdvanceTimer.current);
        autoAdvanceTimer.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageDone, stageIndex, isLastStage]);

  useEffect(() => {
    // reset the "already auto-advanced" guard whenever the person changes stage manually
    setAutoAdvancing(false);
  }, [stageIndex]);

  const nextStageTitle = !isLastStage ? plan.stages[stageIndex + 1].title : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-lime-50 to-amber-50">
      <header className="sticky top-0 z-40 backdrop-blur bg-white/80 border-b border-emerald-100">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={() => router.push('/')} className="flex items-center gap-2 text-emerald-800 hover:text-emerald-950 text-sm font-medium">
            <ArrowLeft className="h-4 w-4" /> Back to dashboard
          </button>
          <div className="text-right">
            <h1 className="font-bold text-emerald-950 leading-tight">{plan.name} — Production Plan</h1>
            <p className="text-xs text-emerald-700/70">{plan.duration} · {plan.season}</p>
          </div>
        </div>
        <div className="h-1.5 bg-emerald-50">
          <div className="h-full bg-emerald-600 transition-all duration-500" style={{ width: `${progressPct}%` }} />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-3xl">
        {/* Stage rail */}
        <div className="flex items-center gap-1 overflow-x-auto pb-4 mb-6 -mx-1 px-1">
          {plan.stages.map((s, i) => {
            const Icon = STAGE_ICONS[s.key] || Sprout;
            const done = s.steps.every((_, si) => completed[`${s.key}_${si}`]);
            const active = i === stageIndex;
            return (
              <button
                key={s.key}
                onClick={() => { cancelAutoAdvance(); setStageIndex(i); }}
                className={`flex flex-col items-center gap-1 shrink-0 px-3 py-2 rounded-xl border-2 transition min-w-[92px]
                  ${active ? 'border-emerald-500 bg-emerald-50' : done ? 'border-emerald-200 bg-white' : 'border-slate-200 bg-white hover:border-emerald-300'}`}
              >
                <div className={`h-9 w-9 rounded-full grid place-items-center transition-colors ${done ? 'bg-emerald-600 text-white' : active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                  {done ? <CheckCircle2 className="h-5 w-5" /> : <Icon className="h-4 w-4" />}
                </div>
                <span className={`text-[11px] font-medium text-center leading-tight ${active ? 'text-emerald-900' : 'text-slate-600'}`}>{s.title}</span>
              </button>
            );
          })}
        </div>

        {/* Progress summary */}
        <div className="flex items-center justify-between mb-4">
          <Badge variant="outline" className="text-emerald-800 border-emerald-300">Step {stageIndex + 1} of {plan.stages.length}</Badge>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span>{doneSteps}/{totalSteps} tasks done</span>
            <div className="h-1.5 w-24 rounded-full bg-slate-200 overflow-hidden">
              <div className="h-full bg-emerald-600 transition-all duration-500" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        </div>

        {/* Current stage card */}
        <div className="rounded-2xl border border-emerald-200 bg-white shadow-sm p-6">
          <div className="flex items-start justify-between gap-4 mb-1">
            <h2 className="text-xl font-bold text-emerald-950">{stage.title}</h2>
            <Badge className={stageDone ? 'bg-emerald-600' : 'bg-slate-100 text-slate-600 border border-slate-200'} variant={stageDone ? 'default' : 'outline'}>
              {stageDoneCount}/{stage.steps.length}
            </Badge>
          </div>
          <p className="text-sm text-slate-600 mb-5">{stage.summary}</p>

          <ul className="space-y-2.5">
            {stage.steps.map((text, i) => {
              const key = `${stage.key}_${i}`;
              return <StepRow key={key} index={i} text={text} checked={!!completed[key]} onToggle={toggleStep} />;
            })}
          </ul>

          {/* Auto-advance banner: replaces having to press "Next" once every
              task in a stage is checked off. */}
          {autoAdvancing && !isLastStage && (
            <div className="mt-5 flex items-center justify-between gap-3 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 animate-in fade-in slide-in-from-bottom-1">
              <div className="flex items-center gap-2 text-sm text-emerald-900">
                <PartyPopper className="h-4 w-4 text-emerald-700 shrink-0" />
                <span>Stage complete! Moving on to <b>{nextStageTitle}</b>…</span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button size="sm" variant="ghost" className="h-8 px-2 text-emerald-700 hover:text-emerald-900" onClick={cancelAutoAdvance}>
                  <X className="h-3.5 w-3.5 mr-1" /> Stay
                </Button>
                <Button size="sm" className="h-8 px-3 bg-emerald-600 hover:bg-emerald-700" onClick={goNext}>
                  Go now <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </div>
            </div>
          )}
          {stageDone && isLastStage && (
            <div className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              <PartyPopper className="h-4 w-4 text-emerald-700 shrink-0" />
              All stages complete — this crop plan is finished. 🎉
            </div>
          )}
        </div>

        {/* Previous / Next navigation — Previous always available; Next
            happens automatically once a stage's checklist is complete, but
            stays here too in case someone wants to move on manually. */}
        <div className="flex items-center justify-between mt-6">
          <Button variant="outline" onClick={goPrev} disabled={stageIndex === 0} className="h-11 px-5">
            <ArrowLeft className="h-4 w-4 mr-2" /> Previous
          </Button>
          {!isLastStage ? (
            <Button variant="ghost" onClick={goNext} className="h-11 px-5 text-emerald-700 hover:text-emerald-900 hover:bg-emerald-50">
              Skip to next <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button onClick={goHome} className="h-11 px-5 bg-emerald-600 hover:bg-emerald-700">
              Finish & return <CheckCircle2 className="h-4 w-4 ml-2" />
            </Button>
          )}
        </div>
      </main>
    </div>
  );
}

export default function CropPlanPage({ params }) {
  const { id } = use(params);
  return (
    <AuthGuard>
      <CropPlan cropId={id} />
    </AuthGuard>
  );
}
