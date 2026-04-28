# UI Styles — Reference

This file is loaded by `SKILL.md` when a style decision is needed.

The real `ui-ux-pro-max` skill has 50+ styles — below is an excerpt showing structure.

---

## Glassmorphism
- **Look:** frosted glass, backdrop blur, translucent cards
- **Tokens:** `backdrop-blur-xl`, `bg-white/10`, subtle borders
- **Good for:** landing pages, creative portfolios, music/video apps
- **Avoid for:** accessibility-critical dashboards (contrast issues)

## Neumorphism
- **Look:** soft shadows, embossed or inset surfaces, pastel palettes
- **Tokens:** `shadow-inner`, `shadow-lg`, soft pastel bg
- **Good for:** control panels, finance apps, calculator UIs
- **Avoid for:** text-heavy content (contrast often fails)

## Brutalism
- **Look:** sharp edges, high contrast, raw typography-first
- **Tokens:** thick borders (`border-2`), no rounding, mono fonts
- **Good for:** brand sites, portfolios, editorial
- **Avoid for:** consumer apps needing warmth

## Bento Grid
- **Look:** varied-size cards in a modular grid, Apple-inspired
- **Tokens:** `grid-cols-12`, varying `col-span`, rounded corners
- **Good for:** product pages, feature showcases, modern landings
- **Avoid for:** data-heavy dashboards

## Minimalism
- **Look:** generous whitespace, single accent color, clear hierarchy
- **Tokens:** `max-w-prose`, subtle dividers, one vibrant color
- **Good for:** SaaS landings, B2B, serious business sites
- **Avoid for:** consumer-fun contexts (feels cold)

## Matrix / Terminal
- **Look:** monospace, black bg, neon accent (green/orange)
- **Tokens:** `font-mono`, scanlines, matrix rain bg
- **Good for:** dev tools, CTF challenges, technical demos
- **Avoid for:** general consumer

## Dark Mode First
- **Look:** dark bg default, high-contrast text
- **Tokens:** `bg-slate-950`, `text-slate-100`, accent color
- **Good for:** dev tools, content consumption, ergonomic apps
- **Avoid for:** printable content, medical apps

## Flat Design
- **Look:** no shadows/gradients, solid colors, clean shapes
- **Tokens:** flat `bg-*`, no `shadow-*`, no gradients
- **Good for:** Material apps, utility UIs
- **Avoid for:** luxury/premium feel

*(In the real skill, 50+ styles with more detail — this is an excerpt)*
