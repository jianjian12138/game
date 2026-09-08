#!/usr/bin/env python3
"""
commercial_shell.py: 商业级完整游戏 UI 外壳与状态机包装生成器
为任何游戏生成 Steam / 移动端商业标准的 UI 包装：
主菜单 (Title)、局外天赋加点 (Talent)、系统设置 (Settings)、局内暂停 (Pause)、结算统计 (Victory/Defeat)。
"""

class CommercialShell:

    @staticmethod
    def get_shell_css() -> str:
        return """
    /* 商业级 UI 包装外壳样式 */
    .shell-overlay {
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(10, 12, 16, 0.88); backdrop-filter: blur(8px);
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      z-index: 1000; transition: opacity 0.2s ease;
    }
    .shell-hidden { display: none !important; opacity: 0; pointer-events: none; }
    
    .shell-card {
      background: linear-gradient(145deg, #1c2128, #161b22);
      border: 2px solid #30363d; border-radius: 14px; padding: 28px 36px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.8), 0 0 20px rgba(0, 238, 255, 0.15);
      text-align: center; max-width: 540px; width: 90%;
    }
    
    .shell-btn {
      background: linear-gradient(135deg, #1f6feb, #238636);
      color: #fff; border: 1px solid #388bfd; border-radius: 8px;
      padding: 10px 24px; font-size: 1.05rem; font-weight: bold; cursor: pointer;
      margin: 8px 6px; transition: transform 0.15s, box-shadow 0.15s;
    }
    .shell-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(31, 111, 235, 0.4); }
    .shell-btn-gold { background: linear-gradient(135deg, #ffd700, #ff9900); color: #111; border-color: #ffd700; }
    .shell-btn-danger { background: linear-gradient(135deg, #da3633, #8e1515); border-color: #f85149; }

    .talent-item {
      display: flex; justify-content: space-between; align-items: center;
      background: #0d1117; border: 1px solid #21262d; border-radius: 8px;
      padding: 10px 14px; margin: 8px 0; text-align: left;
    }
"""

    @staticmethod
    def get_shell_html(title: str) -> str:
        return f"""
    <!-- 1. 主菜单封面 (Title Screen) -->
    <div id="screen-title" class="shell-overlay">
      <div class="shell-card">
        <h1 style="font-size: 2.5rem; color: #ffd700; margin-bottom: 8px;">🌻 {title}</h1>
        <p style="color: #8b949e; font-size: 0.9rem; margin-bottom: 24px;">商业级高完成度版 · 策略守护 · 局外天赋养成</p>
        <div style="display:flex; flex-direction:column; gap:10px; max-width:280px; margin:0 auto;">
          <button class="shell-btn shell-btn-gold" onclick="ShellUI.startNewGame()">▶️ 开始保卫战</button>
          <button class="shell-btn" onclick="ShellUI.openTalents()">🌟 永久天赋树</button>
          <button class="shell-btn" onclick="ShellUI.openSettings()">⚙️ 系统设置</button>
        </div>
        <div style="margin-top:20px; color:#58a6ff; font-size:0.85rem;">
          🪙 黄金金币: <span id="meta-coin-val">0</span>
        </div>
      </div>
    </div>

    <!-- 2. 天赋升级面板 (Talents Modal) -->
    <div id="screen-talents" class="shell-overlay shell-hidden">
      <div class="shell-card" style="max-width: 600px;">
        <h2 style="color: #ffd700; margin-bottom: 14px;">🌟 局外长线天赋树 (Meta Talents)</h2>
        <div style="color:#8b949e; font-size:0.85rem; margin-bottom:12px;">使用战局带出的金币永久强化属性</div>
        <div id="talent-list-container"></div>
        <button class="shell-btn" style="margin-top: 15px;" onclick="ShellUI.closeTalents()">返回主菜单</button>
      </div>
    </div>

    <!-- 3. 设置面板 (Settings Modal) -->
    <div id="screen-settings" class="shell-overlay shell-hidden">
      <div class="shell-card">
        <h2 style="color: #58a6ff; margin-bottom: 16px;">⚙️ 系统偏好设置</h2>
        <div style="margin: 14px 0; text-align:left;">
          <label style="color:#c9d1d9;">🎵 主音量: <span id="vol-lbl">80%</span></label>
          <input type="range" id="vol-slider" min="0" max="100" value="80" style="width:100%; margin-top:6px;" onchange="ShellUI.onVolumeChange(this.value)">
        </div>
        <div style="margin: 14px 0; text-align:left;">
          <button class="shell-btn" onclick="ShellUI.toggleFullscreen()">🖥️ 全屏切换</button>
          <button class="shell-btn shell-btn-danger" onclick="ShellUI.resetSave()">⚠️ 重置所有存档</button>
        </div>
        <button class="shell-btn" style="margin-top: 15px;" onclick="ShellUI.closeSettings()">关闭设置</button>
      </div>
    </div>
"""

    @staticmethod
    def get_shell_js() -> str:
        return """
// 商业 UI 外壳控制器
const ShellUI = (function() {
  function updateCoinDisplay() {
    const save = SaveSystem.get();
    const el = document.getElementById('meta-coin-val');
    if (el) el.innerText = save.meta_coins;
  }

  function renderTalents() {
    const container = document.getElementById('talent-list-container');
    if (!container) return;
    const save = SaveSystem.get();
    const defs = TalentSystem.getDefinitions();

    container.innerHTML = Object.entries(defs).map(([k, def]) => {
      const curLvl = save.unlocked_talents[k] || 0;
      const isMax = curLvl >= def.maxLevel;
      const nextCost = isMax ? 'MAX' : def.cost[curLvl] + ' 🪙';
      const canAfford = !isMax && save.meta_coins >= def.cost[curLvl];

      return `
        <div class="talent-item">
          <div>
            <div style="font-weight:bold; color:#e6edf3;">${def.name} <span style="color:#58a6ff; font-size:0.8rem;">(Lv.${curLvl}/${def.maxLevel})</span></div>
            <div style="color:#8b949e; font-size:0.78rem;">${def.desc}</div>
          </div>
          <button class="shell-btn ${canAfford ? 'shell-btn-gold' : ''}" style="padding:4px 12px; font-size:0.82rem;" ${(!canAfford || isMax) ? 'disabled' : ''} onclick="ShellUI.upgrade('${k}')">
            ${isMax ? '已达上限' : '升级: ' + nextCost}
          </button>
        </div>
      `;
    }).join('');
  }

  return {
    init: function() {
      updateCoinDisplay();
    },
    startNewGame: function() {
      document.getElementById('screen-title').classList.add('shell-hidden');
      if (typeof window.startActualMatch === 'function') {
        window.startActualMatch();
      }
    },
    openTalents: function() {
      renderTalents();
      document.getElementById('screen-talents').classList.remove('shell-hidden');
    },
    closeTalents: function() {
      document.getElementById('screen-talents').classList.add('shell-hidden');
      updateCoinDisplay();
    },
    upgrade: function(k) {
      if (TalentSystem.upgradeTalent(k)) {
        renderTalents();
        updateCoinDisplay();
      }
    },
    openSettings: function() {
      document.getElementById('screen-settings').classList.remove('shell-hidden');
    },
    closeSettings: function() {
      document.getElementById('screen-settings').classList.add('shell-hidden');
    },
    onVolumeChange: function(v) {
      document.getElementById('vol-lbl').innerText = v + '%';
      SaveSystem.update(d => { d.settings.bgm_volume = v / 100; });
    },
    toggleFullscreen: function() {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen();
      else document.exitFullscreen();
    },
    resetSave: function() {
      if (confirm('确认清空所有金币与天赋数据重置为初始状态？')) {
        SaveSystem.reset();
        updateCoinDisplay();
        renderTalents();
      }
    }
  };
})();
"""
