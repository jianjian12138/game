#!/usr/bin/env python3
"""
grid_defense_compiler.py: 吸收《PvZ》与《A Dark Room》精髓的正统网格策略防守编译器
核心特性：
1. 5×9 严格离散空间网格与绝对坐标吸附对齐
2. 分行射线判定 (Row-based Ray Tracing) 与啃咬状态机 (Walk ➔ Eat ➔ Walk)
3. 阳光经济循环与卡牌半透明冷却遮罩 (Cooldown Masks)
4. 5 行终极割草机安全防线 (Lawnmover Safety Net)
5. 融入《A Dark Room》文字事件流与渐进波次压迫感
"""
import json
from typing import Dict, Any

class GridDefenseCompiler:

    @staticmethod
    def compile_grid_defense_game(title: str = "植物防线：黎明保卫战", custom_rules: str = "") -> str:
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - 5×9 工业级正统网格策略防守</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      background: #0d1117; color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-height: 100vh; overflow: hidden;
    }}
    #game-container {{
      position: relative; width: 960px; height: 620px;
      border: 3px solid #30363d; border-radius: 14px;
      background: #111a14; overflow: hidden;
      box-shadow: 0 25px 70px rgba(0,0,0,0.9), 0 0 30px rgba(46, 160, 67, 0.2);
    }}
    canvas {{ display: block; width: 100%; height: 100%; }}

    /* 顶部卡牌栏与阳光银行 (PvZ 标准 HUD) */
    #top-bar {{
      position: absolute; top: 0; left: 0; width: 100%; height: 75px;
      background: rgba(13, 17, 23, 0.92); border-bottom: 2px solid #238636;
      display: flex; align-items: center; padding: 0 16px; z-index: 50;
    }}
    .sun-bank {{
      background: #1c271e; border: 2px solid #ffd700; border-radius: 8px;
      padding: 6px 14px; display: flex; align-items: center; gap: 8px; margin-right: 18px;
    }}
    .sun-icon {{ font-size: 1.6rem; animation: sunSpin 6s linear infinite; }}
    @keyframes sunSpin {{ 100% {{ transform: rotate(360deg); }} }}
    .sun-val {{ font-size: 1.4rem; font-weight: bold; color: #ffd700; }}

    /* 卡牌槽 */
    .card-deck {{ display: flex; gap: 10px; flex: 1; }}
    .plant-card {{
      position: relative; width: 85px; height: 62px; background: #21262d;
      border: 2px solid #30363d; border-radius: 6px; cursor: pointer;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      transition: all 0.15s ease; overflow: hidden;
    }}
    .plant-card:hover:not(.disabled) {{
      border-color: #ffd700; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(255,215,0,0.3);
    }}
    .plant-card.selected {{
      border-color: #00eeff !important; box-shadow: 0 0 14px #00eeff !important;
    }}
    .plant-card.disabled {{
      opacity: 0.5; cursor: not-allowed; filter: grayscale(0.8);
    }}
    .card-cost {{ font-size: 0.72rem; font-weight: bold; color: #ffd700; position: absolute; bottom: 2px; right: 4px; }}
    .card-icon {{ font-size: 1.5rem; margin-top: -8px; }}
    .card-name {{ font-size: 0.65rem; color: #c9d1d9; font-weight: bold; }}
    
    /* 冷却遮罩 (Cooldown Mask) */
    .cd-overlay {{
      position: absolute; top: 0; left: 0; width: 100%; height: 0%;
      background: rgba(0, 0, 0, 0.65); pointer-events: none; transition: height 0.1s linear;
    }}

    /* 吸收 A Dark Room 的渐进事件叙事浮层 */
    #event-banner {{
      position: absolute; bottom: 8px; left: 16px;
      font-size: 0.85rem; color: #8b949e; font-style: italic; z-index: 40;
      background: rgba(13,17,23,0.85); padding: 4px 12px; border-radius: 4px;
    }}
  </style>
</head>
<body>

  <div id="game-container">
    <div id="top-bar">
      <div class="sun-bank">
        <div class="sun-icon">☀️</div>
        <div class="sun-val" id="sun-count">150</div>
      </div>
      <div class="card-deck" id="card-deck"></div>
      <div style="font-size: 0.9rem; font-weight:bold; color: #ff7b72; margin-left: 12px;">
        波次: <span id="wave-num" style="color:#ffd700;">1</span> / 3
      </div>
    </div>

    <canvas id="gameCanvas" width="960" height="620"></canvas>
    <div id="event-banner">微风拂过草坪，泥土的芬芳在黑暗中散开……</div>
  </div>

  <script>
    // =================================================================
    // 🌻 5×9 工业离散网格核心规范 (吸收 PythonPlantsVsZombies)
    // =================================================================
    const GRID_ROWS = 5;
    const GRID_COLS = 9;
    const GRID_LEFT = 110;
    const GRID_TOP = 85;
    const CELL_W = 88;
    const CELL_H = 100;

    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');

    // 植物卡牌大典
    const CARDS = [
      {{ id: 'sunflower', name: '向日葵', icon: '🌻', cost: 50, cd: 7, hp: 300 }},
      {{ id: 'peashooter', name: '豌豆射手', icon: '🌱', cost: 100, cd: 7, hp: 300 }},
      {{ id: 'wallnut', name: '坚果墙', icon: '🌰', cost: 50, cd: 18, hp: 3500 }},
      {{ id: 'cherrybomb', name: '樱桃炸弹', icon: '🍒', cost: 150, cd: 25, hp: 300 }},
      {{ id: 'shovel', name: '铲子', icon: '⛏️', cost: 0, cd: 0, hp: 0 }}
    ];

    let sun = 150;
    let selectedPlantId = null;
    let wave = 1;
    let gameTick = 0;

    // 5×9 离散矩阵状态
    const gridPlants = Array.from({{ length: GRID_ROWS }}, () => Array(GRID_COLS).fill(null));

    // 5 行小推车安全网
    const lawnMovers = [
      {{ row: 0, x: GRID_LEFT - 45, active: false, launched: false }},
      {{ row: 1, x: GRID_LEFT - 45, active: false, launched: false }},
      {{ row: 2, x: GRID_LEFT - 45, active: false, launched: false }},
      {{ row: 3, x: GRID_LEFT - 45, active: false, launched: false }},
      {{ row: 4, x: GRID_LEFT - 45, active: false, launched: false }}
    ];

    let zombies = [];
    let peas = [];
    let sunDrops = [];
    let hoverCell = null;

    // CD 时间表
    const cardCDState = {{}};
    CARDS.forEach(c => cardCDState[c.id] = 0);

    // 渲染卡牌
    function initCardsUI() {{
      const deck = document.getElementById('card-deck');
      deck.innerHTML = CARDS.map(c => `
        <div class="plant-card" id="card-${{c.id}}" onclick="selectCard('${{c.id}}')">
          <div class="cd-overlay" id="cd-${{c.id}}"></div>
          <div class="card-icon">${{c.icon}}</div>
          <div class="card-name">${{c.name}}</div>
          <div class="card-cost">${{c.cost > 0 ? c.cost : ''}}</div>
        </div>
      `).join('');
    }}

    function selectCard(id) {{
      if (selectedPlantId === id) {{
        selectedPlantId = null;
      }} else {{
        const card = CARDS.find(c => c.id === id);
        if (id === 'shovel' || (sun >= card.cost && cardCDState[id] <= 0)) {{
          selectedPlantId = id;
        }}
      }}
      updateCardDeckVisuals();
    }}

    function updateCardDeckVisuals() {{
      CARDS.forEach(c => {{
        const el = document.getElementById('card-' + c.id);
        const cdEl = document.getElementById('cd-' + c.id);
        if (!el) return;

        if (selectedPlantId === c.id) el.classList.add('selected');
        else el.classList.remove('selected');

        const isAffordable = (c.cost <= sun);
        const isCooldown = (cardCDState[c.id] > 0);
        if (!isAffordable || isCooldown) {{
          el.classList.add('disabled');
        }} else {{
          el.classList.remove('disabled');
        }}

        if (isCooldown && c.cd > 0) {{
          const pct = (cardCDState[c.id] / (c.cd * 60)) * 100;
          cdEl.style.height = pct + '%';
        }} else {{
          cdEl.style.height = '0%';
        }}
      }});
    }}

    // 鼠标网格吸附交互
    canvas.addEventListener('mousemove', e => {{
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      const c = Math.floor((mx - GRID_LEFT) / CELL_W);
      const r = Math.floor((my - GRID_TOP) / CELL_H);
      if (r >= 0 && r < GRID_ROWS && c >= 0 && c < GRID_COLS) {{
        hoverCell = {{ r, c }};
      }} else {{
        hoverCell = null;
      }}
    }});

    canvas.addEventListener('click', e => {{
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      // 拾取阳光
      for (let i = sunDrops.length - 1; i >= 0; i--) {{
        const s = sunDrops[i];
        if (Math.hypot(mx - s.x, my - s.y) < 30) {{
          sun += s.val;
          document.getElementById('sun-count').innerText = sun;
          sunDrops.splice(i, 1);
          updateCardDeckVisuals();
          return;
        }}
      }}

      // 种植 / 铲除
      if (!selectedPlantId || !hoverCell) return;
      const {{ r, c }} = hoverCell;

      if (selectedPlantId === 'shovel') {{
        if (gridPlants[r][c]) {{
          gridPlants[r][c] = null;
          selectedPlantId = null;
          updateCardDeckVisuals();
        }}
      }} else {{
        // 种植
        const card = CARDS.find(item => item.id === selectedPlantId);
        if (!gridPlants[r][c] && sun >= card.cost && cardCDState[card.id] <= 0) {{
          sun -= card.cost;
          document.getElementById('sun-count').innerText = sun;
          cardCDState[card.id] = card.cd * 60; // 冷却帧数

          gridPlants[r][c] = {{
            id: card.id,
            name: card.name,
            icon: card.icon,
            r: r, c: c,
            hp: card.hp,
            maxHp: card.hp,
            timer: 0
          }};

          // 樱桃炸弹 1 秒后引爆
          if (card.id === 'cherrybomb') {{
            setTimeout(() => {{
              explodeCherry(r, c);
            }}, 900);
          }}

          selectedPlantId = null;
          updateCardDeckVisuals();
        }}
      }}
    }});

    function explodeCherry(r, c) {{
      gridPlants[r][c] = null;
      // 3×3 范围核爆
      for (let i = zombies.length - 1; i >= 0; i--) {{
        const z = zombies[i];
        const cellX = GRID_LEFT + c * CELL_W + CELL_W/2;
        const cellY = GRID_TOP + r * CELL_H + CELL_H/2;
        if (Math.hypot(z.x - cellX, z.y - cellY) < 180) {{
          zombies.splice(i, 1);
        }}
      }}
    }}

    // 主物理循环
    function loop() {{
      requestAnimationFrame(loop);
      gameTick++;

      // 冷却倒计时
      CARDS.forEach(c => {{
        if (cardCDState[c.id] > 0) cardCDState[c.id]--;
      }});
      if (gameTick % 6 === 0) updateCardDeckVisuals();

      // 天空掉落自然阳光
      if (gameTick % 360 === 0 && sunDrops.length < 8) {{
        sunDrops.push({{
          x: GRID_LEFT + Math.random() * (GRID_COLS * CELL_W),
          y: -20,
          targetY: GRID_TOP + Math.random() * (GRID_ROWS * CELL_H),
          val: 25
        }});
      }}

      // 阳光下落动画
      sunDrops.forEach(s => {{
        if (s.y < s.targetY) s.y += 1.4;
      }});

      // 植物逻辑 (向日葵产阳光 / 豌豆射手分行射线射击)
      for (let r = 0; r < GRID_ROWS; r++) {{
        for (let c = 0; c < GRID_COLS; c++) {{
          const p = gridPlants[r][c];
          if (!p) continue;
          p.timer++;

          // 向日葵周期产光
          if (p.id === 'sunflower' && p.timer >= 540) {{
            p.timer = 0;
            const px = GRID_LEFT + c * CELL_W + CELL_W/2;
            const py = GRID_TOP + r * CELL_H + CELL_H/2;
            sunDrops.push({{ x: px, y: py - 10, targetY: py + 20, val: 25 }});
          }}

          // 豌豆射手分行射线射击
          if (p.id === 'peashooter' && p.timer >= 85) {{
            // 检查当前行前方是否有僵尸
            const hasEnemyInRow = zombies.some(z => z.row === r && z.x > (GRID_LEFT + c * CELL_W));
            if (hasEnemyInRow) {{
              p.timer = 0;
              peas.push({{
                row: r,
                x: GRID_LEFT + c * CELL_W + 45,
                y: GRID_TOP + r * CELL_H + 42,
                vx: 5.5,
                dmg: 20
              }});
            }}
          }}
        }}
      }}

      // 豌豆子弹推进与分行碰撞
      for (let i = peas.length - 1; i >= 0; i--) {{
        const b = peas[i];
        b.x += b.vx;
        for (let j = zombies.length - 1; j >= 0; j--) {{
          const z = zombies[j];
          if (z.row === b.row && Math.abs(z.x - b.x) < 22) {{
            z.hp -= b.dmg;
            peas.splice(i, 1);
            if (z.hp <= 0) zombies.splice(j, 1);
            break;
          }}
        }}
        if (b.x > canvas.width + 20) peas.splice(i, 1);
      }}

      // 僵尸刷怪节奏 (渐进波次)
      if (gameTick % Math.max(160, 400 - wave * 70) === 0 && zombies.length < 25) {{
        const r = Math.floor(Math.random() * GRID_ROWS);
        const isBucket = Math.random() < (wave * 0.25);
        zombies.push({{
          row: r,
          x: canvas.width + 20,
          y: GRID_TOP + r * CELL_H + CELL_H/2,
          speed: isBucket ? 0.35 : 0.45,
          hp: isBucket ? 750 : 200,
          maxHp: isBucket ? 750 : 200,
          isBucket: isBucket,
          eating: false
        }});
      }}

      // 僵尸移动与啃咬状态机
      zombies.forEach(z => {{
        // 检测前方是否有植物
        const c = Math.floor((z.x - 20 - GRID_LEFT) / CELL_W);
        if (c >= 0 && c < GRID_COLS && gridPlants[z.row][c]) {{
          // 进入啃咬状态
          z.eating = true;
          const plant = gridPlants[z.row][c];
          plant.hp -= 0.65;
          if (plant.hp <= 0) {{
            gridPlants[z.row][c] = null; // 植物被吃掉
            z.eating = false;
          }}
        }} else {{
          z.eating = false;
          z.x -= z.speed;
        }}

        // 突破到最左侧触碰小推车
        const mover = lawnMovers[z.row];
        if (z.x < (GRID_LEFT - 10) && !mover.launched) {{
          mover.launched = true;
        }}
      }});

      // 小推车安全网极速冲锋
      lawnMovers.forEach(m => {{
        if (m.launched && m.x < canvas.width + 60) {{
          m.x += 8.5;
          // 秒杀该行所有僵尸
          for (let i = zombies.length - 1; i >= 0; i--) {{
            if (zombies[i].row === m.row && Math.abs(zombies[i].x - m.x) < 40) {{
              zombies.splice(i, 1);
            }}
          }}
        }}
      }});

      draw();
    }}

    // 画面绘制
    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 1. 绘制 5×9 经典绿茵棋盘
      for (let r = 0; r < GRID_ROWS; r++) {{
        for (let c = 0; c < GRID_COLS; c++) {{
          const isEven = (r + c) % 2 === 0;
          ctx.fillStyle = isEven ? '#1f3d24' : '#19331e';
          ctx.fillRect(GRID_LEFT + c * CELL_W, GRID_TOP + r * CELL_H, CELL_W, CELL_H);
          ctx.strokeStyle = '#274e2e'; ctx.lineWidth = 1;
          ctx.strokeRect(GRID_LEFT + c * CELL_W, GRID_TOP + r * CELL_H, CELL_W, CELL_H);
        }}
      }}

      // 高亮当前选中网格
      if (hoverCell) {{
        ctx.strokeStyle = selectedPlantId === 'shovel' ? '#ff3366' : '#ffd700';
        ctx.lineWidth = 2.5;
        ctx.strokeRect(GRID_LEFT + hoverCell.c * CELL_W, GRID_TOP + hoverCell.r * CELL_H, CELL_W, CELL_H);
      }}

      // 2. 绘制小推车
      lawnMovers.forEach(m => {{
        if (m.x < canvas.width + 50) {{
          ctx.font = '24px sans-serif'; ctx.textAlign = 'center';
          ctx.fillText('🚜', m.x, GRID_TOP + m.row * CELL_H + CELL_H/2 + 8);
        }}
      }});

      // 3. 绘制植物
      for (let r = 0; r < GRID_ROWS; r++) {{
        for (let c = 0; c < GRID_COLS; c++) {{
          const p = gridPlants[r][c];
          if (!p) continue;
          const px = GRID_LEFT + c * CELL_W + CELL_W/2;
          const py = GRID_TOP + r * CELL_H + CELL_H/2;

          ctx.font = '36px sans-serif'; ctx.textAlign = 'center';
          ctx.fillText(p.icon, px, py + 12);

          // 坚果墙损伤裂纹
          if (p.id === 'wallnut' && p.hp < p.maxHp * 0.5) {{
            ctx.fillStyle = '#ff7b72'; ctx.font = '14px sans-serif';
            ctx.fillText('⚡损', px, py - 18);
          }}
        }}
      }}

      // 4. 绘制豌豆子弹
      peas.forEach(b => {{
        ctx.fillStyle = '#70e000'; ctx.shadowColor = '#70e000'; ctx.shadowBlur = 8;
        ctx.beginPath(); ctx.arc(b.x, b.y, 6.5, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
      }});

      // 5. 绘制僵尸
      zombies.forEach(z => {{
        ctx.font = '34px sans-serif'; ctx.textAlign = 'center';
        const zombieIcon = z.isBucket ? '🪣🧟' : '🧟';
        ctx.fillText(zombieIcon, z.x, z.y + 10);

        // 僵尸血条
        const pct = Math.max(0, z.hp / z.maxHp);
        ctx.fillStyle = 'rgba(0,0,0,0.6)';
        ctx.fillRect(z.x - 18, z.y - 28, 36, 4);
        ctx.fillStyle = z.isBucket ? '#ffd700' : '#ff3366';
        ctx.fillRect(z.x - 18, z.y - 28, 36 * pct, 4);
      }});

      // 6. 绘制阳光掉落物
      sunDrops.forEach(s => {{
        ctx.font = '28px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText('☀️', s.x, s.y);
      }});
    }}

    // 初始化
    initCardsUI();
    loop();
  </script>
</body>
</html>"""
