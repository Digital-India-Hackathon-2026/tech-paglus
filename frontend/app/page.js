'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { toast, Toaster } from 'sonner';
import { Mic, MicOff, Volume2, Pause, RotateCw, MapPin, Upload, ThumbsUp, ThumbsDown, Sprout, CloudRain, TrendingUp, Droplets, Wheat, Leaf, Loader2, Compass, FileText, Sun, Wind, Languages, Bot, Play, Radio, Info, LogOut, ChevronLeft, ChevronRight, ClipboardList } from 'lucide-react';
import { STRINGS, LANG_TAGS, t } from '@/lib/i18n';
import AuthGuard from '@/components/AuthGuard';
import { useAuth } from '@/lib/auth';
import { LOGOUT } from '@/lib/constants/testIds/auth';
import NotificationBell from '@/components/NotificationBell';
import { useNotifications, buildSmartAlerts } from '@/hooks/use-notifications';
import { useLanguage } from '@/lib/language';

const STATUS = { idle:'idle', listening:'listening', thinking:'thinking', locating:'locating', readingPdf:'readingPdf', checkingMandi:'checkingMandi', checkingWeather:'checkingWeather', preparing:'preparing', speaking:'speaking' };

function getSessionId(){
  if (typeof window === 'undefined') return 'srv';
  let s = localStorage.getItem('agri_session');
  if (!s){ s = 'sess_' + Math.random().toString(36).slice(2,10); localStorage.setItem('agri_session', s); }
  return s;
}

function useSpeech(lang){
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [supported, setSupported] = useState(true);
  const recRef = useRef(null);
  useEffect(()=>{
    if (typeof window === 'undefined') return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR){ setSupported(false); return; }
    const r = new SR(); r.continuous=false; r.interimResults=true; r.lang = LANG_TAGS[lang]||'en-IN';
    r.onresult = (e)=>{ let txt=''; for(const res of e.results) txt += res[0].transcript; setTranscript(txt); };
    r.onend = ()=> setListening(false);
    r.onerror = ()=> setListening(false);
    recRef.current = r;
  },[lang]);
  const start = () => { try { setTranscript(''); recRef.current?.start(); setListening(true);} catch{} };
  const stop  = () => { try { recRef.current?.stop(); } catch{} };
  const speak = (text, opts={}) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    // chunked speech for natural pauses
    const chunks = String(text||'').split(/(?<=[.!?。।,])\s+/).filter(Boolean);
    chunks.forEach((c,i)=>{
      const u = new SpeechSynthesisUtterance(c);
      u.lang = LANG_TAGS[lang]||'en-IN';
      u.rate = opts.rate ?? 0.92;
      u.pitch = 1;
      window.speechSynthesis.speak(u);
    });
  };
  const pause = ()=> window.speechSynthesis?.pause();
  const resume = ()=> window.speechSynthesis?.resume();
  const stopSpeak = ()=> window.speechSynthesis?.cancel();
  return { listening, transcript, supported, start, stop, speak, pause, resume, stopSpeak };
}

function AgentStatusBar({ status, lang }){
  const label = status==='idle' ? STRINGS[lang].idle : STRINGS[lang][status];
  const busy = status !== 'idle';
  return (
    <div className="flex items-center gap-3 rounded-full bg-white/60 backdrop-blur px-4 py-2 shadow-sm border border-emerald-100">
      <div className={`h-2.5 w-2.5 rounded-full ${busy?'bg-amber-500 animate-pulse':'bg-emerald-500'}`}></div>
      <span className="text-sm font-medium text-emerald-900">{label}</span>
      {busy && <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-700" />}
    </div>
  );
}

function ScorePill({ label, value }){
  const color = value>=75 ? 'bg-emerald-100 text-emerald-800 border-emerald-200' : value>=50 ? 'bg-amber-100 text-amber-800 border-amber-200' : 'bg-rose-100 text-rose-800 border-rose-200';
  return <span className={`text-xs px-2 py-0.5 rounded-full border ${color}`}>{label}: {value}</span>;
}

const PAGES = [
  { key: 'agent', label: 'AI Agent' },
  { key: 'farm', label: 'Location & Farm' },
  { key: 'weather', label: 'Weather' },
  { key: 'crops', label: 'Recommended Crops' },
  { key: 'details', label: 'Plan & Schemes' },
];

function AppContent(){
  const router = useRouter();
  const { user, logout } = useAuth({ redirectIfUnauthenticated: false });
  // Language chosen at signup/login (and changeable from the header below)
  // drives the whole app — kept in sync with the global selection.
  const { lang: globalLang, setLang: setGlobalLang } = useLanguage();
  const [lang, setLangState] = useState('en');
  useEffect(() => { setLangState(globalLang); }, [globalLang]);
  const setLang = (code) => { setLangState(code); setGlobalLang(code); };
  const T = STRINGS[lang];
  const [status, setStatus] = useState('idle');
  const [sessionId] = useState(() => (typeof window!=='undefined'?getSessionId():'srv'));
  const speech = useSpeech(lang);
    const [pageIndex, setPageIndexState] = useState(() => {
     if (typeof window === 'undefined') return 0;
     const stepParam = new URLSearchParams(window.location.search).get('step');
     const parsed = parseInt(stepParam, 10);
     return Number.isFinite(parsed) ? Math.max(0, Math.min(PAGES.length - 1, parsed)) : 0;
   });
   const setPageIndex = (i) => {
     setPageIndexState(i);
     if (typeof window !== 'undefined') {
       const url = new URL(window.location.href);
       url.searchParams.set('step', String(i));
       window.history.replaceState({}, '', url);
     }
   };
  const notifications = useNotifications(sessionId);

  const [location, setLocation] = useState({ query:'', lat:null, lon:null, state:'', district:'', village:'', confidence:'' });
  const [soil, setSoil] = useState('red_loam');
  const [water, setWater] = useState('medium');
  const [budget, setBudget] = useState('medium');
  const [farmSize, setFarmSize] = useState(2);
  const [season, setSeason] = useState('kharif');

  const [pdfFields, setPdfFields] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const [recs, setRecs] = useState(null);
  const [weather, setWeather] = useState(null);
  const [selected, setSelected] = useState(null);
  const [mandi, setMandi] = useState(null);
  const [irrigation, setIrrigation] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [learnedNote, setLearnedNote] = useState(false);

  useEffect(()=>{
    if (speech.transcript) setLocation(l => ({ ...l, query: speech.transcript }));
  }, [speech.transcript]);

  const setStatusFor = (s, ms=900) => { setStatus(s); if(ms>0) setTimeout(()=>setStatus('idle'), ms); };

  async function useGPS(){
    if (!navigator.geolocation) return toast.error('GPS not supported');
    setStatus('locating');
    navigator.geolocation.getCurrentPosition(async pos => {
      const { latitude, longitude } = pos.coords;
      const r = await fetch('/api/reverse-geocode', { method:'POST', body: JSON.stringify({ lat: latitude, lon: longitude })});
      const d = await r.json();
      setLocation({ query:d.display||'', lat:latitude, lon:longitude, state:d.state||'', district:d.district||'', village:d.village||'', confidence:'high' });
      setStatus('idle');
      toast.success('GPS location captured');
    }, () => { setStatus('idle'); toast.error('GPS denied'); });
  }

  async function searchLocation(){
    if (!location.query) return;
    setStatus('locating');
    const r = await fetch('/api/geocode', { method:'POST', body: JSON.stringify({ query: location.query })});
    const d = await r.json();
    if (d.ok){
      setLocation({ ...location, lat:d.lat, lon:d.lon, state:d.state, district:d.district, village:d.village, confidence:d.confidence });
      toast.success(`Found: ${d.display}`);
    } else toast.error('Not found');
    setStatus('idle');
  }

  async function onPdf(e){
    const file = e.target.files?.[0]; if(!file) return;
    setPdfLoading(true); setStatus('readingPdf');
    const fd = new FormData(); fd.append('file', file);
    const r = await fetch('/api/pdf-extract', { method:'POST', body: fd });
    const d = await r.json();
    setPdfLoading(false); setStatus('idle');
    if (!d.ok) return toast.error('Could not read PDF');
    setPdfFields(d);
    // auto-fill
    const f = d.fields;
    setLocation(l => ({ ...l, query: [f.village,f.mandal,f.district,f.state].filter(Boolean).join(', ') || l.query, state: f.state || l.state, district: f.district || l.district, village: f.village || l.village, lat: f.lat||l.lat, lon: f.lon||l.lon, confidence: f.lat?'high':l.confidence }));
    if (f.soilType) setSoil(f.soilType.toLowerCase().includes('black')?'black':f.soilType.toLowerCase().includes('clay')?'clay':f.soilType.toLowerCase().includes('sandy')?'sandy_loam':'red_loam');
    toast.success(`Extracted ${d.confidence}% — ${Object.values(f).filter(Boolean).length} fields`);
  }

  async function runAgent(){
    if (!location.lat || !location.lon) return toast.error('Please confirm location first');
    setLoading(true);
    setStatus('checkingWeather'); await new Promise(r=>setTimeout(r,300));
    setStatus('thinking');
    const body = { lat:location.lat, lon:location.lon, state:location.state, district:location.district, soil, water, budget, farmSize, season };
    const rr = await fetch('/api/recommend', { method:'POST', body: JSON.stringify(body)});
    const rd = await rr.json();
    setRecs(rd); setWeather(rd.weather);
    const top = rd.top?.[0];
    setSelected(top?.id);
    setStatus('checkingMandi');
    const [mr, ir, ar] = await Promise.all([
      fetch('/api/mandi',{method:'POST', body: JSON.stringify({ crop: top?.id, state: location.state, district: location.district })}).then(r=>r.json()),
      fetch('/api/irrigation',{method:'POST', body: JSON.stringify({ crop: top?.id, soil, water, budget, lat:location.lat, lon:location.lon })}).then(r=>r.json()),
      fetch('/api/advisory-ui',{method:'POST', body: JSON.stringify({ crop: top?.id, state:location.state, water, lang, lat:location.lat, lon:location.lon })}).then(r=>r.json())
    ]);
    setMandi(mr); setIrrigation(ir.plan); setAdvisory(ar.advisory);
    // save profile
    fetch('/api/profile', { method:'POST', body: JSON.stringify({ sessionId, lang, location, soil, water, budget, lastCrop: top?.id })});
    setStatus('speaking');
    if (ar.advisory?.voice) speech.speak(ar.advisory.voice);
    setLoading(false);
    setTimeout(()=>setStatus('idle'), 1500);
  }

  async function pickCrop(id){
    setSelected(id); setStatus('preparing');
    const [mr, ir, ar] = await Promise.all([
      fetch('/api/mandi',{method:'POST', body: JSON.stringify({ crop: id, state: location.state, district: location.district })}).then(r=>r.json()),
      fetch('/api/irrigation',{method:'POST', body: JSON.stringify({ crop: id, soil, water, budget, lat:location.lat, lon:location.lon })}).then(r=>r.json()),
      fetch('/api/advisory-ui',{method:'POST', body: JSON.stringify({ crop: id, state:location.state, water, lang, lat:location.lat, lon:location.lon })}).then(r=>r.json())
    ]);
    setMandi(mr); setIrrigation(ir.plan); setAdvisory(ar.advisory);
    setStatus('idle');
  }

  async function sendFeedback(rating){
    const r = await fetch('/api/feedback-ui',{ method:'POST', body: JSON.stringify({ sessionId, rating, cropId: selected })});
    const d = await r.json();
    if (d.learned){ setLearnedNote(true); toast.success(rating==='up'?'Thanks! Learning your preference.':'Got it — will adjust next time'); }
  }

  const topCrop = recs?.top?.[0];

  // Smart notifications: derive farmer-facing alerts whenever weather or
  // irrigation data changes (e.g. "rain expected", "time to water").
  useEffect(() => {
    if (!weather) return;
    const alerts = buildSmartAlerts({ weather, irrigation, crop: selected, lang });
    alerts.forEach((a) => notifications.push(a));
  }, [weather, irrigation, selected]);

  function goToPage(i){ setPageIndex(Math.max(0, Math.min(PAGES.length-1, i))); if (typeof window!=='undefined') window.scrollTo({top:0, behavior:'smooth'}); }
  function openCropPlan(id){
     pickCrop(id);
     router.push(`/crop/${id}?returnStep=4`);
   }
  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-lime-50 to-amber-50">
      <Toaster position="top-right" richColors />
      {/* HEADER */}
      <header className="sticky top-0 z-50 backdrop-blur bg-white/70 border-b border-emerald-100">
        <div className="container mx-auto flex items-center justify-between py-3 px-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-500 to-lime-500 grid place-items-center shadow-md">
              <Bot className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-emerald-900 leading-tight">{T.appName}</h1>
              <p className="text-xs text-emerald-700/70">{T.tagline}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <AgentStatusBar status={status} lang={lang} />
            <NotificationBell items={notifications.items} unreadCount={notifications.unreadCount} onOpen={notifications.markAllRead} onClear={notifications.clear} />
            <Select value={lang} onValueChange={setLang}>
              <SelectTrigger className="w-[130px]"><Languages className="h-4 w-4 mr-1" /><SelectValue/></SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="te">తెలుగు</SelectItem>
                <SelectItem value="hi">हिन्दी</SelectItem>
              </SelectContent>
            </Select>
            {user && (
              <div className="hidden md:flex items-center gap-2 pl-2 border-l border-emerald-100">
                <span className="text-sm text-emerald-900 font-medium">{user.name?.split(' ')[0]}</span>
                <Button variant="ghost" size="sm" onClick={logout} data-testid={LOGOUT.button} title="Log out">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* PAGE NAVIGATION — premium step flow instead of long scrolling */}
        <nav className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1">
          {PAGES.map((p, i) => (
            <button
              key={p.key}
              onClick={() => goToPage(i)}
              className={`shrink-0 flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition
                ${i === pageIndex ? 'border-emerald-500 bg-emerald-600 text-white shadow-sm' : 'border-emerald-200 bg-white text-emerald-800 hover:border-emerald-400'}`}
            >
              <span className={`h-4 w-4 rounded-full grid place-items-center text-[10px] ${i===pageIndex?'bg-white/25':'bg-emerald-50'}`}>{i+1}</span>
              {p.label}
            </button>
          ))}
        </nav>

        {pageIndex === 0 && (
        <>
        {/* HERO / VOICE AGENT */}
        <section className="grid md:grid-cols-3 gap-4">
          <Card className="md:col-span-2 border-emerald-200 bg-gradient-to-br from-white to-emerald-50">
            <CardContent className="p-6 flex flex-col md:flex-row items-start md:items-center gap-4">
              <div className="flex-1">
                <p className="text-sm text-emerald-700 mb-1 uppercase tracking-wider">AI Agent</p>
                <h2 className="text-2xl md:text-3xl font-bold text-emerald-950 leading-tight">{T.hello}</h2>
                <p className="text-sm text-emerald-800/70 mt-2">{T.noKey}</p>
              </div>
              <div className="flex flex-col gap-2 w-full md:w-auto">
                <Button onClick={()=> speech.listening ? speech.stop() : (setStatus('listening'), speech.start())} className={`${speech.listening?'bg-rose-600 hover:bg-rose-700':'bg-emerald-600 hover:bg-emerald-700'} h-12 rounded-xl`}>
                  {speech.listening ? <><MicOff className="h-4 w-4 mr-2"/> {T.stopVoice}</> : <><Mic className="h-4 w-4 mr-2"/> {T.startVoice}</>}
                </Button>
                <a href="/pest-guard" className="inline-flex h-12 items-center justify-center rounded-xl border border-amber-200 bg-amber-50 px-4 text-sm font-semibold text-amber-900 hover:bg-amber-100">📷 Live pest & animal guard</a>
                {advisory?.voice && (
                  <div className="flex gap-1">
                    <Button variant="outline" size="sm" onClick={()=>speech.speak(advisory.voice)}><Volume2 className="h-3 w-3 mr-1"/>{T.speak}</Button>
                    <Button variant="outline" size="sm" onClick={()=>speech.pause()}><Pause className="h-3 w-3"/></Button>
                    <Button variant="outline" size="sm" onClick={()=>speech.speak(advisory.voice)}><RotateCw className="h-3 w-3"/></Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-emerald-200">
            <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><FileText className="h-4 w-4 text-emerald-700"/> {T.uploadPdf}</CardTitle></CardHeader>
            <CardContent>
              <label className="block cursor-pointer border-2 border-dashed border-emerald-300 rounded-lg p-4 text-center hover:bg-emerald-50 transition">
                <Upload className="h-6 w-6 mx-auto mb-1 text-emerald-600"/>
                <span className="text-xs text-emerald-800">Soil Health Card / ROR / Pattadar</span>
                <input type="file" accept="application/pdf" className="hidden" onChange={onPdf} />
              </label>
              {pdfLoading && <div className="mt-2 text-xs text-emerald-700 flex items-center gap-2"><Loader2 className="h-3 w-3 animate-spin"/> Reading PDF…</div>}
              {pdfFields && (
                <div className="mt-3 text-xs">
                  <div className="flex justify-between mb-1"><span className="text-emerald-800 font-medium">{T.extractedFrom}</span><Badge variant="secondary">{pdfFields.confidence}%</Badge></div>
                  <Progress value={pdfFields.confidence} className="h-1.5"/>
                  <div className="grid grid-cols-2 gap-1 mt-2 text-emerald-900">
                    {Object.entries(pdfFields.fields||{}).filter(([,v])=>v).slice(0,8).map(([k,v])=>(
                      <div key={k} className="truncate"><span className="text-emerald-600">{k}:</span> {String(v)}</div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </section>
        </>
        )}

        {pageIndex === 1 && (
        <>
        {/* LOCATION + FARM DETAILS */}
        <section className="grid md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base flex items-center gap-2"><MapPin className="h-4 w-4 text-emerald-700"/>{T.confirmLocation}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input placeholder="Village, District, State" value={location.query} onChange={e=>setLocation({...location, query:e.target.value})} onKeyDown={e=>e.key==='Enter'&&searchLocation()} />
                <Button onClick={searchLocation} variant="secondary"><Compass className="h-4 w-4"/></Button>
                <Button onClick={useGPS} variant="outline" className="whitespace-nowrap"><MapPin className="h-4 w-4 mr-1"/>{T.useGps}</Button>
              </div>
              {location.lat && (
                <div className="text-xs text-emerald-800 bg-emerald-50 rounded-lg p-3 space-y-1">
                  <div className="flex justify-between"><span>Latitude</span><span className="font-mono">{location.lat.toFixed(4)}</span></div>
                  <div className="flex justify-between"><span>Longitude</span><span className="font-mono">{location.lon.toFixed(4)}</span></div>
                  <div className="flex justify-between"><span>Confidence</span><Badge className={location.confidence==='high'?'bg-emerald-600':location.confidence==='medium'?'bg-amber-500':'bg-rose-500'}>{location.confidence}</Badge></div>
                  {location.state && <div className="flex justify-between"><span>State</span><span className="font-medium">{location.state}</span></div>}
                  {location.district && <div className="flex justify-between"><span>District</span><span className="font-medium">{location.district}</span></div>}
                  {location.lat && (
                    <div className="mt-2 rounded-md overflow-hidden border">
                      <iframe title="map" width="100%" height="180" src={`https://www.openstreetmap.org/export/embed.html?bbox=${location.lon-0.05}%2C${location.lat-0.05}%2C${location.lon+0.05}%2C${location.lat+0.05}&marker=${location.lat}%2C${location.lon}&layer=mapnik`}></iframe>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-base flex items-center gap-2"><Sprout className="h-4 w-4 text-emerald-700"/>Farm details</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs">Soil</Label>
                <Select value={soil} onValueChange={setSoil}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent>
                  <SelectItem value="red_loam">Red loam</SelectItem><SelectItem value="black">Black</SelectItem><SelectItem value="clay">Clay</SelectItem><SelectItem value="sandy_loam">Sandy loam</SelectItem><SelectItem value="alluvial">Alluvial</SelectItem><SelectItem value="loam">Loam</SelectItem>
                </SelectContent></Select></div>
              <div><Label className="text-xs">{T.water}</Label>
                <Select value={water} onValueChange={setWater}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="low">{T.low}</SelectItem><SelectItem value="medium">{T.medium}</SelectItem><SelectItem value="high">{T.high}</SelectItem></SelectContent></Select></div>
              <div><Label className="text-xs">{T.budget}</Label>
                <Select value={budget} onValueChange={setBudget}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="low">{T.low}</SelectItem><SelectItem value="medium">{T.medium}</SelectItem><SelectItem value="high">{T.high}</SelectItem></SelectContent></Select></div>
              <div><Label className="text-xs">{T.season}</Label>
                <Select value={season} onValueChange={setSeason}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="kharif">{T.kharif}</SelectItem><SelectItem value="rabi">{T.rabi}</SelectItem><SelectItem value="summer">{T.summer}</SelectItem></SelectContent></Select></div>
              <div className="col-span-2"><Label className="text-xs">{T.farmSize}</Label><Input type="number" value={farmSize} onChange={e=>setFarmSize(+e.target.value)} /></div>
              <Button onClick={runAgent} disabled={loading || !location.lat} className="col-span-2 bg-emerald-600 hover:bg-emerald-700 h-11">
                {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin"/>{T.processing}</> : <><Play className="h-4 w-4 mr-2"/>Get personalized advice</>}
              </Button>
            </CardContent>
          </Card>
        </section>
        </>
        )}

        {pageIndex === 2 && (
        <>
        {/* WEATHER PANEL */}
        {weather?.data ? (
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><CloudRain className="h-4 w-4 text-sky-600"/> Weather & 7-day forecast</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                <div className="rounded-lg bg-sky-50 p-3"><div className="text-xs text-sky-700">Now</div><div className="text-2xl font-bold text-sky-900">{weather.data.current?.temperature_2m}°C</div></div>
                <div className="rounded-lg bg-emerald-50 p-3"><div className="text-xs text-emerald-700">Humidity</div><div className="text-2xl font-bold text-emerald-900">{weather.data.current?.relative_humidity_2m}%</div></div>
                <div className="rounded-lg bg-indigo-50 p-3"><div className="text-xs text-indigo-700">7-day rain</div><div className="text-2xl font-bold text-indigo-900">{weather.summary?.rain7?.toFixed(0)}mm</div></div>
                <div className="rounded-lg bg-amber-50 p-3"><div className="text-xs text-amber-700">Max heat</div><div className="text-2xl font-bold text-amber-900">{weather.summary?.heat?.toFixed(0)}°C</div></div>
              </div>
              <div className="grid grid-cols-7 gap-1">
                {weather.data.daily?.temperature_2m_max?.slice(0,7).map((tmax,i)=>(
                  <div key={i} className="rounded-md bg-slate-50 p-2 text-center text-xs">
                    <div className="font-medium text-slate-700">D{i+1}</div>
                    <div className="text-rose-600">{tmax.toFixed(0)}°</div>
                    <div className="text-sky-600">{weather.data.daily.temperature_2m_min[i].toFixed(0)}°</div>
                    <div className="text-indigo-700 font-medium">{weather.data.daily.precipitation_sum[i].toFixed(0)}mm</div>
                  </div>
                ))}
              </div>
              {weather.risks?.length>0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {weather.risks.map(r=>(<Badge key={r.id} className={r.level==='high'?'bg-rose-600':'bg-amber-500'}>⚠ {r.msg}</Badge>))}
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card><CardContent className="p-8 text-center text-sm text-slate-500">Run the agent from the "Location & Farm" step to see weather here.</CardContent></Card>
        )}
        </>
        )}

        {pageIndex === 3 && (
        <>
        {/* CROP RECOMMENDATIONS */}
        {recs?.top && (
          <Card>
            <CardHeader className="pb-2 flex flex-row items-center justify-between"><CardTitle className="text-base flex items-center gap-2"><Wheat className="h-4 w-4 text-amber-600"/> {T.topCrops}</CardTitle>
              <Badge variant="outline">{recs.season} • {location.state}</Badge></CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                {recs.top.map((c,i)=>(
                  <div key={c.id} onClick={()=>openCropPlan(c.id)} className={`cursor-pointer rounded-xl border-2 p-4 transition ${selected===c.id?'border-emerald-500 bg-emerald-50':'border-slate-200 hover:border-emerald-300 bg-white'}`}>
                    <div className="flex justify-between items-start mb-1">
                      <div><div className="text-xs text-slate-500">#{i+1}</div><h4 className="font-bold text-emerald-950">{lang==='te'?c.name_te : lang==='hi'?c.name_hi : c.name}</h4></div>
                      <div className="text-right"><div className="text-2xl font-bold text-emerald-700">{c.total}</div><div className="text-[10px] text-slate-500">score</div></div>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      <ScorePill label="soil" value={c.scores.soil}/>
                      <ScorePill label="water" value={c.scores.water}/>
                      <ScorePill label="region" value={c.scores.region}/>
                      <ScorePill label="profit" value={c.scores.profit}/>
                      <ScorePill label="demand" value={c.scores.demand}/>
                    </div>
                    <p className="text-xs text-slate-700 mt-2 italic">{c.reason}</p>
                    <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
                      <div className="bg-slate-50 rounded p-1.5"><div className="text-slate-500">Modal ₹/qt</div><div className="font-bold">₹{c.modalPrice.toLocaleString()}</div></div>
                      <div className="bg-emerald-50 rounded p-1.5"><div className="text-emerald-600">Est. profit</div><div className="font-bold">₹{c.expectedProfit.toLocaleString()}</div></div>
                    </div>
                    {c.oversupplyRisk && <Badge className="bg-amber-500 mt-2 text-[10px]">⚠ oversupply risk in your state</Badge>}
                    <div className="mt-3 flex items-center gap-1 text-xs font-semibold text-emerald-700"><ClipboardList className="h-3.5 w-3.5"/> View full production plan <ChevronRight className="h-3.5 w-3.5"/></div>
                  </div>
                ))}
              </div>
              {recs.whyNotOthers?.length>0 && (
                <details className="mt-4"><summary className="cursor-pointer text-sm text-emerald-800 font-medium">{T.whyNot}</summary>
                  <div className="mt-2 text-xs text-slate-600 grid md:grid-cols-2 gap-1">
                    {recs.whyNotOthers.map(a=>(<div key={a.id}>• <b>{a.name}</b>: score {a.total} — {a.reason}</div>))}
                  </div>
                </details>
              )}
            </CardContent>
          </Card>
        )}
        </>
        )}

        {pageIndex === 4 && (
        <>
        {/* MANDI + IRRIGATION + ADVISORY */}
        {selected ? (
          <section className="grid md:grid-cols-3 gap-4">
            {mandi && (
              <Card><CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><TrendingUp className="h-4 w-4 text-emerald-700"/> {T.mandiPrices}</CardTitle></CardHeader><CardContent>
                <div className="rounded-lg bg-emerald-50 p-3 mb-2">
                  <div className="flex justify-between"><span className="text-xs text-emerald-700">Modal</span><span className="text-xl font-bold">₹{mandi.primary?.modal?.toLocaleString()}</span></div>
                  <div className="flex justify-between text-xs mt-1"><span>Min ₹{mandi.primary?.min?.toLocaleString()}</span><span>Max ₹{mandi.primary?.max?.toLocaleString()}</span></div>
                  <Badge className="mt-2" variant="outline">{mandi.primary?.trend==='up'?T.trendUp:mandi.primary?.trend==='down'?T.trendDown:T.trendStable} • {mandi.source}</Badge>
                </div>
                <div className="space-y-1 text-xs">{mandi.nearby?.map(m=>(<div key={m.market} className="flex justify-between border-b py-1"><span>{m.market}</span><span>₹{m.modal.toLocaleString()}</span></div>))}</div>
              </CardContent></Card>
            )}
            {irrigation && (
              <Card><CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><Droplets className="h-4 w-4 text-sky-600"/> {T.irrigation}</CardTitle></CardHeader><CardContent>
                <div className="mb-2"><Badge className="bg-sky-600">{irrigation.primary?.toUpperCase()}</Badge> <span className="text-xs text-slate-500">alt: {irrigation.alternative}</span></div>
                <p className="text-xs text-emerald-700 mb-2">{irrigation.benefit}</p>
                {irrigation.warning && <div className="text-xs text-amber-800 bg-amber-50 rounded p-2 mb-2">⚠ {irrigation.warning}</div>}
                <div className="space-y-1 text-xs">{irrigation.schedule.map(s=>(<div key={s.day} className="flex justify-between border-b py-1"><span>Day {s.day+1}</span><span className={s.action.includes('Skip')?'text-sky-700':'text-emerald-800'}>{s.action}</span></div>))}</div>
                <p className="text-[10px] text-slate-500 mt-2">{irrigation.subsidy}</p>
              </CardContent></Card>
            )}
            {advisory && (
              <Card><CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><Leaf className="h-4 w-4 text-emerald-700"/> {T.advisory}</CardTitle></CardHeader><CardContent className="text-sm space-y-2">
                <p className="font-semibold text-emerald-950">{advisory.short}</p>
                <p className="text-xs text-slate-700"><b><Sun className="h-3 w-3 inline"/> Weather:</b> {advisory.weather}</p>
                <p className="text-xs text-slate-700"><b><Droplets className="h-3 w-3 inline"/> Irrigation:</b> {advisory.irrigation}</p>
                <p className="text-xs text-slate-700"><b><TrendingUp className="h-3 w-3 inline"/> Mandi:</b> {advisory.mandi}</p>
                <p className="text-xs text-slate-700"><b><Sprout className="h-3 w-3 inline"/> Fertilizer:</b> {advisory.fertilizer}</p>
                <p className="text-xs text-rose-700"><b>⚠ {T.riskWarning}:</b> {advisory.risk}</p>
                <div className="flex gap-2 mt-3 pt-2 border-t">
                  <span className="text-xs text-slate-600 self-center">{T.feedback}</span>
                  <Button size="sm" variant="outline" onClick={()=>sendFeedback('up')}><ThumbsUp className="h-3 w-3 mr-1"/> {T.yes}</Button>
                  <Button size="sm" variant="outline" onClick={()=>sendFeedback('down')}><ThumbsDown className="h-3 w-3 mr-1"/> {T.no}</Button>
                </div>
                {learnedNote && <div className="text-[10px] text-emerald-700 flex items-center gap-1"><Info className="h-3 w-3"/>{T.learnedFrom}</div>}
              </CardContent></Card>
            )}
          </section>
        ) : (
          <Card><CardContent className="p-8 text-center text-sm text-slate-500">Pick a recommended crop on the previous step to see its market, irrigation and advisory plan here.</CardContent></Card>
        )}

        {/* SCHEMES */}
        <Card><CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><Info className="h-4 w-4 text-indigo-600"/> Government schemes for you</CardTitle></CardHeader><CardContent className="grid md:grid-cols-2 gap-3 text-sm">
          <div className="rounded-lg border p-3"><div className="font-semibold text-indigo-800">PM-KISAN</div><div className="text-xs text-slate-600">₹6,000/year direct benefit to eligible farmers.</div></div>
          <div className="rounded-lg border p-3"><div className="font-semibold text-indigo-800">PMFBY (Fasal Bima)</div><div className="text-xs text-slate-600">Crop insurance — low premium against weather losses.</div></div>
          <div className="rounded-lg border p-3"><div className="font-semibold text-indigo-800">Soil Health Card</div><div className="text-xs text-slate-600">Free soil testing every 2 years.</div></div>
          <div className="rounded-lg border p-3"><div className="font-semibold text-indigo-800">PMKSY (Micro-Irrigation)</div><div className="text-xs text-slate-600">55-90% subsidy on drip/sprinkler for small/marginal farmers.</div></div>
        </CardContent></Card>
        </>
        )}

        {/* NEXT / PREVIOUS — premium step flow instead of long scrolling */}
        <div className="flex items-center justify-between pt-4 border-t border-emerald-100">
          <Button variant="outline" onClick={()=>goToPage(pageIndex-1)} disabled={pageIndex===0} className="h-11 px-5">
            <ChevronLeft className="h-4 w-4 mr-1"/> Previous
          </Button>
          <span className="text-xs text-slate-500">Step {pageIndex+1} of {PAGES.length}</span>
          <Button onClick={()=>goToPage(pageIndex+1)} disabled={pageIndex===PAGES.length-1} className="h-11 px-5 bg-emerald-600 hover:bg-emerald-700">
            Next <ChevronRight className="h-4 w-4 ml-1"/>
          </Button>
        </div>

        <footer className="text-center text-xs text-slate-500 py-6">
          <div>AgriSarthi AI — rule-based advisory active (no AI key). Weather via Open-Meteo • Location via Nominatim/OSM • Mandi via transparent estimator.</div>
        </footer>
      </main>
    </div>
  );
}

export default function Page(){
  return (
    <AuthGuard>
      <AppContent />
    </AuthGuard>
  );
}