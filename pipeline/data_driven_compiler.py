#!/usr/bin/env python3
"""
data_driven_compiler.py: 工业级数据驱动游戏编译器 (Data-Driven Compiler)
全面接入真实游戏 PNG 精灵图资产！
彻底告别手动画线、画圆或画弱智布偶的畸形做法！
通过标准的 ctx.drawImage() 硬件加速加载并渲染商业级高清立绘与精灵！
"""
import os
import json
from typing import Dict, Any, Optional
from core.runtime_system_bus import RuntimeSystemBus

class DataDrivenCompiler:

    @staticmethod
    def compile_playable_game(
        domain_model: Dict[str, Any],
        mode: str = "fast",
        llm_provider: str = "gemini",
        llm_model: Optional[str] = None,
    ) -> str:
        effective_mode = os.environ.get("LLM_DEFAULT_MODE", "fast") if mode == "fast" else mode
        if effective_mode == "llm":
            llm_code = DataDrivenCompiler._compile_with_llm(domain_model, llm_provider, llm_model)
            if llm_code:
                return llm_code

        title = domain_model["story_goals"]["title"]
        chars_json = json.dumps(domain_model["characters"], ensure_ascii=False)
        skills_json = json.dumps(domain_model["skills"], ensure_ascii=False)
        waves_json = json.dumps(domain_model["waves"], ensure_ascii=False)
        lore = domain_model["story_goals"]["lore"]
        primary_obj = domain_model["story_goals"]["primary_objective"]

        # 绑定高清透明精灵图路径
        sprite_map = {
            "char_warrior": "assets/sprites/hero_warrior.png",
            "char_ranger": "assets/sprites/hero_ranger.png",
            "char_mage": "assets/sprites/hero_mage.png",
            "enemy_normal": "assets/sprites/enemy_monster.png",
            "boss_titan": "assets/sprites/boss_titan.png"
        }
        sprite_map_json = json.dumps(sprite_map, ensure_ascii=False)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - 商业级全系统大作</title>
  <style>
{RuntimeSystemBus.get_system_bus_css()}
    /* 高清角色立绘卡片样式 */
    .char-portrait-img {{
      display: block; width: 100px; height: 100px; margin: 0 auto 10px auto;
      object-fit: contain; filter: drop-shadow(0 6px 12px rgba(0,0,0,0.6));
      transition: transform 0.2s ease;
    }}
    .char-card:hover .char-portrait-img {{
      transform: scale(1.08) translateY(-2px);
    }}
  </style>
</head>
<body>

  <div id="game-container">
    <!-- 顶部高精度 HUD -->
    <div id="hud-overlay">
      <div style="font-weight:bold; color:#58a6ff; font-size:1.1rem;">
        等级 LV.<span id="hud-level" style="color:#ffd700; font-size:1.3rem;">1</span>
      </div>
      <div class="exp-bar-container">
        <div class="exp-bar-fill" id="hud-exp-fill"></div>
        <div class="exp-bar-text" id="hud-exp-text">EXP 0 / 100</div>
      </div>
      <div style="font-weight:bold; color:#ff7b72; font-size:1.1rem;">
        生命: <span id="hud-hp" style="color:#fff;">100</span>
      </div>
      <div style="font-weight:bold; color:#79c0ff; font-size:1.1rem; margin-left:14px;">
        时间: <span id="hud-timer" style="color:#ffd700;">00:00</span>
      </div>
    </div>

    <!-- 游戏画布 -->
    <canvas id="gameCanvas" width="920" height="600"></canvas>

    <!-- 1. 启动封面与角色选择 (真实立绘卡片) -->
    <div id="screen-char-select" class="bus-modal">
      <div class="bus-card">
        <h1 style="font-size:2.3rem; color:#ffd700; margin-bottom:6px;">⚔️ {title}</h1>
        <p style="color:#8b949e; font-size:0.88rem; margin-bottom:10px;">{lore}</p>
        <div style="background:#0d1117; padding:6px 14px; border-radius:6px; color:#58a6ff; font-size:0.82rem; margin-bottom:14px;">
          🎯 核心目标: {primary_obj}
        </div>
        <h3 style="color:#c9d1d9; font-size:1.05rem; margin-bottom:10px;">请选择你的出战特战英雄:</h3>
        
        <div class="char-grid" id="char-selection-container"></div>
        <button class="bus-btn" id="start-battle-btn" onclick="GameApp.startMatch()" disabled>请先点击选择一位英雄</button>
      </div>
    </div>

    <!-- 2. 升级三选一技能构筑面板 -->
    <div id="screen-levelup" class="bus-modal bus-hidden">
      <div class="bus-card">
        <h2 style="color:#ffd700; font-size:2rem; margin-bottom:6px;">✨ 等级跃升！选择你的技能构筑</h2>
        <p style="color:#8b949e; font-size:0.85rem; margin-bottom:16px;">选择一项技能或武器，实时强化你的输出弹幕与生存能力</p>
        <div class="choice-grid" id="choice-container"></div>
      </div>
    </div>

    <!-- 3. 结算统计面板 -->
    <div id="screen-gameover" class="bus-modal bus-hidden">
      <div class="bus-card">
        <h2 id="end-title" style="font-size:2.4rem; color:#ffd700; margin-bottom:10px;">🎉 战斗大捷</h2>
        <p id="end-desc" style="color:#ccc; font-size:0.92rem; line-height:1.5; margin-bottom:18px;"></p>
        <div style="background:#0d1117; border-radius:8px; padding:12px; margin-bottom:20px; display:flex; justify-content:space-around;">
          <div>存活时间: <span id="stat-time" style="color:#58a6ff; font-weight:bold;">00:00</span></div>
          <div>消灭敌军: <span id="stat-kills" style="color:#ff7b72; font-weight:bold;">0</span></div>
          <div>最终等级: <span id="stat-level" style="color:#ffd700; font-weight:bold;">1</span></div>
        </div>
        <button class="bus-btn" onclick="location.reload()">🔄 重新开始新的轮回</button>
      </div>
    </div>
  </div>

  <script>
{RuntimeSystemBus.get_runtime_system_bus_js()}

    // 领域数据与高清精灵资产配置
    const CHARACTERS_DATA = {chars_json};
    const SKILLS_DATA = {skills_json};
    const WAVES_DATA = {waves_json};
    const SPRITE_MAP = {sprite_map_json};

    // 预加载所有真实游戏资产图片
    const AssetManager = (function() {{
      const loadedImages = {{}};
      Object.keys(SPRITE_MAP).forEach(key => {{
        const img = new Image();
        img.src = SPRITE_MAP[key];
        loadedImages[key] = img;
      }});
      return {{
        get: function(key) {{ return loadedImages[key]; }}
      }};
    }})();

    const GameApp = (function() {{
      const canvas = document.getElementById('gameCanvas');
      const ctx = canvas.getContext('2d');

      let selectedChar = null;
      let player = null;
      let isPlaying = false;
      let matchTimer = 0;
      let killCount = 0;
      let animTick = 0;

      let enemies = [];
      let bullets = [];
      let gems = [];
      let activeOrbs = [];
      let lightningStrikes = [];

      const playerSkillLevels = {{}};

      function initCharSelectUI() {{
        const container = document.getElementById('char-selection-container');
        container.innerHTML = CHARACTERS_DATA.map(c => `
          <div class="char-card" id="card-${{c.id}}" onclick="GameApp.selectChar('${{c.id}}')">
            <img class="char-portrait-img" src="${{SPRITE_MAP[c.id]}}" alt="${{c.name}}" />
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="char-name" style="color:${{c.color}}">${{c.name}}</span>
            </div>
            <div class="char-desc">${{c.desc}}</div>
            <div class="char-stat">❤️ 生命: ${{c.hp}} | ⚡ 速度: ${{c.speed}}</div>
            <div style="color:#ffd700; font-size:0.75rem; margin-top:6px;">🌟 被动: ${{c.passive}}</div>
          </div>
        `).join('');
      }}

      function triggerLevelUp() {{
        AudioBus.play('levelup');
        isPlaying = false;

        const available = SKILLS_DATA.filter(s => (playerSkillLevels[s.id] || 0) < s.max_level);
        const shuffled = [...available].sort(() => Math.random() - 0.5).slice(0, 3);

        const container = document.getElementById('choice-container');
        container.innerHTML = shuffled.map(sk => {{
          const curLvl = playerSkillLevels[sk.id] || 0;
          const nextUpgrade = sk.upgrades[curLvl] || {{ desc: '最大强化' }};
          return `
            <div class="choice-card" onclick="GameApp.applySkillUpgrade('${{sk.id}}')">
              <div>
                <div class="choice-icon">${{sk.icon}}</div>
                <div class="choice-title">${{sk.name}} (Lv.${{curLvl + 1}})</div>
                <div class="choice-desc">${{nextUpgrade.desc}}</div>
              </div>
              <div style="color:#58a6ff; font-size:0.75rem; margin-top:12px; font-weight:bold;">[点击选择升级]</div>
            </div>
          `;
        }}).join('');

        document.getElementById('screen-levelup').classList.remove('bus-hidden');
      }}

      return {{
        init: function() {{
          initCharSelectUI();
        }},
        selectChar: function(charId) {{
          selectedChar = CHARACTERS_DATA.find(c => c.id === charId);
          document.querySelectorAll('.char-card').forEach(c => c.style.borderColor = '#30363d');
          const el = document.getElementById('card-' + charId);
          if (el) el.style.borderColor = '#00eeff';

          const btn = document.getElementById('start-battle-btn');
          btn.innerText = `出战英雄: ${{selectedChar.name}} [点击开战]`;
          btn.disabled = false;
        }},
        startMatch: function() {{
          if (!selectedChar) return;
          document.getElementById('screen-char-select').classList.add('bus-hidden');

          player = {{
            x: canvas.width / 2,
            y: canvas.height / 2,
            radius: 24, // 适配真实精灵尺寸
            hp: selectedChar.hp,
            maxHp: selectedChar.hp,
            speed: selectedChar.speed,
            color: selectedChar.color,
            level: 1,
            exp: 0,
            expNext: 100,
            knifeTimer: 0,
            lightningTimer: 0
          }};

          playerSkillLevels[selectedChar.starting_weapon] = 1;

          isPlaying = true;
          matchTimer = 0;
          killCount = 0;
          animTick = 0;
          enemies = [];
          bullets = [];
          gems = [];
          activeOrbs = [];
          updateHUD();
          requestAnimationFrame(GameApp.loop);

          setInterval(() => {{
            if (isPlaying) {{
              matchTimer++;
              const m = Math.floor(matchTimer / 60).toString().padStart(2, '0');
              const s = (matchTimer % 60).toString().padStart(2, '0');
              document.getElementById('hud-timer').innerText = `${{m}}:${{s}}`;
              
              if (matchTimer === 180) {{
                GameApp.spawnBoss();
              }}
            }}
          }}, 1000);
        }},
        applySkillUpgrade: function(skillId) {{
          playerSkillLevels[skillId] = (playerSkillLevels[skillId] || 0) + 1;
          document.getElementById('screen-levelup').classList.add('bus-hidden');
          isPlaying = true;
          requestAnimationFrame(GameApp.loop);
        }},
        spawnBoss: function() {{
          enemies.push({{
            isBoss: true,
            name: '深渊灭绝领主 · 贝希摩斯',
            x: canvas.width / 2,
            y: -80,
            radius: 55,
            hp: 4200,
            maxHp: 4200,
            speed: 0.85
          }});
          JuiceBus.triggerHit(5, 12);
        }},
        loop: function() {{
          if (!isPlaying) return;
          requestAnimationFrame(GameApp.loop);

          animTick++;
          if (!JuiceBus.isFrozen()) {{
            GameApp.update();
          }}
          JuiceBus.update();
          GameApp.draw();
        }},
        update: function() {{
          let dx = 0, dy = 0;
          if (keys['KeyW'] || keys['ArrowUp']) dy -= 1;
          if (keys['KeyS'] || keys['ArrowDown']) dy += 1;
          if (keys['KeyA'] || keys['ArrowLeft']) dx -= 1;
          if (keys['KeyD'] || keys['ArrowRight']) dx += 1;

          if (dx !== 0 && dy !== 0) {{
            dx *= 0.7071; dy *= 0.7071;
          }}

          const bootsBonus = 1 + (playerSkillLevels['passive_boots'] || 0) * 0.15;
          player.x += dx * player.speed * bootsBonus;
          player.y += dy * player.speed * bootsBonus;

          // 刚性空间边界
          player.x = Math.max(player.radius + 10, Math.min(canvas.width - player.radius - 10, player.x));
          player.y = Math.max(player.radius + 10, Math.min(canvas.height - player.radius - 10, player.y));

          // 环绕烈焰
          const flameLvl = playerSkillLevels['spinning_axe'] || 0;
          if (flameLvl > 0) {{
            const orbCount = flameLvl >= 5 ? 6 : (1 + flameLvl);
            activeOrbs = [];
            const angleSpeed = animTick * 0.045 * (1 + flameLvl * 0.1);
            for (let i = 0; i < orbCount; i++) {{
              const a = angleSpeed + (i * Math.PI * 2 / orbCount);
              const dist = 60 + flameLvl * 6;
              activeOrbs.push({{
                x: player.x + Math.cos(a) * dist,
                y: player.y + Math.sin(a) * dist,
                radius: 8 + flameLvl * 1.5,
                damage: 28 + flameLvl * 10
              }});
            }}
          }}

          // 穿刺飞刀
          const knifeLvl = playerSkillLevels['throwing_knives'] || 0;
          if (knifeLvl > 0) {{
            player.knifeTimer++;
            const interval = Math.max(20, 55 - knifeLvl * 7);
            if (player.knifeTimer >= interval && enemies.length > 0) {{
              player.knifeTimer = 0;
              const target = enemies.reduce((prev, curr) => {{
                return Math.hypot(curr.x - player.x, curr.y - player.y) < Math.hypot(prev.x - player.x, prev.y - player.y) ? curr : prev;
              }});
              const angle = Math.atan2(target.y - player.y, target.x - player.x);
              const knifeCount = knifeLvl >= 5 ? 8 : (1 + knifeLvl);
              for (let k = 0; k < knifeCount; k++) {{
                const spread = (k - (knifeCount - 1) / 2) * 0.16;
                bullets.push({{
                  x: player.x, y: player.y,
                  vx: Math.cos(angle + spread) * 8.5,
                  vy: Math.sin(angle + spread) * 8.5,
                  damage: 32 + knifeLvl * 12,
                  life: 65
                }});
              }}
              AudioBus.play('slash');
            }}
          }}

          // 雷霆轰顶
          const lightningLvl = playerSkillLevels['lightning_storm'] || 0;
          if (lightningLvl > 0) {{
            player.lightningTimer++;
            const lInterval = Math.max(35, 85 - lightningLvl * 12);
            if (player.lightningTimer >= lInterval && enemies.length > 0) {{
              player.lightningTimer = 0;
              const strikeCount = lightningLvl >= 5 ? enemies.length : Math.min(enemies.length, 1 + lightningLvl);
              for (let i = 0; i < strikeCount; i++) {{
                const e = enemies[Math.floor(Math.random() * enemies.length)];
                e.hp -= (55 + lightningLvl * 25);
                lightningStrikes.push({{ x: e.x, y: e.y, life: 10 }});
                JuiceBus.spawnText(e.x, e.y - 20, 55 + lightningLvl * 25, true);
                JuiceBus.triggerHit(2, 4);
                AudioBus.play('hit');
                if (e.hp <= 0) GameApp.killEnemy(e);
              }}
            }}
          }}

          // 弹道移动
          for (let i = bullets.length - 1; i >= 0; i--) {{
            const b = bullets[i];
            b.x += b.vx; b.y += b.vy; b.life--;
            for (let j = enemies.length - 1; j >= 0; j--) {{
              const e = enemies[j];
              if (Math.hypot(b.x - e.x, b.y - e.y) < (e.radius + 10)) {{
                const isCrit = Math.random() < 0.28;
                const dmg = isCrit ? b.damage * 2 : b.damage;
                e.hp -= dmg;
                JuiceBus.spawnText(e.x, e.y - 15, dmg, isCrit);
                JuiceBus.triggerHit(isCrit ? 4 : 2, isCrit ? 8 : 4);
                AudioBus.play('hit');
                b.life = 0;
                if (e.hp <= 0) GameApp.killEnemy(e);
                break;
              }}
            }}
            if (b.life <= 0) bullets.splice(i, 1);
          }}

          // 烈焰触碰
          activeOrbs.forEach(orb => {{
            enemies.forEach(e => {{
              if (Math.hypot(orb.x - e.x, orb.y - e.y) < (orb.radius + e.radius)) {{
                e.hp -= orb.damage * 0.05;
                if (Math.random() < 0.15) JuiceBus.spawnText(e.x, e.y - 15, Math.round(orb.damage), false);
                if (e.hp <= 0) GameApp.killEnemy(e);
              }}
            }});
          }});

          // 怪物生成
          if (Math.random() < 0.045 && enemies.length < 75) {{
            const edge = Math.floor(Math.random() * 4);
            let ex = 0, ey = 0;
            if (edge === 0) {{ ex = Math.random() * canvas.width; ey = -30; }}
            else if (edge === 1) {{ ex = canvas.width + 30; ey = Math.random() * canvas.height; }}
            else if (edge === 2) {{ ex = Math.random() * canvas.width; ey = canvas.height + 30; }}
            else {{ ex = -30; ey = Math.random() * canvas.height; }}

            const isFast = matchTimer > 45 && Math.random() < 0.35;
            enemies.push({{
              x: ex, y: ey,
              radius: isFast ? 18 : 22,
              hp: isFast ? 50 : 35 + matchTimer * 0.4,
              maxHp: isFast ? 50 : 35 + matchTimer * 0.4,
              speed: isFast ? 2.1 : 1.25
            }});
          }}

          enemies.forEach(e => {{
            const a = Math.atan2(player.y - e.y, player.x - e.x);
            e.x += Math.cos(a) * e.speed;
            e.y += Math.sin(a) * e.speed;

            if (Math.hypot(e.x - player.x, e.y - player.y) < (e.radius + player.radius)) {{
              player.hp -= e.isBoss ? 1.4 : 0.4;
              JuiceBus.triggerHit(2, 5);
              updateHUD();
              if (player.hp <= 0) GameApp.endMatch(false);
            }}
          }});

          // 经验磁吸
          const magnetBonus = 1 + (playerSkillLevels['passive_magnet'] || 0) * 0.6;
          const pickupRange = 70 * magnetBonus;

          for (let i = gems.length - 1; i >= 0; i--) {{
            const g = gems[i];
            const dist = Math.hypot(player.x - g.x, player.y - g.y);
            if (dist < pickupRange) {{
              const a = Math.atan2(player.y - g.y, player.x - g.x);
              g.x += Math.cos(a) * 8.5;
              g.y += Math.sin(a) * 8.5;
              if (dist < player.radius + 8) {{
                player.exp += g.val;
                AudioBus.play('gem');
                gems.splice(i, 1);
                if (player.exp >= player.expNext) {{
                  player.exp -= player.expNext;
                  player.level++;
                  player.expNext = Math.round(player.expNext * 1.35);
                  triggerLevelUp();
                }}
                updateHUD();
              }}
            }}
          }}

          for (let i = lightningStrikes.length - 1; i >= 0; i--) {{
            lightningStrikes[i].life--;
            if (lightningStrikes[i].life <= 0) lightningStrikes.splice(i, 1);
          }}
        }},
        killEnemy: function(e) {{
          enemies = enemies.filter(item => item !== e);
          killCount++;
          gems.push({{ x: e.x, y: e.y, val: e.isBoss ? 150 : 15, color: e.isBoss ? '#ffd700' : '#00eeff' }});
          if (e.isBoss) {{
            GameApp.endMatch(true);
          }}
        }},
        endMatch: function(isWin) {{
          isPlaying = false;
          const m = Math.floor(matchTimer / 60).toString().padStart(2, '0');
          const s = (matchTimer % 60).toString().padStart(2, '0');

          document.getElementById('end-title').innerText = isWin ? '🏆 歼灭大捷！深渊已平定！' : '💀 战术阵亡！残躯长眠于星海';
          document.getElementById('end-title').style.color = isWin ? '#ffd700' : '#ff4d4d';
          document.getElementById('end-desc').innerText = isWin
            ? `太不可思议了！你成功斩杀了【深渊灭绝领主】，歼灭了异星虫潮，完成了星际跃迁撤离！`
            : `你被汹涌的虫潮淹没，但在星空中留下了英勇的战斗数据记录！`;
          document.getElementById('stat-time').innerText = `${{m}}:${{s}}`;
          document.getElementById('stat-kills').innerText = killCount;
          document.getElementById('stat-level').innerText = player.level;

          document.getElementById('screen-gameover').classList.remove('bus-hidden');
        }},
        draw: function() {{
          ctx.save();
          ctx.clearRect(0, 0, canvas.width, canvas.height);

          JuiceBus.applyOffset(ctx);

          // 地面网格
          ctx.strokeStyle = '#162235'; ctx.lineWidth = 1;
          for (let x = 0; x < canvas.width; x += 40) {{
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
          }}
          for (let y = 0; y < canvas.height; y += 40) {{
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
          }}

          // 经验水晶
          gems.forEach(g => {{
            ctx.fillStyle = g.color; ctx.shadowColor = g.color; ctx.shadowBlur = 8;
            ctx.beginPath(); ctx.arc(g.x, g.y, 4.5, 0, Math.PI * 2); ctx.fill();
            ctx.shadowBlur = 0;
          }});

          // 环绕烈焰
          activeOrbs.forEach(orb => {{
            ctx.fillStyle = '#ff9900'; ctx.shadowColor = '#ff5500'; ctx.shadowBlur = 12;
            ctx.beginPath(); ctx.arc(orb.x, orb.y, orb.radius, 0, Math.PI * 2); ctx.fill();
            ctx.shadowBlur = 0;
          }});

          // 飞刀
          bullets.forEach(b => {{
            ctx.fillStyle = '#00eeff'; ctx.shadowColor = '#00eeff'; ctx.shadowBlur = 6;
            ctx.beginPath(); ctx.arc(b.x, b.y, 3.5, 0, Math.PI * 2); ctx.fill();
            ctx.shadowBlur = 0;
          }});

          // 👾 绘制生动怪物 (调用真实原画精灵贴图)
          const imgMonster = AssetManager.get('enemy_normal');
          const imgBoss = AssetManager.get('boss_titan');

          enemies.forEach(e => {{
            ctx.save();
            ctx.translate(e.x, e.y);

            // 怪物阴影
            ctx.fillStyle = 'rgba(0,0,0,0.3)';
            ctx.beginPath();
            ctx.ellipse(0, e.radius * 0.75, e.radius * 0.8, e.radius * 0.3, 0, 0, Math.PI * 2);
            ctx.fill();

            if (e.isBoss) {{
              // 巨型晶石熔岩 Boss (真实原画贴图)
              const breath = Math.sin(animTick * 0.08) * 3;
              if (imgBoss && imgBoss.complete) {{
                const bossW = 120, bossH = 120;
                ctx.drawImage(imgBoss, -bossW/2, -bossH/2 + breath, bossW, bossH);
              }}
            }} else {{
              // 真实小怪精灵贴图
              const walkBob = Math.sin(animTick * 0.15) * 2;
              if (imgMonster && imgMonster.complete) {{
                const mW = e.radius * 2.2, mH = e.radius * 2.2;
                ctx.drawImage(imgMonster, -mW/2, -mH/2 + walkBob, mW, mH);
              }}
            }}

            // 血条
            if (e.hp < e.maxHp) {{
              const pct = Math.max(0, e.hp / e.maxHp);
              const barW = e.isBoss ? 80 : 30;
              ctx.fillStyle = 'rgba(0,0,0,0.7)';
              ctx.fillRect(-barW/2, -e.radius - 12, barW, 5);
              ctx.fillStyle = e.isBoss ? '#ff0055' : '#70e000';
              ctx.fillRect(-barW/2, -e.radius - 12, barW * pct, 5);
            }}

            ctx.restore();
          }});

          // 👤 绘制玩家出战英雄 (调用真实商业原画精灵贴图)
          if (player && selectedChar) {{
            const imgHero = AssetManager.get(selectedChar.id);
            if (imgHero && imgHero.complete) {{
              ctx.save();
              ctx.translate(player.x, player.y);

              // 足底阴影
              ctx.fillStyle = 'rgba(0,0,0,0.35)';
              ctx.beginPath();
              ctx.ellipse(0, 20, 20, 7, 0, 0, Math.PI * 2);
              ctx.fill();

              // 步态呼吸起伏
              const breath = Math.sin(animTick * 0.08) * 2;
              const tilt = Math.sin(animTick * 0.12) * 0.05;
              ctx.rotate(tilt);

              // 绘制高清立绘精灵
              const heroSize = 64;
              ctx.drawImage(imgHero, -heroSize/2, -heroSize/2 - 6 + breath, heroSize, heroSize);

              ctx.restore();
            }}
          }}

          // 雷霆风暴
          lightningStrikes.forEach(l => {{
            ctx.strokeStyle = '#00eeff'; ctx.lineWidth = 3; ctx.shadowColor = '#00eeff'; ctx.shadowBlur = 15;
            ctx.beginPath();
            ctx.moveTo(l.x, 0); ctx.lineTo(l.x + (Math.random()*20-10), l.y/2); ctx.lineTo(l.x, l.y);
            ctx.stroke(); ctx.shadowBlur = 0;
          }});

          JuiceBus.renderTexts(ctx);

          ctx.restore();
        }}
      }};

      function updateHUD() {{
        if (!player) return;
        document.getElementById('hud-level').innerText = player.level;
        document.getElementById('hud-hp').innerText = Math.max(0, Math.round(player.hp));
        const pct = Math.min(100, (player.exp / player.expNext) * 100);
        document.getElementById('hud-exp-fill').style.width = pct + '%';
        document.getElementById('hud-exp-text').innerText = `EXP ${{player.exp}} / ${{player.expNext}}`;
      }}
    }})();

    const keys = {{}};
    window.addEventListener('keydown', e => keys[e.code] = true);
    window.addEventListener('keyup', e => keys[e.code] = false);
    window.addEventListener('blur', () => Object.keys(keys).forEach(k => keys[k] = false));

    GameApp.init();
  </script>
</body>
</html>"""

    @staticmethod
    def _compile_with_llm(
        domain_model: Dict[str, Any],
        provider: str,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """使用 LLM 结合领域模型生成动态游戏代码"""
        try:
            from core.llm_gateway import LLMGateway
            from core.prompt_template_engine import CodeGenPrompt

            title = domain_model.get("story_goals", {}).get("title", "未命名游戏")
            lore = domain_model.get("story_goals", {}).get("lore", "")
            characters = domain_model.get("characters", [])
            skills = domain_model.get("skills", [])
            waves = domain_model.get("waves", [])

            constraints = (
                f"背景与世界观: {lore}\n"
                f"角色列表: {json.dumps(characters, ensure_ascii=False)}\n"
                f"技能体系: {json.dumps(skills, ensure_ascii=False)}\n"
                f"关卡波次: {json.dumps(waves, ensure_ascii=False)}"
            )

            prompt = CodeGenPrompt.for_html5(
                title=title,
                genre="数据驱动创新RPG/动作",
                rules=constraints,
            )
            gw = LLMGateway(provider=provider, model=model)
            resp = gw.call(prompt.user, system=prompt.system)
            if resp.success and "<html" in resp.text.lower():
                from pipeline.completeness_guard import CompletenessGuard
                audit = CompletenessGuard.audit_game_code(resp.text)
                if audit.get("is_fully_qualified", False):
                    return resp.text.strip()
        except Exception as e:
            print(f"[DataDrivenCompiler] LLM 编译异常: {e}")
        return None
