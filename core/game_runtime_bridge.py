"""
Game Runtime Bridge — 运行时全端编译与 H5/微信小游戏代码生成器
=============================================================
将 ModularGameAssembler 组装的 Parts 目录与游戏状态自动编译为
纯原生、零第三方依赖的 60FPS 生产级 HTML5 / WeChat Minigame 运行包。
"""

import json
from typing import Dict, Any, List, Optional
from core.ford_t_game_parts_hub import ModularGameAssembler


class GameRuntimeBridge:
    """Compiles assembled parts and configurations into client web runtime bundles."""

    @staticmethod
    def compile_playable_html(
        title: str,
        active_parts: List[str],
        initial_player_hp: int = 100,
        initial_score: int = 0
    ) -> str:
        """
        Generates a zero-dependency, high-polish HTML5/Canvas interactive game
        wiring input polling, particle sparks, hit-stop, trauma screen-shake, and HUD.
        """
        parts_json = json.dumps(active_parts)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{title} — Ford-T Production Runtime</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      background: #080c14; color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-height: 100vh; overflow: hidden;
    }}
    #game-container {{
      position: relative; width: 800px; height: 500px;
      border: 2px solid #30363d; border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.9), 0 0 40px rgba(0, 238, 255, 0.15);
      background: #0b1320; overflow: hidden;
    }}
    canvas {{ display: block; width: 100%; height: 100%; }}
    #hud-overlay {{
      position: absolute; top: 0; left: 0; width: 100%; height: 50px;
      padding: 10px 20px; display: flex; align-items: center; justify-content: space-between;
      pointer-events: none; z-index: 20;
      background: linear-gradient(180deg, rgba(8,12,20,0.85) 0%, transparent 100%);
    }}
    .bar-bg {{ width: 220px; height: 14px; background: #21262d; border-radius: 7px; overflow: hidden; }}
    .hp-fill {{ height: 100%; width: 100%; background: linear-gradient(90deg, #ff416c, #ff4b2b); transition: width 0.1s; }}
    .badge {{ font-size: 13px; font-weight: bold; letter-spacing: 1px; color: #00eeff; }}
    #parts-drawer {{
      position: absolute; bottom: 8px; left: 16px; font-size: 11px;
      color: #8b949e; z-index: 10; pointer-events: none;
    }}
  </style>
</head>
<body>
  <div id="game-container">
    <div id="hud-overlay">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span class="badge">HP</span>
        <div class="bar-bg"><div id="hp-bar" class="hp-fill"></div></div>
      </div>
      <div class="badge" id="score-display">SCORE: 0</div>
      <div class="badge" id="combo-display">COMBO: 0x</div>
    </div>
    <div id="parts-drawer">Active Parts: <span id="parts-list"></span></div>
    <canvas id="stage" width="800" height="500"></canvas>
  </div>

  <script>
    const ACTIVE_PARTS = {parts_json};
    document.getElementById('parts-list').textContent = ACTIVE_PARTS.join(', ');

    const canvas = document.getElementById('stage');
    const ctx = canvas.getContext('2d');

    // Game Feel & State
    let trauma = 0.0;
    let hitStop = 0;
    let score = {initial_score};
    let combo = 0;
    let playerHp = {initial_player_hp};

    const player = {{ x: 200, y: 250, vx: 0, vy: 0, w: 32, h: 48, sx: 1.0, sy: 1.0 }};
    const target = {{ x: 600, y: 250, w: 40, h: 60, hp: 100, flash: 0 }};
    const floatingTexts = [];
    const sparks = [];
    const keys = {{}};

    window.addEventListener('keydown', e => keys[e.key] = true);
    window.addEventListener('keyup', e => keys[e.key] = false);

    function triggerImpact(damage, isCrit) {{
      trauma = Math.min(1.0, trauma + (isCrit ? 0.7 : 0.4));
      hitStop = isCrit ? 8 : 4;
      target.hp = Math.max(0, target.hp - damage);
      target.flash = 6;
      combo++;
      score += damage * 10;

      player.sx = isCrit ? 1.4 : 1.25;
      player.sy = 1.0 / player.sx;

      // Floating number
      floatingTexts.push({{
        text: isCrit ? damage + '!' : '' + damage,
        x: target.x + (Math.random() - 0.5) * 20,
        y: target.y - 30,
        vy: -3.5,
        alpha: 1.0,
        color: isCrit ? '#ffea00' : '#ffffff'
      }});

      // Sparks
      for (let i = 0; i < (isCrit ? 16 : 8); i++) {{
        const ang = (Math.random() - 0.5) * Math.PI * 0.8;
        const spd = 4 + Math.random() * 6;
        sparks.push({{
          x: target.x, y: target.y,
          vx: Math.cos(ang) * spd,
          vy: Math.sin(ang) * spd,
          life: 20, maxLife: 20,
          color: isCrit ? '#ffe600' : '#ff5500'
        }});
      }}
    }}

    // Canvas Click / Spacebar Attack
    window.addEventListener('keydown', e => {{
      if (e.code === 'Space' || e.code === 'KeyJ') {{
        const dist = Math.hypot(target.x - player.x, target.y - player.y);
        if (dist < 120) {{
          const isCrit = Math.random() < 0.3;
          triggerImpact(isCrit ? 45 : 22, isCrit);
        }}
      }}
    }});

    function update() {{
      if (hitStop > 0) {{
        hitStop--;
        return; // Freeze frames on hit-stop!
      }}

      // Player Movement
      if (keys['ArrowLeft'] || keys['KeyA']) player.x -= 4;
      if (keys['ArrowRight'] || keys['KeyD']) player.x += 4;
      if (keys['ArrowUp'] || keys['KeyW']) player.y -= 4;
      if (keys['ArrowDown'] || keys['KeyS']) player.y += 4;

      player.x = Math.max(40, Math.min(760, player.x));
      player.y = Math.max(60, Math.min(460, player.y));

      // Squash/stretch spring back
      player.sx += (1.0 - player.sx) * 0.2;
      player.sy = 1.0 / Math.max(0.1, player.sx);

      // Flash decay
      if (target.flash > 0) target.flash--;

      // Trauma decay
      if (trauma > 0) trauma = Math.max(0, trauma - 0.03);

      // Sparks & Numbers
      for (let s of sparks) {{ s.x += s.vx; s.y += s.vy; s.life--; }}
      for (let t of floatingTexts) {{ t.y += t.vy; t.vy += 0.15; t.alpha -= 0.02; }}
    }}

    function render() {{
      ctx.save();
      // Screen Shake (Trauma^2)
      if (trauma > 0) {{
        const shake = trauma * trauma * 18.0;
        const ox = (Math.random() - 0.5) * shake;
        const oy = (Math.random() - 0.5) * shake;
        ctx.translate(ox, oy);
      }}

      ctx.clearRect(-20, -20, canvas.width + 40, canvas.height + 40);

      // Grid backdrop
      ctx.strokeStyle = '#162235';
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 40) {{
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }}
      for (let y = 0; y < canvas.height; y += 40) {{
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }}

      // Target Entity
      ctx.save();
      ctx.translate(target.x, target.y);
      ctx.fillStyle = target.flash > 0 ? '#ffffff' : '#e03131';
      ctx.fillRect(-target.w/2, -target.h/2, target.w, target.h);
      // Target HP bar
      ctx.fillStyle = '#21262d';
      ctx.fillRect(-target.w/2, -target.h/2 - 12, target.w, 5);
      ctx.fillStyle = '#38ef7d';
      ctx.fillRect(-target.w/2, -target.h/2 - 12, target.w * (target.hp / 100), 5);
      ctx.restore();

      // Player Entity (Squash & Stretch)
      ctx.save();
      ctx.translate(player.x, player.y);
      ctx.scale(player.sx, player.sy);
      ctx.fillStyle = '#00eeff';
      ctx.fillRect(-player.w/2, -player.h/2, player.w, player.h);
      ctx.restore();

      // Sparks
      for (let s of sparks) {{
        if (s.life <= 0) continue;
        ctx.fillStyle = s.color;
        ctx.fillRect(s.x, s.y, 3, 3);
      }}

      // Floating Numbers
      for (let t of floatingTexts) {{
        if (t.alpha <= 0) continue;
        ctx.save();
        ctx.globalAlpha = Math.max(0, t.alpha);
        ctx.font = 'bold 20px -apple-system, sans-serif';
        ctx.fillStyle = t.color;
        ctx.fillText(t.text, t.x, t.y);
        ctx.restore();
      }}

      ctx.restore();

      // Update HUD DOM
      document.getElementById('score-display').textContent = 'SCORE: ' + score;
      document.getElementById('combo-display').textContent = 'COMBO: ' + combo + 'x';
    }}

    function loop() {{
      update();
      render();
      requestAnimationFrame(loop);
    }}
    loop();
  </script>
</body>
</html>
"""
