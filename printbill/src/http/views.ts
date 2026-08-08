/** Minimal server-rendered page shell for the few customer-facing pages. */
import { seller } from '../config/env.js';

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function page(title: string, body: string): string {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>${escapeHtml(title)} · ${escapeHtml(seller.tradeName)}</title>
<style>
  :root {
    --bg: #f6f7f9; --card: #ffffff; --ink: #16181d; --muted: #6b7280;
    --accent: #0f766e; --line: #e5e7eb;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0f1115; --card: #171a21; --ink: #e8eaed; --muted: #9aa3af;
            --accent: #2dd4bf; --line: #262b35; }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; background: var(--bg); color: var(--ink);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex; justify-content: center; align-items: flex-start; min-height: 100vh;
  }
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 28px; max-width: 420px; width: 100%; margin-top: 6vh;
    box-shadow: 0 1px 2px rgba(0,0,0,.05), 0 8px 24px rgba(0,0,0,.04);
  }
  .center { text-align: center; }
  h1 { font-size: 1.6rem; margin: 0 0 8px; letter-spacing: -0.02em; }
  p { margin: 8px 0; }
  .muted { color: var(--muted); }
  .small { font-size: .82rem; }
  .price { font-size: 1.5rem; font-weight: 650; color: var(--accent); }
  .hero { width: 100%; border-radius: 10px; margin-bottom: 16px; display: block; }
  .tick {
    width: 56px; height: 56px; border-radius: 50%; background: var(--accent);
    color: #fff; font-size: 30px; line-height: 56px; margin: 0 auto 12px;
  }
  .button {
    display: block; width: 100%; text-align: center; margin-top: 14px; padding: 13px 18px;
    background: var(--accent); color: #fff; border: 0; border-radius: 10px;
    font-size: 1rem; font-weight: 600; cursor: pointer; text-decoration: none;
  }
  .button.ghost { background: transparent; color: var(--muted); border: 1px solid var(--line); }
  label { display: block; margin-top: 14px; font-size: .85rem; color: var(--muted); }
  select {
    width: 100%; margin-top: 6px; padding: 11px; border-radius: 9px;
    border: 1px solid var(--line); background: var(--bg); color: var(--ink); font-size: 1rem;
  }
</style>
</head>
<body>${body}</body>
</html>`;
}
