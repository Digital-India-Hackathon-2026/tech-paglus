'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle, ArrowLeft, Bug, Camera, CheckCircle2, ChevronDown, ClipboardCheck,
  CloudRain, Cpu, Download, FileImage, History, ImageIcon, Languages, Leaf, Loader2,
  MapPin, Microscope, RefreshCw, ShieldCheck, Sparkles, Sprout, ThumbsDown, ThumbsUp,
  Upload, Volume2, X, ZoomIn,
} from 'lucide-react';
import AuthGuard from '@/components/AuthGuard';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { useLanguage } from '@/lib/language';

const ACCEPTED = 'image/jpeg,image/png,image/webp,image/heic,image/heif';
const STAGES = ['Checking image quality', 'Detecting crop and plant part', 'Scanning disease and pests', 'Localizing damage', 'Preparing safe advice'];

function getOwnerId() {
  if (typeof window === 'undefined') return 'browser-session';
  let value = localStorage.getItem('agrisarthi_vision_owner');
  if (!value) {
    value = `vision_${crypto.randomUUID?.() || Math.random().toString(36).slice(2)}`;
    localStorage.setItem('agrisarthi_vision_owner', value);
  }
  return value;
}

function severityClass(level) {
  if (['severe', 'high'].includes(level)) return 'bg-rose-600';
  if (level === 'moderate') return 'bg-amber-500';
  if (['low', 'very_low'].includes(level)) return 'bg-yellow-500';
  if (level === 'healthy') return 'bg-emerald-600';
  return 'bg-slate-500';
}

function confidence(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function Field({ label, children }) {
  return <label className="space-y-1 text-sm font-medium text-emerald-950"><span>{label}</span>{children}</label>;
}

function SelectField({ value, onChange, children }) {
  return <select value={value} onChange={(event) => onChange(event.target.value)} className="h-11 w-full rounded-lg border border-emerald-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-emerald-500">{children}</select>;
}

function ImagePreview({ item, onRemove }) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-emerald-200 bg-white">
      <img src={item.url} alt={item.file.name} className="h-32 w-full object-cover" />
      <button type="button" onClick={onRemove} className="absolute right-2 top-2 rounded-full bg-black/65 p-1 text-white" aria-label="Remove image"><X className="h-4 w-4" /></button>
      <div className="truncate px-2 py-1.5 text-xs text-slate-600">{item.file.name}</div>
    </div>
  );
}

function ResultImage({ image }) {
  const original = image.urls?.original;
  const annotated = image.urls?.annotated;
  const zoom = image.urls?.zoom;
  return (
    <Card className="overflow-hidden border-emerald-200">
      <CardHeader className="pb-2"><CardTitle className="flex items-center justify-between gap-2 text-sm"><span className="truncate">{image.original_name}</span><Badge variant="outline">{image.quality?.suitable ? 'Clear' : 'Retake needed'}</Badge></CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          {original && <div><p className="mb-1 text-xs font-semibold text-slate-600">Original</p><a href={original} target="_blank" rel="noreferrer"><img src={original} alt="Original crop" className="h-56 w-full rounded-lg border object-contain bg-slate-50" /></a></div>}
          <div><p className="mb-1 text-xs font-semibold text-slate-600">Annotated result</p>{annotated ? <a href={annotated} target="_blank" rel="noreferrer"><img src={annotated} alt="Annotated damage" className="h-56 w-full rounded-lg border object-contain bg-slate-50" /></a> : <div className="grid h-56 place-items-center rounded-lg border border-dashed bg-slate-50 p-4 text-center text-xs text-slate-500">No boxes or masks were generated. This is expected when trained localization weights are unavailable or no region passes the threshold.</div>}</div>
        </div>
        {zoom && <div><p className="mb-1 flex items-center gap-1 text-xs font-semibold text-slate-600"><ZoomIn className="h-3.5 w-3.5" /> Most affected region</p><a href={zoom} target="_blank" rel="noreferrer"><img src={zoom} alt="Zoomed damage" className="max-h-64 w-full rounded-lg border object-contain bg-slate-50" /></a></div>}
        {!image.quality?.suitable && <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><b>Capture again:</b><ul className="mt-1 list-disc pl-5">{(image.quality?.capture_guidance || []).map((item) => <li key={item}>{item}</li>)}</ul></div>}
      </CardContent>
    </Card>
  );
}

function ScannerContent() {
  const { lang, setLang } = useLanguage();
  const galleryRef = useRef(null);
  const cameraRef = useRef(null);
  const filesRef = useRef([]);
  const [ownerId] = useState(() => getOwnerId());
  const [files, setFiles] = useState([]);
  const [crop, setCrop] = useState('auto');
  const [plantPart, setPlantPart] = useState('auto');
  const [growthStage, setGrowthStage] = useState('auto');
  const [harvestStage, setHarvestStage] = useState('auto');
  const [location, setLocation] = useState('');
  const [latitude, setLatitude] = useState(null);
  const [longitude, setLongitude] = useState(null);
  const [preference, setPreference] = useState('integrated');
  const [budget, setBudget] = useState('low');
  const [previousTreatment, setPreviousTreatment] = useState('');
  const [consent, setConsent] = useState(false);
  const [result, setResult] = useState(null);
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState([]);
  const [view, setView] = useState('simple');
  const [loading, setLoading] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedbackVerdict, setFeedbackVerdict] = useState('partially_correct');
  const [cropCorrect, setCropCorrect] = useState(null);
  const [diseaseCorrect, setDiseaseCorrect] = useState(null);
  const [pestCorrect, setPestCorrect] = useState(null);
  const [treatmentHelpful, setTreatmentHelpful] = useState(null);
  const [correctedLabel, setCorrectedLabel] = useState('');
  const [expertDiagnosis, setExpertDiagnosis] = useState('');
  const [feedbackNotes, setFeedbackNotes] = useState('');

  useEffect(() => {
    fetch('/api/vision/health').then((response) => response.json()).then(setHealth).catch(() => setHealth(null));
    loadHistory();
  }, []);

  useEffect(() => { filesRef.current = files; }, [files]);
  useEffect(() => () => filesRef.current.forEach((item) => URL.revokeObjectURL(item.url)), []);

  useEffect(() => {
    if (!loading) return undefined;
    const timer = setInterval(() => setStageIndex((index) => Math.min(index + 1, STAGES.length - 1)), 1400);
    return () => clearInterval(timer);
  }, [loading]);

  async function loadHistory() {
    try {
      const response = await fetch(`/api/vision/history?owner_id=${encodeURIComponent(ownerId)}&limit=12`);
      const data = await response.json();
      if (response.ok) setHistory(data.items || []);
    } catch {}
  }

  function addFiles(fileList) {
    const selected = Array.from(fileList || []).filter((file) => file.type.startsWith('image/') || /\.(heic|heif)$/i.test(file.name));
    setFiles((current) => {
      const remaining = Math.max(0, 8 - current.length);
      return [...current, ...selected.slice(0, remaining).map((file) => ({ file, url: URL.createObjectURL(file) }))];
    });
  }

  function removeFile(index) {
    setFiles((current) => {
      URL.revokeObjectURL(current[index].url);
      return current.filter((_, itemIndex) => itemIndex !== index);
    });
  }

  function locate() {
    if (!navigator.geolocation) return setError('GPS is not supported in this browser.');
    navigator.geolocation.getCurrentPosition((position) => {
      setLatitude(position.coords.latitude);
      setLongitude(position.coords.longitude);
      setLocation((value) => value || `GPS: ${position.coords.latitude.toFixed(5)}, ${position.coords.longitude.toFixed(5)}`);
    }, () => setError('Location permission was denied. You can type the village, district, and state manually.'));
  }

  async function analyze() {
    if (!files.length) return setError('Add at least one clear crop, plant, produce, or pest image.');
    setLoading(true); setStageIndex(0); setError(''); setFeedbackMessage(''); setResult(null);
    const form = new FormData();
    files.forEach((item) => form.append('files', item.file, item.file.name));
    form.append('owner_id', ownerId);
    form.append('crop', crop);
    form.append('plant_part', plantPart);
    form.append('growth_stage', growthStage);
    form.append('harvest_stage', harvestStage);
    form.append('location', location);
    if (latitude != null) form.append('latitude', String(latitude));
    if (longitude != null) form.append('longitude', String(longitude));
    form.append('treatment_preference', preference);
    form.append('budget', budget);
    form.append('previous_treatment', previousTreatment);
    form.append('consent', String(consent));
    form.append('language', lang);
    try {
      const response = await fetch('/api/vision/analyze-session', { method: 'POST', body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Analysis failed.');
      setResult(data);
      await loadHistory();
    } catch (analysisError) {
      setError(analysisError.message || 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  }

  async function openHistory(analysisId) {
    setError('');
    const response = await fetch(`/api/vision/result/${analysisId}`);
    const data = await response.json();
    if (response.ok) setResult(data); else setError(data.detail || 'This analysis has expired.');
  }

  function speak() {
    if (!result?.voice_summary || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(result.voice_summary);
    utterance.lang = lang === 'te' ? 'te-IN' : lang === 'hi' ? 'hi-IN' : 'en-IN';
    utterance.rate = 0.9;
    window.speechSynthesis.speak(utterance);
  }

  function downloadReport() {
    if (!result) return;
    const diagnoses = [
      ...(result.diseases || []).map((item) => `${item.name} (${confidence(item.confidence)})`),
      ...(result.pests || []).map((item) => `${item.name} — directly visible (${confidence(item.confidence)})`),
    ];
    if (result.health_assessment?.reliable) diagnoses.push(`Apparently healthy (${confidence(result.health_assessment.confidence)})`);
    const recommendations = result.recommendations?.selected || [];
    const imageLinks = (result.images || []).map((image) => {
      const original = image.urls?.original ? `${window.location.origin}${image.urls.original}` : '';
      const annotated = image.urls?.annotated ? `${window.location.origin}${image.urls.annotated}` : '';
      const zoom = image.urls?.zoom ? `${window.location.origin}${image.urls.zoom}` : '';
      return `<li><strong>${escapeHtml(image.original_name)}</strong>${original ? ` — <a href="${escapeHtml(original)}">original</a>` : ''}${annotated ? ` · <a href="${escapeHtml(annotated)}">annotated</a>` : ''}${zoom ? ` · <a href="${escapeHtml(zoom)}">zoomed region</a>` : ''}</li>`;
    }).join('');
    const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AgriSarthi Vision Report</title><style>body{font-family:Arial,sans-serif;max-width:850px;margin:32px auto;padding:0 20px;color:#173b2a;line-height:1.5}h1,h2{color:#12633d}.summary{background:#eefbf3;border:1px solid #b6e3c7;border-radius:12px;padding:16px}.warning{background:#fff8e7;border:1px solid #efd38a;border-radius:10px;padding:12px}li{margin:7px 0}.meta{color:#52645b;font-size:14px}@media print{a{color:inherit;text-decoration:none}}</style></head><body><h1>AgriSarthi AI Crop Vision Report</h1><p class="meta">Analysis ID: ${escapeHtml(result.analysis_id)}<br>Created: ${escapeHtml(new Date(result.created_at).toLocaleString())}</p><div class="summary"><strong>Crop:</strong> ${escapeHtml(result.detected_crop)}<br><strong>Plant part:</strong> ${escapeHtml(result.plant_part)}<br><strong>Growth stage:</strong> ${escapeHtml(result.growth_stage)}<br><strong>Status:</strong> ${escapeHtml(result.status)}<br><strong>Image-based severity:</strong> ${escapeHtml(result.severity?.level || 'unknown')} ${result.severity?.affected_percentage == null ? '(not estimated)' : `(${escapeHtml(result.severity.affected_percentage)}%)`}<p>${escapeHtml(result.farmer_message)}</p></div><h2>Findings</h2>${diagnoses.length ? `<ul>${diagnoses.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : '<p>No reliable diagnosis was generated.</p>'}<h2>Recommended actions</h2>${recommendations.length ? `<ol>${recommendations.map((item) => `<li><strong>${escapeHtml(item.title)}</strong>: ${escapeHtml(item.detail)} <em>(${escapeHtml(item.cost_category || 'cost unknown')})</em></li>`).join('')}</ol>` : '<p>No treatment recommendation was generated.</p>'}<h2>Images</h2><ul>${imageLinks}</ul><p class="warning"><strong>Important:</strong> ${escapeHtml(result.disclaimer)} Image links remain available only during the configured retention period.</p></body></html>`;
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `agrisarthi-vision-report-${result.analysis_id}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function downloadRawJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `agrisarthi-vision-technical-${result.analysis_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function sendFeedback(verdict = feedbackVerdict) {
    if (!result) return;
    setFeedbackMessage('');
    const response = await fetch('/api/vision/feedback', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_id: result.analysis_id, owner_id: ownerId, verdict,
        crop_correct: cropCorrect, disease_correct: diseaseCorrect, pest_correct: pestCorrect,
        treatment_helpful: treatmentHelpful, corrected_label: correctedLabel || null,
        expert_diagnosis: expertDiagnosis || null, notes: feedbackNotes || null,
      }),
    });
    const data = await response.json();
    setFeedbackMessage(response.ok ? data.message : data.detail || 'Could not save feedback.');
    if (response.ok) setShowFeedbackForm(false);
  }

  function startFeedback(verdict) {
    setFeedbackVerdict(verdict);
    setShowFeedbackForm(true);
    setFeedbackMessage('');
  }

  const selectedRecommendations = result?.recommendations?.selected || [];
  const qualityProgress = useMemo(() => loading ? ((stageIndex + 1) / STAGES.length) * 100 : 0, [loading, stageIndex]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-lime-50 to-amber-50">
      <header className="sticky top-0 z-20 border-b border-emerald-100 bg-white/90 backdrop-blur">
        <div className="container mx-auto flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div><a href="/" className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700"><ArrowLeft className="h-3.5 w-3.5" /> AgriSarthi home</a><h1 className="mt-1 flex items-center gap-2 text-xl font-bold text-emerald-950"><Microscope className="h-6 w-6" /> AI Crop Pest & Disease Vision Analyzer</h1></div>
          <div className="flex items-center gap-2"><Badge className={health?.development_mode ? 'bg-amber-600' : 'bg-emerald-700'}><Cpu className="mr-1 h-3 w-3" />{health?.development_mode ? 'Development mode' : 'Models ready'}</Badge><SelectField value={lang} onChange={setLang}><option value="en">English</option><option value="te">తెలుగు</option><option value="hi">हिन्दी</option></SelectField></div>
        </div>
      </header>

      <main className="container mx-auto space-y-5 px-4 py-6">
        {health?.development_mode && <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"><b>No trained vision weights are installed.</b> The app will validate image quality and preserve the complete integration flow, but it will not invent crop, disease, pest, severity, or treatment predictions. Add evaluated weights using the model registry instructions.</div>}

        <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
          <Card className="border-emerald-200">
            <CardHeader><CardTitle className="flex items-center gap-2"><Camera className="h-5 w-5 text-emerald-700" /> Add crop images</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files); }} className={`rounded-2xl border-2 border-dashed p-7 text-center transition ${dragging ? 'border-emerald-600 bg-emerald-50' : 'border-emerald-300 bg-white'}`}>
                <ImageIcon className="mx-auto h-12 w-12 text-emerald-600" /><p className="mt-2 font-semibold text-emerald-950">Upload up to 8 views from field, plant, leaf, stem, fruit, root, seed, harvested produce, stored produce, or visible pest</p><p className="mt-1 text-xs text-slate-500">JPEG, PNG, WEBP, and HEIC/HEIF when backend support is installed. Each image must be within the configured upload limit.</p>
                <div className="mt-4 flex flex-wrap justify-center gap-2"><Button type="button" onClick={() => cameraRef.current?.click()} className="h-12 bg-emerald-600 hover:bg-emerald-700"><Camera className="mr-2 h-5 w-5" /> Take photo</Button><Button type="button" variant="outline" onClick={() => galleryRef.current?.click()} className="h-12"><Upload className="mr-2 h-5 w-5" /> Choose images</Button></div>
                <input ref={cameraRef} type="file" accept={ACCEPTED} capture="environment" className="hidden" onChange={(event) => addFiles(event.target.files)} />
                <input ref={galleryRef} type="file" accept={ACCEPTED} multiple className="hidden" onChange={(event) => addFiles(event.target.files)} />
              </div>
              {files.length > 0 && <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{files.map((item, index) => <ImagePreview key={`${item.file.name}-${index}`} item={item} onRemove={() => removeFile(index)} />)}</div>}
            </CardContent>
          </Card>

          <Card className="border-emerald-200">
            <CardHeader><CardTitle className="flex items-center gap-2"><Sprout className="h-5 w-5 text-emerald-700" /> Analysis context</CardTitle></CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <Field label="Crop"><SelectField value={crop} onChange={setCrop}><option value="auto">Auto-detect</option>{['cotton','rice','maize','tomato','chilli','potato','groundnut','soybean','wheat','other'].map((item) => <option key={item} value={item}>{item}</option>)}</SelectField></Field>
              <Field label="Plant part"><SelectField value={plantPart} onChange={setPlantPart}><option value="auto">Auto-detect</option>{['field','whole_plant','leaf','stem','fruit','flower','root','seed','harvested_produce','stored_produce','visible_pest'].map((item) => <option key={item} value={item}>{item.replaceAll('_',' ')}</option>)}</SelectField></Field>
              <Field label="Growth stage"><SelectField value={growthStage} onChange={setGrowthStage}><option value="auto">Auto-detect</option>{['seedling','vegetative','flowering','fruiting','maturity','storage'].map((item) => <option key={item} value={item}>{item}</option>)}</SelectField></Field>
              <Field label="Condition stage"><SelectField value={harvestStage} onChange={setHarvestStage}><option value="auto">Auto-detect</option><option value="pre_harvest">Pre-harvest</option><option value="post_harvest">Post-harvest</option></SelectField></Field>
              <Field label="Treatment preference"><SelectField value={preference} onChange={setPreference}><option value="natural">Natural only</option><option value="artificial">Artificial only</option><option value="integrated">Integrated pest management</option><option value="cheapest">Cheapest safe option</option><option value="fastest">Fastest safe option</option></SelectField></Field>
              <Field label="Budget"><SelectField value={budget} onChange={setBudget}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></SelectField></Field>
              <Field label="Farmer location"><div className="flex gap-2"><Input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Village, district, state" /><Button type="button" variant="outline" onClick={locate}><MapPin className="h-4 w-4" /></Button></div></Field>
              <Field label="Previously applied treatment"><Textarea value={previousTreatment} onChange={(event) => setPreviousTreatment(event.target.value)} placeholder="Optional: treatment name, date, and result" /></Field>
              <label className="flex items-start gap-2 rounded-lg border bg-white p-3 text-xs text-slate-700"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-0.5" /><span>I consent to retaining these images for the configured consent period. Without consent, images are kept only temporarily for this analysis and then expire.</span></label>
              <Button onClick={analyze} disabled={loading || !files.length} className="h-14 bg-emerald-600 text-base hover:bg-emerald-700">{loading ? <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Analyzing safely</> : <><Sparkles className="mr-2 h-5 w-5" /> Analyze images</>}</Button>
              {loading && <div className="rounded-lg bg-emerald-50 p-3"><div className="mb-2 flex items-center justify-between text-xs font-semibold text-emerald-900"><span>{STAGES[stageIndex]}</span><span>{Math.round(qualityProgress)}%</span></div><Progress value={qualityProgress} /></div>}
              {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
            </CardContent>
          </Card>
        </section>

        {result && <section className="space-y-4">
          <Card className="border-emerald-300 bg-white">
            <CardContent className="p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between"><div><div className="flex flex-wrap items-center gap-2"><Badge className={severityClass(result.severity?.level)}>{result.severity?.level || 'unknown'}</Badge><Badge variant="outline">{result.status}</Badge><Badge variant="outline">{result.detected_crop}</Badge></div><h2 className="mt-3 text-xl font-bold text-emerald-950">{result.farmer_message}</h2><p className="mt-2 text-sm text-slate-600">Affected area: {result.severity?.affected_percentage == null ? 'Not estimated' : `${result.severity.affected_percentage}%`} · Plant part: {result.plant_part} · Stage: {result.growth_stage}</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={speak}><Volume2 className="mr-2 h-4 w-4" /> Voice explanation</Button><Button variant="outline" onClick={downloadReport}><Download className="mr-2 h-4 w-4" /> Download farmer report</Button>{view === 'advanced' && <Button variant="outline" onClick={downloadRawJson}><FileImage className="mr-2 h-4 w-4" /> Technical JSON</Button>}</div></div>
              <div className="mt-4 flex gap-2"><Button size="sm" variant={view === 'simple' ? 'default' : 'outline'} onClick={() => setView('simple')}>Simple farmer view</Button><Button size="sm" variant={view === 'advanced' ? 'default' : 'outline'} onClick={() => setView('advanced')}>Advanced view</Button></div>
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">{result.images?.map((image) => <ResultImage key={image.image_id} image={image} />)}</div>

          {view === 'simple' ? <><div className="grid gap-4 lg:grid-cols-3">
            <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Bug className="h-5 w-5 text-rose-600" /> What was found</CardTitle></CardHeader><CardContent className="space-y-3">{result.health_assessment?.reliable && <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3"><b>Apparently healthy</b><p className="text-xs text-emerald-800">Confidence {confidence(result.health_assessment.confidence)}. This applies only to the uploaded image.</p></div>}{result.diseases?.length ? result.diseases.map((item) => <div key={`${item.raw_label}-${item.rank}`} className="rounded-lg border p-3"><b>{item.name}</b><p className="text-xs text-slate-600">{item.category} · confidence {confidence(item.confidence)}</p></div>) : null}{result.pests?.length ? result.pests.map((item, index) => <div key={`${item.raw_label}-${index}`} className="rounded-lg border p-3"><b>{item.name}</b><p className="text-xs text-slate-600">Directly visible · confidence {confidence(item.confidence)}</p></div>) : null}{!result.health_assessment?.reliable && !result.diseases?.length && !result.pests?.length && <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">No reliable diagnosis was produced. Follow the requested image angles and contact an expert if symptoms are spreading.</div>}</CardContent></Card>
            <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><ClipboardCheck className="h-5 w-5 text-emerald-700" /> Safe next steps</CardTitle></CardHeader><CardContent><ol className="space-y-3">{selectedRecommendations.slice(0, 6).map((item, index) => <li key={`${item.title}-${index}`} className="flex gap-3 text-sm"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-emerald-100 font-bold text-emerald-800">{index + 1}</span><span><b>{item.title}:</b> {item.detail}</span></li>)}</ol>{result.recommendations?.commercial_warning && <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">{result.recommendations.commercial_warning}</div>}</CardContent></Card>
            <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><CloudRain className="h-5 w-5 text-sky-600" /> Weather & prevention</CardTitle></CardHeader><CardContent className="space-y-2">{(result.recommendations?.weather_warnings || []).map((item) => <div key={item} className="rounded-lg bg-sky-50 p-3 text-sm text-sky-900">{item}</div>)}{!(result.recommendations?.weather_warnings || []).length && <p className="text-sm text-slate-600">Weather advice needs field coordinates and a working forecast connection.</p>}{result.recommendations?.nutrient_note && <div className="rounded-lg bg-lime-50 p-3 text-sm text-lime-900">{result.recommendations.nutrient_note}</div>}</CardContent></Card>
          </div><div className="grid gap-4 lg:grid-cols-2"><Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Leaf className="h-5 w-5 text-emerald-700" /> Natural and low-cost options</CardTitle></CardHeader><CardContent className="space-y-2">{(result.recommendations?.natural || []).length ? result.recommendations.natural.map((item, index) => <div key={`${item.title}-${index}`} className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-3 text-sm"><div className="flex items-center justify-between gap-2"><b>{item.title}</b><Badge variant="outline">{item.cost_category || 'unknown cost'}</Badge></div><p className="mt-1 text-slate-700">{item.detail}</p></div>) : <p className="text-sm text-slate-500">No natural option was generated without a reliable diagnosis.</p>}</CardContent></Card><Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="h-5 w-5 text-sky-700" /> Verified commercial options</CardTitle></CardHeader><CardContent className="space-y-2">{(result.recommendations?.commercial || []).length ? result.recommendations.commercial.map((item, index) => <div key={`${item.title}-${index}`} className="rounded-lg border border-sky-100 bg-sky-50/50 p-3 text-sm"><div className="flex items-center justify-between gap-2"><b>{item.title}</b><Badge variant="outline">{item.cost_category || 'unknown cost'}</Badge></div><p className="mt-1 text-xs font-medium text-sky-800">{item.product_category || 'Registered crop protection product'} · active ingredient shown above</p><p className="mt-1 text-slate-700">{item.detail}</p>{item.safety_precautions?.length ? <ul className="mt-2 list-disc pl-5 text-xs text-slate-600">{item.safety_precautions.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}<p className="mt-2 text-xs text-slate-500">Re-entry: {item.re_entry_interval || 'confirm label'} · Pre-harvest: {item.pre_harvest_interval || 'confirm label'}</p></div>) : <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{result.recommendations?.commercial_warning || 'No verified commercial record matched this analysis.'}</div>}</CardContent></Card></div></> : <div className="grid gap-4 lg:grid-cols-2">
            <Card><CardHeader><CardTitle className="text-base">Confidence and alternatives</CardTitle></CardHeader><CardContent className="space-y-2"><pre className="max-h-96 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-emerald-100">{JSON.stringify({ health_assessment: result.health_assessment, diseases: result.diseases, pests: result.pests, pest_evidence: result.pest_evidence, alternatives: result.possible_alternatives, severity: result.severity, uncertainty: result.uncertainty, explainability: result.explainability, image_regions: result.images?.map((image) => ({ image_id: image.image_id, damage_regions: image.damage_regions, crop_prediction: image.crop_prediction })) }, null, 2)}</pre></CardContent></Card>
            <Card><CardHeader><CardTitle className="text-base">Model registry and runtime</CardTitle></CardHeader><CardContent className="space-y-2">{Object.values(result.model_summary?.models || {}).map((model) => <div key={model.key} className="rounded-lg border p-3 text-xs"><div className="flex items-center justify-between"><b>{model.name}</b><Badge className={model.ready ? 'bg-emerald-600' : 'bg-slate-500'}>{model.ready ? 'ready' : 'unavailable'}</Badge></div><p className="mt-1 text-slate-600">Version {model.version} · {model.task} · threshold {model.threshold}</p><p className="text-slate-500">{model.message}</p></div>)}</CardContent></Card>
          </div>}

          <Card className="border-amber-200"><CardContent className="p-4"><div className="flex gap-3"><AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" /><div><p className="font-semibold text-amber-950">Advisory limitation</p><p className="text-sm text-amber-900">{result.disclaimer}</p></div></div><div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3 text-sm"><span>Was this result correct?</span><Button size="sm" variant="outline" onClick={() => startFeedback('correct')}><ThumbsUp className="mr-1 h-4 w-4" /> Correct</Button><Button size="sm" variant="outline" onClick={() => startFeedback('partially_correct')}>Partly</Button><Button size="sm" variant="outline" onClick={() => startFeedback('incorrect')}><ThumbsDown className="mr-1 h-4 w-4" /> Incorrect</Button>{feedbackMessage && <span className="text-xs text-emerald-700">{feedbackMessage}</span>}</div>{showFeedbackForm && <div className="mt-4 grid gap-3 rounded-xl border bg-slate-50 p-4 md:grid-cols-2"><Field label="Crop name correct?"><SelectField value={cropCorrect == null ? '' : String(cropCorrect)} onChange={(value) => setCropCorrect(value === '' ? null : value === 'true')}><option value="">Not sure</option><option value="true">Yes</option><option value="false">No</option></SelectField></Field><Field label="Disease correct?"><SelectField value={diseaseCorrect == null ? '' : String(diseaseCorrect)} onChange={(value) => setDiseaseCorrect(value === '' ? null : value === 'true')}><option value="">Not sure / not applicable</option><option value="true">Yes</option><option value="false">No</option></SelectField></Field><Field label="Pest correct?"><SelectField value={pestCorrect == null ? '' : String(pestCorrect)} onChange={(value) => setPestCorrect(value === '' ? null : value === 'true')}><option value="">Not sure / not applicable</option><option value="true">Yes</option><option value="false">No</option></SelectField></Field><Field label="Treatment helpful?"><SelectField value={treatmentHelpful == null ? '' : String(treatmentHelpful)} onChange={(value) => setTreatmentHelpful(value === '' ? null : value === 'true')}><option value="">Not tried / not sure</option><option value="true">Helpful</option><option value="false">Not helpful</option></SelectField></Field><Field label="Corrected crop, disease, or pest label"><Input value={correctedLabel} onChange={(event) => setCorrectedLabel(event.target.value)} placeholder="Optional corrected label" /></Field><Field label="Agriculture-expert diagnosis"><Input value={expertDiagnosis} onChange={(event) => setExpertDiagnosis(event.target.value)} placeholder="Optional expert diagnosis" /></Field><div className="md:col-span-2"><Field label="Additional notes"><Textarea value={feedbackNotes} onChange={(event) => setFeedbackNotes(event.target.value)} placeholder="Symptoms, treatment result, or why the prediction was wrong" /></Field></div><div className="flex gap-2 md:col-span-2"><Button onClick={() => sendFeedback(feedbackVerdict)} className="bg-emerald-700 hover:bg-emerald-800">Save for expert review</Button><Button variant="outline" onClick={() => setShowFeedbackForm(false)}>Cancel</Button></div><p className="text-xs text-slate-500 md:col-span-2">Feedback is stored as a pending dataset candidate. It is never used for uncontrolled online training.</p></div>}</CardContent></Card>
        </section>}

        <Card className="border-emerald-200"><CardHeader><CardTitle className="flex items-center gap-2 text-base"><History className="h-5 w-5" /> Analysis history</CardTitle></CardHeader><CardContent>{history.length ? <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">{history.map((item) => <button key={item.analysis_id} onClick={() => openHistory(item.analysis_id)} className="rounded-lg border bg-white p-3 text-left hover:border-emerald-500"><div className="flex items-center justify-between"><b className="capitalize text-emerald-950">{item.crop || 'unknown crop'}</b><Badge className={severityClass(item.severity)}>{item.severity || 'unknown'}</Badge></div><p className="mt-1 text-xs text-slate-500">{new Date(item.created_at).toLocaleString()} · {item.status}</p></button>)}</div> : <p className="text-sm text-slate-500">No previous vision analyses are available for this browser session.</p>}</CardContent></Card>
      </main>
    </div>
  );
}

export default function PestGuardPage() {
  return <AuthGuard><ScannerContent /></AuthGuard>;
}
