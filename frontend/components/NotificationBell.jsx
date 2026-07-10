'use client';
import { useState } from 'react';
import { Bell, CloudRain, Droplets, Sun, AlertTriangle, Info, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ICONS = { rain: CloudRain, droplet: Droplets, sun: Sun, warning: AlertTriangle, info: Info };
const LEVEL_STYLE = {
  action: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  warning: 'border-amber-200 bg-amber-50 text-amber-900',
  info: 'border-sky-200 bg-sky-50 text-sky-900',
};

export default function NotificationBell({ items = [], unreadCount = 0, onOpen, onClear }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        className="relative h-10 w-10 rounded-full"
        onClick={() => {
          const next = !open;
          setOpen(next);
          if (next) onOpen?.();
        }}
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-rose-600 text-[10px] leading-4 text-white font-semibold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-auto rounded-2xl border border-emerald-100 bg-white shadow-xl z-50 animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center justify-between px-4 py-3 border-b border-emerald-50">
            <span className="text-sm font-semibold text-emerald-950">Smart notifications</span>
            <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-600">
              <X className="h-4 w-4" />
            </button>
          </div>
          {items.length === 0 ? (
            <div className="px-4 py-8 text-center text-xs text-slate-500">
              No alerts yet — we'll notify you about watering, rain and crop risks here.
            </div>
          ) : (
            <div className="divide-y divide-emerald-50">
              {items.map((n) => {
                const Icon = ICONS[n.icon] || Info;
                return (
                  <div key={n.id} className={`px-4 py-3 flex gap-3 ${!n.read ? 'bg-emerald-50/40' : ''}`}>
                    <div className={`h-8 w-8 shrink-0 rounded-full border grid place-items-center ${LEVEL_STYLE[n.level] || LEVEL_STYLE.info}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-emerald-950">{n.title}</p>
                      <p className="text-xs text-slate-600 mt-0.5">{n.message}</p>
                      <p className="text-[10px] text-slate-400 mt-1">{new Date(n.ts).toLocaleString()}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {items.length > 0 && (
            <div className="px-4 py-2 border-t border-emerald-50 text-right">
              <button onClick={onClear} className="text-xs text-slate-500 hover:text-rose-600">Clear all</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
