"""
Game Remix Patcher & Zero-Dependency Single-File Web Playable Bundler (Article 42)
Inspired by Playabl's 'TikTok-style UGC Game Distribution & Forking Engine'.

1. GameRemixPatcher: Applies structural delta mutations to a parent game spec while preserving lineage.
2. PlayableWebBundler: Compiles any StructuredGameSpec into a 100% self-contained, zero-dependency HTML5 Canvas playable.
"""

import os
import json
import uuid
import time
from typing import Dict, Any, Optional
from core.prompt_to_game_assembler import StructuredGameSpec, PromptToGameAssembler


class GameRemixPatcher:
    """
    Handles Game Remixing (Fork & Mutate).
    Maintains ancestry tracking, applies delta patches, and alters rules/controls/aesthetics.
    """

    @staticmethod
    def remix_game(
        parent_spec: StructuredGameSpec,
        remix_prompt: str,
        delta_patch: Optional[Dict[str, Any]] = None,
        author: str = "RemixCreator"
    ) -> StructuredGameSpec:
        parent_dict = parent_spec.to_dict()
        new_id = f"remix_{uuid.uuid4().hex[:8]}"
        
        # Clone data
        child_dict = json.loads(json.dumps(parent_dict))
        child_dict["spec_id"] = new_id
        child_dict["parent_id"] = parent_spec.spec_id
        child_dict["author"] = author
        child_dict["prompt"] = f"{parent_spec.prompt} -> [Remix]: {remix_prompt}"

        # Initialize or extend lineage
        lineage = list(parent_dict.get("remix_lineage", []))
        mutation_record = {
            "timestamp": time.time(),
            "parent_id": parent_spec.spec_id,
            "child_id": new_id,
            "remix_prompt": remix_prompt,
            "applied_delta": delta_patch or {}
        }
        lineage.append(mutation_record)
        child_dict["remix_lineage"] = lineage

        child_spec = StructuredGameSpec.from_dict(child_dict)

        # Apply semantic modifications from remix prompt
        r_lower = remix_prompt.lower()
        if "faster" in r_lower or "2x" in r_lower or "加倍" in r_lower or "快" in r_lower:
            child_spec.controls.move_speed *= 1.5
            child_spec.pacing.spawn_interval_sec = max(0.4, child_spec.pacing.spawn_interval_sec * 0.7)
        if "harder" in r_lower or "困难" in r_lower or "地狱" in r_lower:
            child_spec.termination.max_lives = max(1, child_spec.termination.max_lives - 1)
            child_spec.pacing.speed_multiplier_per_sec *= 1.8
        if "easier" in r_lower or "简单" in r_lower or "增加生命" in r_lower:
            child_spec.termination.max_lives += 2
        if "wasd" in r_lower:
            child_spec.controls.scheme = "wasd_keys"
            child_spec.controls.gravity = 0.0
        elif "one_tap" in r_lower or "tap" in r_lower or "点击" in r_lower:
            child_spec.controls.scheme = "one_tap"
            child_spec.controls.gravity = 850.0
        elif "drag" in r_lower or "拖动" in r_lower:
            child_spec.controls.scheme = "touch_drag"
            child_spec.controls.gravity = 0.0

        # Themes
        for theme_key in PromptToGameAssembler.THEMES:
            if theme_key in r_lower:
                palette = PromptToGameAssembler.THEMES[theme_key]
                child_spec.aesthetics.theme = theme_key
                child_spec.aesthetics.bg_color = palette["bg_color"]
                child_spec.aesthetics.primary_color = palette["primary_color"]
                child_spec.aesthetics.accent_color = palette["accent_color"]
                child_spec.aesthetics.hazard_color = palette["hazard_color"]
                child_spec.aesthetics.collectible_color = palette["collectible_color"]
                child_spec.avatar.color = palette["primary_color"]
                break

        # Explicit delta patch overrides
        if delta_patch:
            if "controls" in delta_patch:
                for k, v in delta_patch["controls"].items():
                    if hasattr(child_spec.controls, k):
                        setattr(child_spec.controls, k, v)
            if "termination" in delta_patch:
                for k, v in delta_patch["termination"].items():
                    if hasattr(child_spec.termination, k):
                        setattr(child_spec.termination, k, v)
            if "aesthetics" in delta_patch:
                for k, v in delta_patch["aesthetics"].items():
                    if hasattr(child_spec.aesthetics, k):
                        setattr(child_spec.aesthetics, k, v)
            if "title" in delta_patch:
                child_spec.title = delta_patch["title"]

        return child_spec


class PlayableWebBundler:
    """
    Compiles a StructuredGameSpec into a 100% self-contained, zero-dependency HTML5 Canvas file.
    No CDN links, no external scripts. Instant micro-game distribution in browser.
    """

    @staticmethod
    def bundle_to_html(spec: StructuredGameSpec, output_path: Optional[str] = None) -> str:
        spec_json = spec.to_json(indent=2)
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{spec.title} - Playabl UGC Playable</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
    }}
    body {{
      background-color: #05070a;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      overflow: hidden;
    }}
    #game-container {{
      position: relative;
      width: 420px;
      height: 640px;
      max-width: 100vw;
      max-height: 100vh;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8), 0 0 20px {spec.aesthetics.primary_color}33;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid rgba(255, 255, 255, 0.1);
      background: {spec.aesthetics.bg_color};
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
      touch-action: none;
    }}
    /* Playabl TikTok-Style UGC Overlay */
    .ugc-header {{
      position: absolute;
      top: 12px;
      left: 12px;
      right: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      pointer-events: none;
      z-index: 10;
    }}
    .game-badge {{
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(8px);
      padding: 6px 12px;
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.15);
      font-size: 12px;
      font-weight: 600;
      color: #fff;
    }}
    .remix-pill {{
      color: {spec.aesthetics.accent_color};
      margin-left: 4px;
    }}
    .hud-metrics {{
      display: flex;
      gap: 8px;
    }}
    .metric-pill {{
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(8px);
      padding: 6px 12px;
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.15);
      font-size: 13px;
      font-weight: 700;
    }}
    .metric-lives {{
      color: {spec.aesthetics.hazard_color};
    }}
    .metric-score {{
      color: {spec.aesthetics.collectible_color};
    }}
    /* Side Action Bar (TikTok Style) */
    .ugc-actions {{
      position: absolute;
      right: 12px;
      bottom: 60px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      z-index: 10;
    }}
    .ugc-btn {{
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #fff;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      cursor: pointer;
      pointer-events: auto;
      transition: transform 0.15s ease, background 0.15s;
    }}
    .ugc-btn:hover {{
      transform: scale(1.1);
      background: rgba(255, 255, 255, 0.2);
    }}
    .ugc-btn-count {{
      font-size: 9px;
      margin-top: 2px;
      color: #ccc;
    }}
    /* Modal Screen */
    #overlay-modal {{
      position: absolute;
      inset: 0;
      background: rgba(5, 7, 10, 0.85);
      backdrop-filter: blur(8px);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 20;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
      padding: 24px;
      text-align: center;
    }}
    #overlay-modal.active {{
      opacity: 1;
      pointer-events: auto;
    }}
    .modal-title {{
      font-size: 26px;
      font-weight: 800;
      margin-bottom: 8px;
    }}
    .modal-sub {{
      font-size: 14px;
      color: #aaa;
      margin-bottom: 24px;
    }}
    .btn-play {{
      background: linear-gradient(135deg, {spec.aesthetics.primary_color}, {spec.aesthetics.accent_color});
      color: #000;
      font-weight: 800;
      font-size: 16px;
      padding: 12px 32px;
      border-radius: 28px;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 20px {spec.aesthetics.primary_color}66;
      transition: transform 0.15s ease;
    }}
    .btn-play:hover {{
      transform: scale(1.05);
    }}
  </style>
</head>
<body>
  <div id="game-container">
    <!-- Top HUD -->
    <div class="ugc-header">
      <div class="game-badge">
        <span>{spec.title}</span>
        {f'<span class="remix-pill">🔁 Remix</span>' if spec.parent_id else ''}
      </div>
      <div class="hud-metrics">
        <div class="metric-pill metric-lives" id="ui-lives">❤ {spec.termination.max_lives}</div>
        <div class="metric-pill metric-score" id="ui-score">★ 0</div>
      </div>
    </div>

    <!-- TikTok Style Side Floating Buttons -->
    <div class="ugc-actions">
      <button class="ugc-btn" id="btn-like" title="Like">
        ❤<span class="ugc-btn-count" id="like-count">1.2k</span>
      </button>
      <button class="ugc-btn" id="btn-remix" title="Remix Game">
        🔁<span class="ugc-btn-count">Fork</span>
      </button>
      <button class="ugc-btn" id="btn-share" title="Share Link">
        ↗<span class="ugc-btn-count">Share</span>
      </button>
    </div>

    <canvas id="gameCanvas" width="420" height="640"></canvas>

    <!-- Overlay Modal (Start / Over / Win) -->
    <div id="overlay-modal" class="active">
      <h1 class="modal-title" id="modal-title">{spec.title}</h1>
      <p class="modal-sub" id="modal-sub">Controls: {spec.controls.scheme.replace('_', ' ').upper()}<br>Tap anywhere or press SPACE to Start</p>
      <button class="btn-play" id="btn-start">START PLAYING</button>
    </div>
  </div>

  <script>
    // Embedded 5-Pillar Game Spec
    const SPEC = {spec_json};

    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    const uiLives = document.getElementById('ui-lives');
    const uiScore = document.getElementById('ui-score');
    const modal = document.getElementById('overlay-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalSub = document.getElementById('modal-sub');
    const btnStart = document.getElementById('btn-start');

    // State Variables
    let gameState = "READY"; // READY, PLAYING, GAMEOVER, VICTORY
    let score = 0;
    let lives = SPEC.termination.max_lives;
    let timeElapsed = 0;
    let lastTime = performance.now();

    // Player Entity
    const player = {{
      x: canvas.width / 2,
      y: SPEC.controls.scheme === 'one_tap' ? canvas.height / 2 : canvas.height - 80,
      vx: 0,
      vy: 0,
      size: SPEC.avatar.size,
      speed: SPEC.controls.move_speed,
      color: SPEC.avatar.color,
      shape: SPEC.avatar.shape,
      invulnTimer: 0
    }};

    // Input States
    const keys = {{}};
    let pointerX = player.x;
    let pointerY = player.y;
    let isPointerDown = false;

    // Entity Pools
    let hazards = [];
    let collectibles = [];
    let particles = [];
    let spawnTimer = 0;

    // Event Listeners
    window.addEventListener('keydown', (e) => {{
      keys[e.code] = true;
      if (gameState !== 'PLAYING' && (e.code === 'Space' || e.code === 'KeyR' || e.code === 'Enter')) {{
        startGame();
      }}
      if (SPEC.controls.scheme === 'one_tap' && (e.code === 'Space' || e.code === 'ArrowUp')) {{
        player.vy = -SPEC.controls.jump_force;
      }}
    }});

    window.addEventListener('keyup', (e) => {{
      keys[e.code] = false;
    }});

    canvas.addEventListener('pointerdown', (e) => {{
      const rect = canvas.getBoundingClientRect();
      pointerX = (e.clientX - rect.left) * (canvas.width / rect.width);
      pointerY = (e.clientY - rect.top) * (canvas.height / rect.height);
      isPointerDown = true;
      if (gameState !== 'PLAYING') {{
        startGame();
      }} else if (SPEC.controls.scheme === 'one_tap') {{
        player.vy = -SPEC.controls.jump_force;
      }}
    }});

    canvas.addEventListener('pointermove', (e) => {{
      const rect = canvas.getBoundingClientRect();
      pointerX = (e.clientX - rect.left) * (canvas.width / rect.width);
      pointerY = (e.clientY - rect.top) * (canvas.height / rect.height);
    }});

    canvas.addEventListener('pointerup', () => {{ isPointerDown = false; }});
    btnStart.addEventListener('click', startGame);

    // Like Button Interaction
    document.getElementById('btn-like').addEventListener('click', () => {{
      const countEl = document.getElementById('like-count');
      countEl.innerText = '1.3k';
      countEl.style.color = '#ff0055';
    }});

    function startGame() {{
      gameState = "PLAYING";
      score = 0;
      lives = SPEC.termination.max_lives;
      timeElapsed = 0;
      hazards = [];
      collectibles = [];
      particles = [];
      spawnTimer = 0;
      player.x = canvas.width / 2;
      player.y = SPEC.controls.scheme === 'one_tap' ? canvas.height / 2 : canvas.height - 80;
      player.vx = 0;
      player.vy = 0;
      player.invulnTimer = 0;
      uiLives.innerText = `❤ ${{lives}}`;
      uiScore.innerText = `★ ${{score}}`;
      modal.classList.remove('active');
    }}

    function triggerGameOver(won) {{
      gameState = won ? "VICTORY" : "GAMEOVER";
      modalTitle.innerText = won ? "VICTORY!" : "GAME OVER";
      modalTitle.style.color = won ? SPEC.aesthetics.collectible_color : SPEC.aesthetics.hazard_color;
      modalSub.innerHTML = `Final Score: <b>${{score}}</b> | Survived: <b>${{timeElapsed.toFixed(1)}}s</b><br>Click Start or press [R] to retry`;
      btnStart.innerText = "PLAY AGAIN";
      modal.classList.add('active');
    }}

    function spawnEntities(dt) {{
      spawnTimer += dt;
      const cadence = SPEC.pacing.spawn_interval_sec;
      if (spawnTimer >= cadence) {{
        spawnTimer = 0;
        // Spawn Hazard
        const hazardX = Math.random() * (canvas.width - 40) + 20;
        const hazardSpeed = 160 + (timeElapsed * SPEC.pacing.speed_multiplier_per_sec * 60);
        hazards.push({{
          x: hazardX,
          y: -20,
          radius: 12 + Math.random() * 8,
          vy: hazardSpeed,
          color: SPEC.aesthetics.hazard_color
        }});

        // Spawn Collectible with 60% chance
        if (Math.random() < 0.6) {{
          collectibles.push({{
            x: Math.random() * (canvas.width - 40) + 20,
            y: -20,
            radius: 9,
            vy: hazardSpeed * 0.85,
            color: SPEC.aesthetics.collectible_color,
            rot: 0
          }});
        }}
      }}
    }}

    function emitParticles(x, y, color, count = 12) {{
      for (let i = 0; i < count; i++) {{
        const angle = Math.random() * Math.PI * 2;
        const speed = 60 + Math.random() * 180;
        particles.push({{
          x: x,
          y: y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: 0.4 + Math.random() * 0.4,
          maxLife: 0.8,
          color: color,
          size: 2 + Math.random() * 3
        }});
      }}
    }}

    function update(dt) {{
      if (gameState !== "PLAYING") return;
      timeElapsed += dt;

      // Handle Controls
      if (SPEC.controls.scheme === 'one_tap') {{
        player.vy += SPEC.controls.gravity * dt;
        player.y += player.vy * dt;
        // Screen bounds
        if (player.y > canvas.height - player.size) {{
          player.y = canvas.height - player.size;
          player.vy = 0;
        }}
        if (player.y < player.size) {{
          player.y = player.size;
          player.vy = 0;
        }}
      }} else if (SPEC.controls.scheme === 'touch_drag') {{
        if (isPointerDown) {{
          const dx = pointerX - player.x;
          const dy = pointerY - player.y;
          player.x += dx * Math.min(1.0, dt * 14.0);
          player.y += dy * Math.min(1.0, dt * 14.0);
        }}
      }} else if (SPEC.controls.scheme === 'wasd_keys') {{
        let moveX = 0, moveY = 0;
        if (keys['KeyA'] || keys['ArrowLeft']) moveX -= 1;
        if (keys['KeyD'] || keys['ArrowRight']) moveX += 1;
        if (keys['KeyW'] || keys['ArrowUp']) moveY -= 1;
        if (keys['KeyS'] || keys['ArrowDown']) moveY += 1;
        const len = Math.sqrt(moveX * moveX + moveY * moveY);
        if (len > 0) {{
          player.x += (moveX / len) * player.speed * dt;
          player.y += (moveY / len) * player.speed * dt;
        }}
      }}

      // Player Bounds Clamp
      player.x = Math.max(player.size, Math.min(canvas.width - player.size, player.x));
      player.y = Math.max(player.size, Math.min(canvas.height - player.size, player.y));

      if (player.invulnTimer > 0) {{
        player.invulnTimer -= dt;
      }}

      // Spawning
      spawnEntities(dt);

      // Hazards Update
      for (let i = hazards.length - 1; i >= 0; i--) {{
        const h = hazards[i];
        h.y += h.vy * dt;

        // Collision with player
        const dist = Math.sqrt((h.x - player.x)**2 + (h.y - player.y)**2);
        if (dist < h.radius + player.size && player.invulnTimer <= 0) {{
          lives -= 1;
          player.invulnTimer = 1.0; // i-frame
          emitParticles(player.x, player.y, SPEC.aesthetics.hazard_color, 24);
          uiLives.innerText = `❤ ${{lives}}`;
          hazards.splice(i, 1);
          if (lives <= 0) {{
            triggerGameOver(false);
            return;
          }}
          continue;
        }}

        if (h.y > canvas.height + 30) {{
          hazards.splice(i, 1);
        }}
      }}

      // Collectibles Update
      for (let i = collectibles.length - 1; i >= 0; i--) {{
        const c = collectibles[i];
        c.y += c.vy * dt;
        c.rot += dt * 3.0;

        const dist = Math.sqrt((c.x - player.x)**2 + (c.y - player.y)**2);
        if (dist < c.radius + player.size) {{
          score += 1;
          uiScore.innerText = `★ ${{score}}`;
          emitParticles(c.x, c.y, SPEC.aesthetics.collectible_color, 16);
          collectibles.splice(i, 1);

          // Check Win Condition
          if (SPEC.termination.win_condition === 'reach_score' && score >= SPEC.termination.target_score) {{
            triggerGameOver(true);
            return;
          }}
          continue;
        }}

        if (c.y > canvas.height + 30) {{
          collectibles.splice(i, 1);
        }}
      }}

      // Check Survive Time Win Condition
      if (SPEC.termination.win_condition === 'survive_time' && timeElapsed >= SPEC.termination.time_limit_sec) {{
        triggerGameOver(true);
        return;
      }}

      // Particles Update
      for (let i = particles.length - 1; i >= 0; i--) {{
        const p = particles[i];
        p.life -= dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        if (p.life <= 0) {{
          particles.splice(i, 1);
        }}
      }}
    }}

    function render() {{
      // Background
      ctx.fillStyle = SPEC.aesthetics.bg_color;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Grid background aesthetic
      if (SPEC.aesthetics.grid_overlay) {{
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.lineWidth = 1;
        for (let x = 0; x < canvas.width; x += 32) {{
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, canvas.height);
          ctx.stroke();
        }}
        for (let y = 0; y < canvas.height; y += 32) {{
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(canvas.width, y);
          ctx.stroke();
        }}
      }}

      // Render Hazards
      for (const h of hazards) {{
        ctx.fillStyle = h.color;
        ctx.beginPath();
        ctx.arc(h.x, h.y, h.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 10;
        ctx.shadowColor = h.color;
      }}
      ctx.shadowBlur = 0;

      // Render Collectibles
      for (const c of collectibles) {{
        ctx.save();
        ctx.translate(c.x, c.y);
        ctx.rotate(c.rot);
        ctx.fillStyle = c.color;
        ctx.fillRect(-c.radius, -c.radius, c.radius * 2, c.radius * 2);
        ctx.restore();
      }}

      // Render Particles
      for (const p of particles) {{
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.life / p.maxLife;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }}
      ctx.globalAlpha = 1.0;

      // Render Player
      if (player.invulnTimer <= 0 || Math.floor(performance.now() / 100) % 2 === 0) {{
        ctx.fillStyle = player.color;
        ctx.shadowColor = player.color;
        ctx.shadowBlur = 14;
        ctx.beginPath();
        if (player.shape === 'triangle') {{
          ctx.moveTo(player.x, player.y - player.size * 1.3);
          ctx.lineTo(player.x + player.size, player.y + player.size);
          ctx.lineTo(player.x - player.size, player.y + player.size);
          ctx.closePath();
        }} else if (player.shape === 'rect') {{
          ctx.rect(player.x - player.size, player.y - player.size, player.size * 2, player.size * 2);
        }} else {{
          ctx.arc(player.x, player.y, player.size, 0, Math.PI * 2);
        }}
        ctx.fill();
        ctx.shadowBlur = 0;
      }}
    }}

    function loop(now) {{
      const dt = Math.min(0.1, (now - lastTime) / 1000);
      lastTime = now;
      update(dt);
      render();
      requestAnimationFrame(loop);
    }}

    requestAnimationFrame(loop);
  </script>
</body>
</html>
"""
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_template)
        return html_template
