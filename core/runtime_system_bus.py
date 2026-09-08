#!/usr/bin/env python3
"""
runtime_system_bus.py: 通用工业底座运行时总线 (Universal Runtime System Bus)
Agent 正统研发逻辑第二层：封装成熟的 60fps 驱动、刚性空间封闭、4层打击感 (Juice)、
经验平滑磁吸、角色选择与升级三选一卡牌弹窗调度器。
"""

class RuntimeSystemBus:

    @staticmethod
    def get_system_bus_css() -> str:
        """返回高保真商业游戏全套 UI 样式 (包含角色选择、三选一技能卡牌、HUD、结算)"""
        return """
    * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
    body {
      background: #090c10; color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-height: 100vh; overflow: hidden;
    }
    #game-container {
      position: relative; width: 920px; height: 600px;
      border: 3px solid #30363d; border-radius: 12px;
      box-shadow: 0 25px 70px rgba(0,0,0,0.9), 0 0 30px rgba(0, 238, 255, 0.15);
      background: #0d1117; overflow: hidden;
    }
    canvas { display: block; width: 100%; height: 100%; background: #0b1320; }

    /* 顶部高精度 HUD */
    #hud-overlay {
      position: absolute; top: 0; left: 0; width: 100%; height: 64px;
      padding: 10px 24px; display: flex; align-items: center; justify-content: space-between;
      pointer-events: none; z-index: 50; background: linear-gradient(180deg, rgba(13,17,23,0.92) 0%, transparent 100%);
    }
    .exp-bar-container {
      flex: 1; max-width: 480px; height: 14px; background: #21262d;
      border: 1px solid #30363d; border-radius: 7px; overflow: hidden; position: relative; margin: 0 20px;
    }
    .exp-bar-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #00eeff, #38ef7d); transition: width 0.15s ease; }
    .exp-bar-text { position: absolute; width: 100%; text-align: center; font-size: 10px; font-weight: bold; line-height: 14px; color: #fff; text-shadow: 0 1px 2px #000; }

    /* 商业全覆盖浮层面板 */
    .bus-modal {
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(10, 14, 22, 0.88); backdrop-filter: blur(8px);
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      z-index: 100; transition: opacity 0.2s;
    }
    .bus-hidden { display: none !important; opacity: 0; pointer-events: none; }
    
    .bus-card {
      background: linear-gradient(145deg, #161b22, #0d1117);
      border: 2px solid #30363d; border-radius: 14px; padding: 28px 36px;
      text-align: center; max-width: 780px; width: 92%; box-shadow: 0 20px 60px rgba(0,0,0,0.8);
    }
    .bus-btn {
      background: linear-gradient(135deg, #1f6feb, #238636); color: #fff;
      border: 1px solid #388bfd; border-radius: 8px; padding: 12px 28px;
      font-size: 1.1rem; font-weight: bold; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
    }
    .bus-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(31, 111, 235, 0.5); }
    
    /* 角色选择卡片网格 */
    .char-grid { display: flex; gap: 16px; margin: 24px 0; justify-content: center; }
    .char-card {
      flex: 1; max-width: 220px; background: #0d1117; border: 2px solid #30363d;
      border-radius: 10px; padding: 18px 14px; cursor: pointer; transition: all 0.2s ease; text-align: left;
    }
    .char-card:hover { transform: translateY(-4px); border-color: #00eeff; box-shadow: 0 8px 24px rgba(0,238,255,0.25); }
    .char-name { font-size: 1.1rem; font-weight: bold; color: #fff; margin-bottom: 6px; }
    .char-desc { font-size: 0.8rem; color: #8b949e; line-height: 1.4; margin-bottom: 10px; }
    .char-stat { font-size: 0.78rem; color: #58a6ff; }

    /* 技能升级三选一卡片网格 */
    .choice-grid { display: flex; gap: 16px; margin: 20px 0; width: 100%; justify-content: center; }
    .choice-card {
      flex: 1; max-width: 210px; background: #161b22; border: 2px solid #388bfd;
      border-radius: 10px; padding: 18px 14px; cursor: pointer; transition: transform 0.15s, border-color 0.15s;
      display: flex; flex-direction: column; justify-content: space-between; text-align: left;
    }
    .choice-card:hover { transform: translateY(-5px); border-color: #ffd700; box-shadow: 0 10px 30px rgba(255, 215, 0, 0.3); }
    .choice-icon { font-size: 2.2rem; margin-bottom: 8px; }
    .choice-title { font-size: 1.05rem; font-weight: bold; color: #ffd700; margin-bottom: 6px; }
    .choice-desc { font-size: 0.82rem; color: #c9d1d9; line-height: 1.4; }
"""

    @staticmethod
    def get_runtime_system_bus_js() -> str:
        """返回零外部依赖、高保真 Canvas 工业底座总线驱动核心"""
        return """
// =================================================================
// 🎮 工业底座通用运行时总线 (Universal Runtime Bus)
// =================================================================

// 1. 刀刀到肉的 4 层复合打击感控制器 (Juice Engine)
const JuiceBus = (function() {
  let hitstop = 0;
  let shake = 0;
  let screenShake = 0; // Trauma 创伤震屏系统
  const floatingNumbers = [];
  const floatingTexts = floatingNumbers;

  return {
    triggerHit: function(frames = 3, shakePower = 6) {
      hitstop = frames;
      shake = shakePower;
      screenShake = shakePower;
    },
    spawnText: function(x, y, text, isCrit = false) {
      floatingNumbers.push({
        x: x + (Math.random() * 16 - 8),
        y: y,
        text: isCrit ? `💥${text}!` : `${text}`,
        color: isCrit ? '#ffd700' : '#ffffff',
        size: isCrit ? 22 : 15,
        life: 25,
        vy: -1.6
      });
    },
    update: function() {
      if (shake > 0.1) shake *= 0.86; else shake = 0;
      for (let i = floatingNumbers.length - 1; i >= 0; i--) {
        const fn = floatingNumbers[i];
        fn.y += fn.vy;
        fn.life--;
        if (fn.life <= 0) floatingNumbers.splice(i, 1);
      }
    },
    isFrozen: function() {
      if (hitstop > 0) { hitstop--; return true; }
      return false;
    },
    applyOffset: function(ctx) {
      if (shake > 0.1) {
        ctx.translate((Math.random()*2 - 1)*shake, (Math.random()*2 - 1)*shake);
      }
    },
    renderTexts: function(ctx) {
      ctx.save();
      ctx.textAlign = 'center';
      for (const fn of floatingNumbers) {
        ctx.font = `bold ${fn.size}px sans-serif`;
        ctx.fillStyle = fn.color;
        ctx.shadowColor = '#000'; ctx.shadowBlur = 4;
        ctx.fillText(fn.text, fn.x, fn.y);
      }
      ctx.restore();
    }
  };
})();

// 2. 原生 WebAudio 毫秒级无延迟合成器 (原生音效层叠)
const AudioBus = (function() {
  let actx = null;
  function ensureContext() {
    if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
    if (actx.state === 'suspended') actx.resume();
  }
  return {
    play: function(type) {
      ensureContext();
      if (!actx) return;
      const t = actx.currentTime;
      const osc = actx.createOscillator();
      const gain = actx.createGain();
      osc.connect(gain); gain.connect(actx.destination);

      if (type === 'slash') {
        osc.type = 'triangle'; osc.frequency.setValueAtTime(450, t); osc.frequency.exponentialRampToValueAtTime(80, t + 0.08);
        gain.gain.setValueAtTime(0.25, t); gain.gain.linearRampToValueAtTime(0.01, t + 0.08);
        osc.start(t); osc.stop(t + 0.08);
      } else if (type === 'gem') {
        osc.type = 'sine'; osc.frequency.setValueAtTime(987.77, t); osc.frequency.setValueAtTime(1318.5, t + 0.04);
        gain.gain.setValueAtTime(0.18, t); gain.gain.linearRampToValueAtTime(0.01, t + 0.1);
        osc.start(t); osc.stop(t + 0.1);
      } else if (type === 'hit') {
        osc.type = 'sawtooth'; osc.frequency.setValueAtTime(120, t); osc.frequency.exponentialRampToValueAtTime(40, t + 0.06);
        gain.gain.setValueAtTime(0.3, t); gain.gain.linearRampToValueAtTime(0.01, t + 0.06);
        osc.start(t); osc.stop(t + 0.06);
      } else if (type === 'levelup') {
        osc.type = 'triangle';
        [523.25, 659.25, 783.99, 1046.5].forEach((freq, idx) => {
          const oscN = actx.createOscillator();
          const gainN = actx.createGain();
          oscN.type = 'triangle';
          oscN.connect(gainN); gainN.connect(actx.destination);
          oscN.frequency.setValueAtTime(freq, t + idx * 0.08);
          gainN.gain.setValueAtTime(0.2, t + idx * 0.08);
          gainN.gain.linearRampToValueAtTime(0.01, t + (idx + 1) * 0.08);
          oscN.start(t + idx * 0.08); oscN.stop(t + (idx + 1) * 0.08);
        });
      }
    }
  };
})();
const SoundFX = AudioBus;
const AudioEngine = AudioBus;
"""
