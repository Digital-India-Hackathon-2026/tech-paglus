'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Bug, Camera, Cpu, Leaf, Loader2, Play, RefreshCw, ShieldAlert, Square, ThermometerSun, Upload } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import AuthGuard from '@/components/AuthGuard';

function riskColor(level) {
  if (level === 'high') return 'bg-rose-600';
  if (level === 'medium') return 'bg-amber-500';
  if (level === 'unknown') return 'bg-slate-500';
  return 'bg-emerald-600';
}

function DetectionOverlay({ detections }) {
  return (
    <div className="absolute inset-0 pointer-events-none">
      {(detections || []).map((d, idx) => {
        const [x, y, w, h] = d.bbox || [0.1, 0.1, 0.4, 0.3];
        return (
          <div
            key={`${d.label}-${idx}`}
            className="absolute rounded-md border-2 border-amber-300 shadow-[0_0_0_9999px_rgba(0,0,0,0.10)]"
            style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%` }}
          >
            <span className="absolute -top-7 left-0 rounded bg-amber-400 px-2 py-1 text-[10px] font-bold text-slate-900 shadow">
              {d.label} · {Math.round((d.confidence || 0) * 100)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

function PestGuardContent() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  const [cameraOn, setCameraOn] = useState(false);
  const [liveMode, setLiveMode] = useState(false);
  const [thermalStyle, setThermalStyle] = useState(false);
  const [cameraMode, setCameraMode] = useState('rgb');
  const [crop, setCrop] = useState('cotton');
  const [result, setResult] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => () => stopCamera(), []);

  async function startCamera() {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraOn(true);
    } catch (err) {
      setError('Camera permission failed. Open this page on your phone through HTTPS/ngrok, then allow camera permission.');
    }
  }

  function stopCamera() {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
    setLiveMode(false);
    if (streamRef.current) streamRef.current.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOn(false);
  }

  async function uploadBlob(blob, filename = 'camera-frame.jpg') {
    setLoading(true);
    setError('');
    try {
      const fd = new FormData();
      fd.append('file', blob, filename);
      fd.append('crop', crop || 'unknown crop');
      fd.append('camera_mode', cameraMode);
      const response = await fetch('/api/pest-animal-detect', { method: 'POST', body: fd });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.detail || data.error || 'Detection failed');
      setResult(data);
    } catch (err) {
      setError(err.message || 'Detection failed');
    } finally {
      setLoading(false);
    }
  }

  async function captureFrame() {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const w = video.videoWidth || 1280;
    const h = video.videoHeight || 720;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, w, h);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.86));
    if (!blob) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(blob));
    await uploadBlob(blob, `${cameraMode}-camera-frame.jpg`);
  }

  function toggleLive() {
    if (!cameraOn) return;
    if (liveMode) {
      setLiveMode(false);
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
      return;
    }
    setLiveMode(true);
    captureFrame();
    intervalRef.current = setInterval(captureFrame, 4500);
  }

  async function onPhotoUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    await uploadBlob(file, file.name || 'crop-photo.jpg');
  }

  const detections = result?.detections || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-lime-50 to-amber-50">
      <main className="container mx-auto space-y-5 px-4 py-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <a href="/" className="inline-flex items-center gap-1 text-sm font-medium text-emerald-800 hover:underline">
              <ArrowLeft className="h-4 w-4" /> Back to AgriSarthi
            </a>
            <h1 className="mt-2 flex items-center gap-2 text-2xl font-bold text-emerald-950 md:text-3xl">
              <Bug className="h-7 w-7 text-emerald-700" /> Neural Pest & Animal Guard
            </h1>
            <p className="mt-1 text-sm text-emerald-800/75">
              Use your OnePlus camera as the live input, send frames to the laptop backend, and get NN pest report + natural crop-care plan.
            </p>
          </div>
          <Badge className="w-fit bg-emerald-700"><Cpu className="mr-1 h-3 w-3" /> NN-ready detector</Badge>
        </div>

        <section className="grid gap-4 lg:grid-cols-3">
          <Card className="border-emerald-200 lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base"><Camera className="h-4 w-4 text-emerald-700" /> Phone camera / photo input</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <label className="text-xs font-semibold text-emerald-900">Crop</label>
                  <Input value={crop} onChange={(e) => setCrop(e.target.value)} placeholder="cotton, paddy, chilli..." />
                </div>
                <div>
                  <label className="text-xs font-semibold text-emerald-900">Camera mode</label>
                  <select className="h-10 w-full rounded-md border bg-white px-3 text-sm" value={cameraMode} onChange={(e) => setCameraMode(e.target.value)}>
                    <option value="rgb">Normal RGB camera</option>
                    <option value="near_ir_like">IR / night-camera style frame</option>
                    <option value="thermal_external">External thermal camera frame</option>
                  </select>
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[11px] text-amber-900">
                  Real thermal detection needs a calibrated thermal camera feed. Phone IR/night frames are useful only if the NN model is trained on similar images.
                </div>
              </div>

              <div className="relative aspect-video overflow-hidden rounded-2xl border bg-black">
                <video ref={videoRef} muted playsInline className={`h-full w-full object-cover ${thermalStyle ? 'grayscale contrast-150 sepia saturate-200' : ''}`} />
                {!cameraOn && previewUrl && <img src={previewUrl} alt="Uploaded crop preview" className={`h-full w-full object-cover ${thermalStyle ? 'grayscale contrast-150 sepia saturate-200' : ''}`} />}
                {!cameraOn && !previewUrl && (
                  <div className="absolute inset-0 grid place-items-center p-6 text-center text-white/80">
                    <div>
                      <Camera className="mx-auto mb-3 h-12 w-12" />
                      <p className="font-semibold">Start phone rear camera or upload crop photo</p>
                      <p className="mt-1 text-xs text-white/60">Capture leaf underside, stem base, fruits/bolls and damaged crop area.</p>
                    </div>
                  </div>
                )}
                {(cameraOn || previewUrl) && <DetectionOverlay detections={detections} />}
                {loading && (
                  <div className="absolute inset-0 grid place-items-center bg-black/40 text-white">
                    <div className="flex items-center gap-2 rounded-full bg-black/60 px-4 py-2 text-sm"><Loader2 className="h-4 w-4 animate-spin" /> neural scan running…</div>
                  </div>
                )}
              </div>

              <canvas ref={canvasRef} className="hidden" />

              <div className="flex flex-wrap gap-2">
                {!cameraOn ? (
                  <Button onClick={startCamera} className="bg-emerald-600 hover:bg-emerald-700"><Camera className="mr-2 h-4 w-4" /> Start camera</Button>
                ) : (
                  <Button onClick={stopCamera} variant="destructive"><Square className="mr-2 h-4 w-4" /> Stop camera</Button>
                )}
                <Button onClick={captureFrame} disabled={!cameraOn || loading} variant="secondary"><RefreshCw className="mr-2 h-4 w-4" /> Scan frame</Button>
                <Button onClick={toggleLive} disabled={!cameraOn || loading} variant={liveMode ? 'destructive' : 'outline'}>
                  {liveMode ? <Square className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}{liveMode ? 'Stop live scan' : 'Live scan every 4.5s'}
                </Button>
                <label className="inline-flex cursor-pointer items-center rounded-md border bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50">
                  <Upload className="mr-2 h-4 w-4" /> Upload photo
                  <input type="file" accept="image/*" capture="environment" className="hidden" onChange={onPhotoUpload} />
                </label>
                <Button onClick={() => setThermalStyle((v) => !v)} variant="outline">
                  <ThermometerSun className="mr-2 h-4 w-4" /> {thermalStyle ? 'Normal view' : 'Thermal-style preview'}
                </Button>
              </div>

              {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
            </CardContent>
          </Card>

          <Card className="border-emerald-200">
            <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><ShieldAlert className="h-4 w-4 text-amber-600" /> NN report</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {!result ? (
                <p className="text-sm text-slate-600">Scan a frame or upload a crop photo to get a pest/animal report.</p>
              ) : (
                <>
                  <div className="rounded-xl border bg-white p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-semibold text-slate-800">Overall risk</span>
                      <Badge className={riskColor(result.severity)}>{result.severity}</Badge>
                    </div>
                    <Progress value={result.overallRisk || 0} className="h-2" />
                    <p className="mt-2 text-sm text-slate-700">{result.summary}</p>
                    <div className="mt-2 rounded-md bg-slate-50 p-2 text-[11px] text-slate-600">
                      Model: {result.model?.type || 'unknown'} · {result.model?.status || 'unknown'}
                    </div>
                  </div>

                  {!result.modelReady && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                      Neural model is not connected yet. Add <b>backend/ml_models/pest_classifier.onnx</b> or set Roboflow API values in backend <b>.env</b>.
                    </div>
                  )}

                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-emerald-900">Detected classes</h3>
                    {detections.length === 0 ? (
                      <div className="rounded-lg border bg-slate-50 p-3 text-sm text-slate-700">No class prediction yet.</div>
                    ) : (
                      <div className="space-y-2">
                        {detections.map((d, idx) => (
                          <div key={idx} className="rounded-lg border bg-white p-3 text-sm">
                            <div className="flex items-center justify-between gap-2">
                              <div className="font-semibold text-slate-900">{d.label}</div>
                              <Badge className={riskColor(d.severity)}>{d.severity}</Badge>
                            </div>
                            <div className="mt-1 text-xs text-slate-600">Confidence: {Math.round((d.confidence || 0) * 100)}%</div>
                            <p className="mt-2 text-xs text-slate-700">{d.note}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-emerald-900"><Leaf className="h-4 w-4" /> Natural / crop-care actions</h3>
                    <ul className="list-disc space-y-1 pl-4 text-xs text-slate-700">
                      {(result.recommendations || []).slice(0, 8).map((r, idx) => <li key={idx}>{r}</li>)}
                    </ul>
                  </div>

                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-emerald-900">Crop-relevant fertiliser / soil inputs</h3>
                    <ul className="list-disc space-y-1 pl-4 text-xs text-slate-700">
                      {(result.naturalFertiliserPlan || []).slice(0, 8).map((r, idx) => <li key={idx}>{r}</li>)}
                    </ul>
                  </div>

                  <div className="rounded-lg border bg-slate-50 p-3 text-[11px] text-slate-600">{result.thermalNote}</div>
                </>
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

export default function PestGuardPage() {
  return (
    <AuthGuard>
      <PestGuardContent />
    </AuthGuard>
  );
}
