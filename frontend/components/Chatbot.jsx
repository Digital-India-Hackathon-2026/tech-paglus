'use client';

// Floating "Raithu Anna" support chatbot.
// Speaks whatever language the farmer picked at signup/login (via useLanguage),
// answers common questions with simple rule-based replies, and always offers
// a one-tap call to human support for anything it can't confidently answer.

import { useEffect, useRef, useState } from 'react';
import { MessageCircle, X, Send, Phone } from 'lucide-react';
import { useLanguage } from '@/lib/language';

const SUPPORT_TEL = 'tel:1800000000';
const SUPPORT_NUMBER_DISPLAY = '1800 000 0000';

const QUICK_OPTIONS = [
  { key: 'disease', icon: '🌿' },
  { key: 'pest', icon: '🐛' },
  { key: 'water', icon: '💧' },
  { key: 'fertilizer', icon: '🧪' },
  { key: 'weather', icon: '☀️' },
  { key: 'market', icon: '📈' },
  { key: 'schemes', icon: '📋' },
  { key: 'expert', icon: '👨‍🌾' },
];

const QUICK_LABEL_KEY = {
  disease: 'chatCropDisease', pest: 'chatPest', water: 'chatWater', fertilizer: 'chatFertilizer',
  weather: 'chatWeather', market: 'chatMarket', schemes: 'chatSchemes', expert: 'chatExpert',
};

function classify(rawQuestion) {
  const q = rawQuestion.toLowerCase();
  if (/(expert|call|difficult|help me talk)/.test(q)) return 'expert';
  if (/(disease|spot|pest|leaf|कीट|रोग|पत्ती|పురుగు|వ్యాధి|ఆకు)/.test(q)) return 'disease';
  if (/(water|irrigation|पानी|सिंचाई|నీరు|నీటిపారుదల)/.test(q)) return 'water';
  if (/(fertilizer|urea|उर्वरक|खाद|ఎరువు)/.test(q)) return 'fertilizer';
  if (/(weather|rain|मौसम|बारिश|వాతావరణం|వర్షం)/.test(q)) return 'weather';
  if (/(price|market|भाव|मंडी|ధర|మార్కెట్)/.test(q)) return 'market';
  if (/(scheme|government|योजना|सरकार|పథకం|ప్రభుత్వ)/.test(q)) return 'schemes';
  return 'default';
}

const ANSWER_KEY = {
  expert: 'chatAnsExpert', disease: 'chatAnsDisease', water: 'chatAnsWater',
  fertilizer: 'chatAnsFertilizer', weather: 'chatAnsWeather', market: 'chatAnsMarket',
  schemes: 'chatAnsSchemes', default: 'chatAnsDefault',
};

export default function Chatbot() {
  const { tr, lang } = useLanguage();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const scrollRef = useRef(null);

  // Reset the greeting whenever the language changes so the whole
  // conversation UI (not just new replies) matches the chosen language.
  useEffect(() => {
    setMessages([{ role: 'bot', text: tr('chatbotGreeting') }]);
  }, [lang, tr]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, open]);

  function reply(question) {
    const type = classify(question);
    return tr(ANSWER_KEY[type]);
  }

  function send(question) {
    const text = question.trim();
    if (!text) return;
    setMessages((m) => [...m, { role: 'user', text }]);
    setInput('');
    setTimeout(() => {
      setMessages((m) => [...m, { role: 'bot', text: reply(text) }]);
    }, 350);
  }

  function onSubmit(e) {
    e.preventDefault();
    send(input);
  }

  return (
    <>
      {/* Launcher */}
      <button
        type="button"
        aria-label={tr('chatbotName')}
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-50 flex h-16 w-16 items-center justify-center rounded-full border-4 border-primary bg-white text-primary shadow-xl transition hover:scale-105"
      >
        {open ? <X className="h-7 w-7" /> : <span className="text-3xl">👨‍🌾</span>}
        {!open && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive">
            <MessageCircle className="h-2.5 w-2.5 text-white" />
          </span>
        )}
      </button>

      {/* Chat window */}
      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex max-h-[80vh] w-[min(370px,calc(100vw-2rem))] flex-col overflow-hidden rounded-3xl bg-white shadow-2xl">
          <div className="flex items-center gap-3 bg-primary px-4 py-3 text-primary-foreground">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-xl">👨‍🌾</span>
            <span className="text-lg font-bold">{tr('chatbotName')}</span>
            <button type="button" onClick={() => setOpen(false)} className="ml-auto text-2xl leading-none">×</button>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto bg-muted/40 p-3" style={{ minHeight: 200, maxHeight: 260 }}>
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === 'bot'
                    ? 'max-w-[86%] rounded-2xl rounded-tl-sm bg-secondary px-3 py-2 text-sm leading-snug text-secondary-foreground'
                    : 'ml-auto max-w-[86%] rounded-2xl rounded-tr-sm bg-primary px-3 py-2 text-sm leading-snug text-primary-foreground'
                }
              >
                {m.text}
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-1.5 border-t border-border bg-white px-3 py-2">
            {QUICK_OPTIONS.map((o) => (
              <button
                key={o.key}
                type="button"
                onClick={() => send(`${o.icon} ${tr(QUICK_LABEL_KEY[o.key])}`)}
                className="rounded-full border border-border px-2.5 py-1.5 text-xs font-semibold text-primary hover:bg-secondary"
              >
                {o.icon} {tr(QUICK_LABEL_KEY[o.key])}
              </button>
            ))}
          </div>

          <a
            href={SUPPORT_TEL}
            className="mx-3 mt-2 flex items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-bold text-primary-foreground"
          >
            <Phone className="h-4 w-4" /> {tr('chatCallSupport')}
          </a>
          <div className="pb-1 pt-1 text-center text-xs text-muted-foreground">
            {tr('chatSupportNumber')}: {SUPPORT_NUMBER_DISPLAY}
          </div>

          <form onSubmit={onSubmit} className="flex items-center gap-2 border-t border-border p-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={tr('chatInputPlaceholder')}
              className="flex-1 rounded-xl border-0 bg-muted px-3 py-2 text-sm outline-none"
            />
            <button type="submit" className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
