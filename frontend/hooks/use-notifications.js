'use client';
import { useCallback, useEffect, useState } from 'react';

// Smart notification engine: turns weather + irrigation data into plain-language
// alerts for the farmer (e.g. "rain expected, skip watering", "time to water").
// Notifications persist to localStorage per session so the bell keeps history.

function storageKey(sessionId) {
  return `agri_notifications_${sessionId || 'default'}`;
}

function load(sessionId) {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(storageKey(sessionId)) || '[]');
  } catch {
    return [];
  }
}

function save(sessionId, list) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(storageKey(sessionId), JSON.stringify(list.slice(0, 30)));
}

export function useNotifications(sessionId) {
  const [items, setItems] = useState([]);

  useEffect(() => {
    setItems(load(sessionId));
  }, [sessionId]);

  const push = useCallback((notif) => {
    setItems((prev) => {
      // avoid duplicate alerts of the same kind within a short window
      if (prev.some((p) => p.key === notif.key && Date.now() - p.ts < 6 * 60 * 60 * 1000)) return prev;
      const next = [{ id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`, ts: Date.now(), read: false, ...notif }, ...prev];
      save(sessionId, next);
      return next;
    });
  }, [sessionId]);

  const markAllRead = useCallback(() => {
    setItems((prev) => {
      const next = prev.map((n) => ({ ...n, read: true }));
      save(sessionId, next);
      return next;
    });
  }, [sessionId]);

  const clear = useCallback(() => {
    setItems([]);
    save(sessionId, []);
  }, [sessionId]);

  const unreadCount = items.filter((n) => !n.read).length;

  return { items, push, markAllRead, clear, unreadCount };
}

// Derives smart farming alerts from the latest weather + irrigation payloads.
export function buildSmartAlerts({ weather, irrigation, crop, lang }) {
  const alerts = [];
  const rain7 = weather?.summary?.rain7;
  const willRainSoon = (weather?.data?.daily?.precipitation_sum || []).slice(0, 2).some((mm) => mm >= 5);
  const heat = weather?.summary?.heat;

  if (willRainSoon) {
    alerts.push({
      key: `rain_${crop || 'all'}`,
      icon: 'rain',
      level: 'info',
      title: 'Rain expected soon',
      message: `Rain is likely in the next 2 days${crop ? ` for your ${crop}` : ''} — you can skip today's irrigation and save water.`,
    });
  } else if (irrigation?.schedule?.some((s) => s.day === 0 && !String(s.action).toLowerCase().includes('skip'))) {
    alerts.push({
      key: `water_${crop || 'all'}`,
      icon: 'droplet',
      level: 'action',
      title: 'Time to water your crop',
      message: `No rain expected today — irrigate${crop ? ` your ${crop}` : ' your field'} as per today's schedule.`,
    });
  }

  if (heat >= 38) {
    alerts.push({
      key: `heat_${crop || 'all'}`,
      icon: 'sun',
      level: 'warning',
      title: 'High heat alert',
      message: `Temperatures are climbing to ${Math.round(heat)}°C — water early morning or evening to reduce stress.`,
    });
  }

  if (rain7 >= 60) {
    alerts.push({
      key: `flood_${crop || 'all'}`,
      icon: 'rain',
      level: 'warning',
      title: 'Heavy rain risk this week',
      message: 'Check field drainage and delay fertilizer/pesticide spraying until the rain eases.',
    });
  }

  if (weather?.risks?.length) {
    weather.risks.forEach((r) => {
      alerts.push({
        key: `risk_${r.id}`,
        icon: r.level === 'high' ? 'warning' : 'info',
        level: r.level === 'high' ? 'warning' : 'info',
        title: 'Weather risk',
        message: r.msg,
      });
    });
  }

  return alerts;
}
