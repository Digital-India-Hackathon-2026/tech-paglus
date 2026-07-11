'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Camera, MessageCircle, HandHeart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import AuthGuard from '@/components/AuthGuard';

const CATEGORY_OPTIONS = [
  'Crop disease/pest',
  'Soil & fertilizer',
  'Water & irrigation',
  'Market / selling',
  'Weather damage',
  'Other',
];

const TAG_STYLES = {
  'Crop disease/pest': 'bg-amber-700',
  'Soil & fertilizer': 'bg-emerald-700',
  'Water & irrigation': 'bg-sky-700',
  'Market / selling': 'bg-orange-600',
  'Weather damage': 'bg-sky-700',
  Other: 'bg-slate-600',
};

const SEED_POSTS = [
  {
    id: 'seed-1',
    name: 'Ramesh N.',
    loc: 'Uppal Kalan, Telangana',
    time: '2 hrs ago',
    tag: 'Crop disease/pest',
    text: 'White spots spreading on my cotton leaves after the last rain. Anyone seen this before? Worried it will spread to the whole field.',
    img: null,
    helped: false,
    comments: [{ name: 'Lakshmi P.', text: 'Looks like fungal leaf spot. Try a copper-based spray after checking with your local agri officer.' }],
  },
  {
    id: 'seed-2',
    name: 'Suresh K.',
    loc: 'Nalgonda, Telangana',
    time: '5 hrs ago',
    tag: 'Water & irrigation',
    text: 'Borewell water level dropping fast this month. How are others managing irrigation timing for paddy right now?',
    img: null,
    helped: false,
    comments: [],
  },
  {
    id: 'seed-3',
    name: 'Anita R.',
    loc: 'Warangal, Telangana',
    time: '1 day ago',
    tag: 'Market / selling',
    text: 'Got a good rate for turmeric at Nizamabad mandi this week — sharing in case it helps others decide when to sell.',
    img: null,
    helped: false,
    comments: [{ name: 'Ramesh N.', text: 'Thanks for sharing, was planning to sell next week too.' }],
  },
];

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function CommunityContent() {
  const router = useRouter();
  const [posts, setPosts] = useState(SEED_POSTS);
  const [text, setText] = useState('');
  const [loc, setLoc] = useState('');
  const [category, setCategory] = useState(CATEGORY_OPTIONS[0]);
  const [photo, setPhoto] = useState(null); // { dataUrl, mimeType }
  const [detecting, setDetecting] = useState(false);
  const [detectedLabel, setDetectedLabel] = useState('');
  const [openComments, setOpenComments] = useState({});
  const [replyDrafts, setReplyDrafts] = useState({});

  async function handlePhoto(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const dataUrl = await fileToBase64(file);
    setPhoto({ dataUrl, mimeType: file.type });
    setDetectedLabel('');
    setDetecting(true);

    try {
      const base64Data = dataUrl.split(',')[1];
      const res = await fetch('/api/detect-category', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base64Data, mimeType: file.type }),
      });
      const data = await res.json();
      if (data.category) {
        setCategory(data.category);
        setDetectedLabel(data.category);
      }
    } catch (err) {
      console.error('Category detection failed:', err);
    } finally {
      setDetecting(false);
    }
  }

  function postProblem() {
    const trimmed = text.trim();
    if (!trimmed) return;
    const newPost = {
      id: `post-${Date.now()}`,
      name: 'You',
      loc: loc.trim() || 'Location not shared',
      time: 'just now',
      tag: category,
      text: trimmed,
      img: photo?.dataUrl || null,
      helped: false,
      comments: [],
    };
    setPosts((prev) => [newPost, ...prev]);
    setText('');
    setLoc('');
    setPhoto(null);
    setDetectedLabel('');
    setCategory(CATEGORY_OPTIONS[0]);
  }

  function toggleHelp(id) {
    setPosts((prev) => prev.map((p) => (p.id === id ? { ...p, helped: !p.helped } : p)));
  }

  function toggleComments(id) {
    setOpenComments((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function addComment(id) {
    const draft = (replyDrafts[id] || '').trim();
    if (!draft) return;
    setPosts((prev) =>
      prev.map((p) => (p.id === id ? { ...p, comments: [...p.comments, { name: 'You', text: draft }] } : p))
    );
    setReplyDrafts((prev) => ({ ...prev, [id]: '' }));
  }

  return (
    <div className="min-h-screen bg-emerald-50/40">
      <header className="border-b border-emerald-100 bg-white">
        <div className="mx-auto max-w-2xl px-5 py-5 flex items-center gap-3">
          <button onClick={() => router.push('/')} className="flex items-center gap-1.5 text-emerald-800 hover:text-emerald-950 text-sm font-medium">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">Community</p>
            <h1 className="text-xl font-bold text-emerald-950">Ask. Show. Solve.</h1>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-5 py-8">
        {/* Composer */}
        <div className="mb-8 rounded-xl border border-emerald-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold text-emerald-950">Share a problem</h2>
          <p className="mb-4 text-sm text-emerald-800/70">A clear photo helps others answer faster.</p>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. Leaves on my tomato plants are curling and turning yellow since last week's rain..."
            className="mb-4 min-h-[90px] w-full resize-y rounded-lg border border-emerald-200 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />

          <label className="mb-4 flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-emerald-300 bg-emerald-50 p-4 text-sm font-medium text-emerald-800 hover:bg-emerald-100">
            <Camera className="h-4 w-4" />
            {detecting ? 'Reading photo to guess the category…' : photo ? 'Photo added — tap to change' : 'Tap to add a photo of the problem'}
            <input type="file" accept="image/*" onChange={handlePhoto} className="hidden" />
          </label>
          {photo && (
            <div className="mb-4 flex items-center gap-3">
              <img src={photo.dataUrl} alt="Attached" className="h-16 w-16 rounded-lg border border-emerald-200 object-cover" />
              {detectedLabel && <span className="text-xs font-medium text-emerald-700">✅ Guessed: {detectedLabel} (change below if wrong)</span>}
            </div>
          )}

          <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-emerald-700">Crop / category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-lg border border-emerald-200 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-emerald-700">Your village/district</label>
              <input
                type="text"
                value={loc}
                onChange={(e) => setLoc(e.target.value)}
                placeholder="e.g. Uppal Kalan, Telangana"
                className="w-full rounded-lg border border-emerald-200 p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>
          </div>

          <Button onClick={postProblem} className="h-11 px-6 bg-emerald-600 hover:bg-emerald-700">Post to community</Button>
        </div>

        {/* Feed */}
        <div className="mb-4 flex items-baseline justify-between border-b-2 border-emerald-900/10 pb-2">
          <h2 className="text-lg font-bold text-emerald-950">Recent from your community</h2>
          <span className="text-xs font-medium text-emerald-700">{posts.length} posts</span>
        </div>

        <div className="space-y-4">
          {posts.map((p) => (
            <div key={p.id} className="rounded-xl border border-emerald-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-200 font-bold text-amber-900">{p.name.charAt(0)}</div>
                  <div>
                    <div className="text-sm font-semibold text-emerald-950">{p.name}</div>
                    <div className="text-xs text-emerald-700/70">{p.loc} · {p.time}</div>
                  </div>
                </div>
                <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-medium text-white ${TAG_STYLES[p.tag] || 'bg-slate-600'}`}>{p.tag}</span>
              </div>

              <p className="mb-3 text-sm leading-relaxed text-emerald-950">{p.text}</p>
              {p.img && <img src={p.img} alt="Attachment" className="mb-3 max-h-72 w-full rounded-lg border border-emerald-200 object-cover" />}

              <div className="flex gap-4 border-t border-dashed border-emerald-200 pt-3 text-xs">
                <button onClick={() => toggleHelp(p.id)} className={`flex items-center gap-1 font-medium ${p.helped ? 'text-emerald-700' : 'text-emerald-700/60 hover:text-emerald-900'}`}>
                  <HandHeart className="h-3.5 w-3.5" /> {p.helped ? 'Offered to help' : 'I can help'}
                </button>
                <button onClick={() => toggleComments(p.id)} className="flex items-center gap-1 font-medium text-emerald-700/60 hover:text-emerald-900">
                  <MessageCircle className="h-3.5 w-3.5" /> {p.comments.length} replies
                </button>
              </div>

              {openComments[p.id] && (
                <div className="mt-3 space-y-2">
                  {p.comments.map((c, i) => (
                    <div key={i} className="border-t border-dashed border-emerald-100 pt-2 text-sm">
                      <b>{c.name}:</b> {c.text}
                    </div>
                  ))}
                  <div className="flex gap-2 pt-1">
                    <input
                      type="text"
                      value={replyDrafts[p.id] || ''}
                      onChange={(e) => setReplyDrafts((prev) => ({ ...prev, [p.id]: e.target.value }))}
                      onKeyDown={(e) => e.key === 'Enter' && addComment(p.id)}
                      placeholder="Write a reply..."
                      className="flex-1 rounded-lg border border-emerald-200 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                    />
                    <button onClick={() => addComment(p.id)} className="rounded-lg bg-emerald-900 px-3 text-xs font-medium text-white">Reply</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </main>

      <footer className="mx-auto max-w-2xl px-5 py-8 text-xs text-emerald-700/60">
        Built for farmers, by the community. Photos help — but never share personal documents or ID here.
      </footer>
    </div>
  );
}

export default function CommunityPage() {
  return (
    <AuthGuard>
      <CommunityContent />
    </AuthGuard>
  );
}
