// Levels (module/levels.py has the rules): reaching level n takes 50·(n−1)² exp.
import { h } from "./dom.js";

const STEP = 50;
export const FRAME_LEVEL = 5; // avatar frame from this level

export const expFor = (level) => STEP * (level - 1) ** 2;

/** { level, progress (0–1 through this level), next (total exp for the next level) } */
export function levelOf(exp) {
  const safe = Math.max(Number(exp) || 0, 0);
  const level = Math.floor(Math.sqrt(Math.floor(safe / STEP))) + 1;
  const from = expFor(level);
  const next = expFor(level + 1);
  return { level, progress: (safe - from) / (next - from), next };
}

/** The colour tier: Lv 1–2 plain, 3–4 green, 5–9 blue, 10–19 purple, 20+ gold. */
export function tierOf(level) {
  if (level >= 20) return "gold";
  if (level >= 10) return "purple";
  if (level >= 5) return "blue";
  if (level >= 3) return "green";
  return "plain";
}

/** A small "Lv 5" badge; nothing for an unknown level (anonymous authors). */
export function levelBadge(level) {
  if (!level) return null;
  return h("span", { class: `lv lv--${tierOf(level)}`, title: `等級 ${level}` }, `Lv ${level}`);
}

/** Frame class for an avatar at this level. */
export function frameClass(level) {
  return level >= FRAME_LEVEL ? ` avatar--frame avatar--${tierOf(level)}` : "";
}
