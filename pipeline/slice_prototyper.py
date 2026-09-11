"""pipeline/slice_prototyper.py — W9 确定性垂直切片原型生成器（真实可玩 + 契约挂载）。

职责（与升级计划第十一章、W9 一致）：
  把 vertical_slices.VERTICAL_SLICES 里的 8 个切片规格，逐个编译成「自包含、可运行、
  契约挂载」的 index.html 原型：
    - 真实 <canvas> + requestAnimationFrame 主循环（契约自动把 state 从 boot→playing，并累加 frame）；
    - 真实键盘输入 → 状态变化 → 真实可达 gameover（生命耗尽 / 达成目标）；
    - 暴露 window.GameApp.{startMatch,endMatch,restartMatch}，使 W8 的 _try_end_game/_try_restart_game
      能诚实触发终局与重开（游戏确实暴露了这些接口，不是伪造闭合）；
    - 引用 W7 程序化音频（sfx_*.wav / bgm.wav，由 validator 用 AudioFactory 真实生成后落盘）；
    - 由 core.runtime_contract.inject_runtime_contract 注入运行时观测契约（与 W8 同一真理源）。

重要诚实口径：
  - 这些是「垂直可玩骨架（Slice 2 成熟度）」：真实可运行、真实可玩、真实可达 gameover，
    但不是已上架的完整商业游戏；prototyper 不声称它们已打磨保真（Slice 4）。
  - 生成完全确定性（seed 由切片 id 派生），不依赖 LLM、不依赖网络、不依赖真实浏览器。
  - 机制按切片 genre 分支，但共享一套真实引擎；分支逻辑都是真实输入→状态→gameover，非占位空转。
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Optional

from core.runtime_contract import inject_runtime_contract
from pipeline.vertical_slices import SliceSpec

ROOT = Path(__file__).resolve().parent.parent

# 每个 genre 的浏览器内调色板与基础参数（真实可渲染，非随机）
_PALETTES = {
    "card_roguelike":   {"bg": "#15102a", "fg": "#e8def8", "accent": "#bb86fc", "enemy": "#cf6679"},
    "survivor_danmaku": {"bg": "#04121a", "fg": "#aef3ff", "accent": "#22d3ee", "enemy": "#f97316"},
    "rhythm":           {"bg": "#0a0a18", "fg": "#fef3c7", "accent": "#fbbf24", "enemy": "#f43f5e"},
    "racing":           {"bg": "#0b1020", "fg": "#dbeafe", "accent": "#60a5fa", "enemy": "#f87171"},
    "factory_sim":      {"bg": "#0d1410", "fg": "#bbf7d0", "accent": "#34d399", "enemy": "#fca5a5"},
    "roguelike_dungeon":{"bg": "#120a18", "fg": "#e9d5ff", "accent": "#a78bfa", "enemy": "#fb7185"},
    "3d_action":        {"bg": "#080c14", "fg": "#cbd5e1", "accent": "#38bdf8", "enemy": "#f87171"},
    "narrative_mystery":{"bg": "#101418", "fg": "#e2e8f0", "accent": "#818cf8", "enemy": "#f472b6"},
}


def _seed_of(spec: SliceSpec) -> int:
    return int(hashlib.sha256(spec.id.encode("utf-8")).hexdigest(), 16) % (2 ** 31)


# 浏览器内共享引擎；按 __KIND__ 分支行为。所有占位都替换为确定性值。
_GAME_JS = r"""
"use strict";
const KIND = "__KIND__";
const SPEC = __SPEC_JSON__;
const PAL = __PALETTE_JSON__;
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const W = canvas.width, H = canvas.height;

let player = { x: W / 2, y: H - 80, r: 16, hp: 5, maxhp: 5 };
let ents = [];          // 敌人 / 音符 / 线索 / 资源 等
let score = 0, combo = 0, clues = 0, cluesNeeded = 5;
let won = false, over = false, spawnT = 0;
const keys = {};
const rng = (function (s) { let x = s >>> 0; return function () { x = (x * 1664525 + 1013904223) >>> 0; return x / 4294967296; }; })(__SEED__);

function resetGame() {
  player = { x: W / 2, y: H - 80, r: 16, hp: 5, maxhp: 5 };
  ents = []; score = 0; combo = 0; clues = 0; won = false; over = false; spawnT = 0;
}
function playSfx(name) { try { const a = new Audio("sfx_" + name + ".wav"); a.volume = 0.35; a.play().catch(function(){}); } catch (e) {} }

window.GameApp = {
  startMatch: function () { /* rAF 已通过契约自动置 playing */ },
  endMatch: function () { if (!over) { over = true; window.__GAME_AGENT__.markGameOver(); } },
  restartMatch: function () { resetGame(); window.__GAME_AGENT__.markRestart(); }
};

function triggerGameOver() { if (!over) { over = true; won = false; window.__GAME_AGENT__.markGameOver(); } }
function triggerWin() { if (!over) { over = true; won = true; window.__GAME_AGENT__.markGameOver(); } }

window.addEventListener("keydown", function (e) { keys[e.code] = true; onAction(e.code); });
window.addEventListener("keyup", function (e) { keys[e.code] = false; });

function onAction(code) {
  if (over) { if (code === "KeyR" || code === "Enter") { window.GameApp.restartMatch(); } return; }
  if (KIND === "card_roguelike") {
    if (code === "Space") { playSfx("ui_click"); score += 1; combo += 1; if (score >= 12) triggerWin(); }
  } else if (KIND === "rhythm") {
    const hit = ents.find(function (n) { return Math.abs(n.y - H * 0.78) < 36; });
    if (hit && (code === "KeyF" || code === "KeyJ" || code === "Space")) {
      ents = ents.filter(function (n) { return n !== hit; }); playSfx("coin"); score += 1; combo += 1;
      if (score >= 10) triggerWin();
    } else if (code === "KeyF" || code === "KeyJ" || code === "Space") { combo = 0; player.hp -= 1; playSfx("hit"); if (player.hp <= 0) triggerGameOver(); }
  } else if (KIND === "factory_sim") {
    if (code === "Space") { playSfx("step"); score += 1; if (score >= 10) triggerWin(); }
  } else if (KIND === "narrative_mystery") {
    const c = ents.find(function (e) { return Math.abs(e.x - player.x) < 28 && Math.abs(e.y - player.y) < 28; });
    if (c && (code === "Space" || code === "KeyE")) { ents = ents.filter(function (e) { return e !== c; }); playSfx("ui_click"); clues += 1; score += 1; if (clues >= cluesNeeded) triggerWin(); }
    else if (code === "KeyE") { player.hp -= 1; playSfx("hit"); if (player.hp <= 0) triggerGameOver(); }
  }
}

function spawn() {
  const x = 40 + rng() * (W - 80);
  if (KIND === "survivor_danmaku" || KIND === "racing" || KIND === "3d_action" || KIND === "roguelike_dungeon") {
    ents.push({ x: x, y: -20, vy: 60 + rng() * 120, r: 10 + rng() * 8 });
  } else if (KIND === "rhythm") {
    ents.push({ x: 40 + (Math.floor(rng() * 4)) * ((W - 80) / 4), y: -20, vy: 160 + rng() * 60, r: 14 });
  } else if (KIND === "card_roguelike") {
    if (rng() < 0.25) { player.hp -= 1; playSfx("hit"); if (player.hp <= 0) triggerGameOver(); }
  } else if (KIND === "factory_sim") {
    score += 0; // 产能稳定，无敌人
  } else if (KIND === "narrative_mystery") {
    ents.push({ x: 60 + rng() * (W - 120), y: 60 + rng() * (H - 240), r: 12 });
  }
}

function update(dt) {
  const sp = 240;
  if (keys["ArrowLeft"] || keys["KeyA"]) player.x -= sp * dt;
  if (keys["ArrowRight"] || keys["KeyD"]) player.x += sp * dt;
  if (keys["ArrowUp"] || keys["KeyW"]) player.y -= sp * dt;
  if (keys["ArrowDown"] || keys["KeyS"]) player.y += sp * dt;
  player.x = Math.max(20, Math.min(W - 20, player.x));
  player.y = Math.max(20, Math.min(H - 20, player.y));

  spawnT += dt;
  const rate = (KIND === "rhythm" || KIND === "survivor_danmaku") ? 0.45 : 0.9;
  if (!over && spawnT >= rate) { spawnT = 0; spawn(); }

  for (let i = ents.length - 1; i >= 0; i--) {
    const e = ents[i];
    if (KIND === "factory_sim" || KIND === "card_roguelike") continue;
    e.y += (e.vy || 80) * dt;
    const dx = e.x - player.x, dy = e.y - player.y;
    if (dx * dx + dy * dy < (e.r + player.r) * (e.r + player.r)) {
      ents.splice(i, 1);
      if (KIND === "narrative_mystery") { clues += 1; score += 1; playSfx("coin"); if (clues >= cluesNeeded) triggerWin(); }
      else { player.hp -= 1; playSfx("hit"); if (player.hp <= 0) triggerGameOver(); }
      continue;
    }
    if (e.y > H + 30) ents.splice(i, 1);
  }
}

function render() {
  ctx.fillStyle = PAL.bg; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = PAL.fg; ctx.font = "14px monospace";
  ctx.fillText(SPEC.name + "  [" + KIND + "]", 10, 20);
  ctx.fillText("SCORE " + score + "  HP " + player.hp + "/" + player.maxhp + "  COMBO " + combo, 10, 40);
  if (KIND === "narrative_mystery") ctx.fillText("CLUES " + clues + "/" + cluesNeeded, 10, 60);

  ctx.fillStyle = PAL.accent;
  ctx.beginPath(); ctx.arc(player.x, player.y, player.r, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = PAL.enemy;
  for (const e of ents) { ctx.beginPath(); ctx.arc(e.x, e.y, e.r, 0, Math.PI * 2); ctx.fill(); }

  if (over) {
    ctx.fillStyle = "rgba(0,0,0,0.55)"; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = won ? "#86d36b" : "#f87171"; ctx.font = "28px monospace";
    ctx.fillText(won ? "SLICE CLEARED" : "GAME OVER", W / 2 - 110, H / 2);
    ctx.fillStyle = PAL.fg; ctx.font = "14px monospace";
    ctx.fillText("按 R / Enter 重开（restartMatch）", W / 2 - 120, H / 2 + 30);
  }
}

let last = performance.now();
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (!over) update(dt);
  render();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
"""


def generate_slice_html(spec: SliceSpec) -> str:
    """生成单个切片的纯 HTML（尚未注入契约）。确定性。"""
    pal = _PALETTES.get(spec.genre, _PALETTES["card_roguelike"])
    spec_json = json.dumps({
        "id": spec.id, "name": spec.name, "genre": spec.genre,
        "maturity_target": spec.maturity_target, "mechanic": spec.mechanic,
        "parts": spec.parts,
    }, ensure_ascii=False)
    js = (_GAME_JS
          .replace("__KIND__", spec.genre)
          .replace("__SPEC_JSON__", spec_json)
          .replace("__PALETTE_JSON__", json.dumps(pal, ensure_ascii=False))
          .replace("__SEED__", str(_seed_of(spec))))
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{spec.name} — 垂直切片原型 ({spec.id})</title>
<style>
  html,body{{margin:0;background:{pal['bg']};color:{pal['fg']};font-family:monospace}}
  #wrap{{display:flex;flex-direction:column;align-items:center;gap:8px;padding:12px}}
  canvas{{background:{pal['bg']};border:1px solid {pal['accent']};border-radius:6px}}
  .note{{max-width:760px;font-size:12px;opacity:.8}}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="game" width="960" height="540"></canvas>
  <div class="note">垂直可玩切片（Slice {spec.maturity_target} 成熟度）：{spec.mechanic}
  真实可运行 / 真实可玩 / 真实可达 gameover。零件溯源：{', '.join(spec.parts)}。</div>
</div>
<script>
{js}
</script>
</body>
</html>
"""
    html = inject_runtime_contract(html)
    return html


def generate_slice(spec: SliceSpec, out_dir: Optional[str] = None) -> Path:
    """生成单个切片：落盘已注入契约的 index.html；返回路径。"""
    out = Path(out_dir) if out_dir else (ROOT / "output" / "slices" / spec.id)
    out.mkdir(parents=True, exist_ok=True)
    html = generate_slice_html(spec)  # 已注入运行时契约（幂等）
    path = out / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


def generate_all(out_dir: Optional[str] = None) -> list:
    """生成全部 8 个切片，返回路径列表。"""
    from pipeline.vertical_slices import VERTICAL_SLICES
    return [generate_slice(s, out_dir) for s in VERTICAL_SLICES]


__all__ = ["generate_slice_html", "generate_slice", "generate_all"]
