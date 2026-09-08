document.addEventListener("DOMContentLoaded", () => {
  const agentList = document.getElementById("agent-list");
  const logBox = document.getElementById("log-box");
  const btnCreate = document.getElementById("btn-create");
  const btnResearch = document.getElementById("btn-research");
  const gameInput = document.getElementById("game-title-input");
  const genreSelect = document.getElementById("game-genre-select");
  const rulesInput = document.getElementById("game-rules-input");
  const gameFrame = document.getElementById("game-frame");
  const progressBar = document.getElementById("progress-bar");
  const hookStageText = document.getElementById("hook-stage-text");
  const activeAgentCount = document.getElementById("active-agent-count");

// DOM XSS 防御 (V5-05)
  function clearContainer(element) {
    if (element.replaceChildren) {
      element.replaceChildren();
    } else {
      while (element.firstChild) {
        element.removeChild(element.firstChild);
      }
    }
  }

  function appendLog(message, options = {}) {
    const entry = document.createElement("div");
    entry.className = options.className ? `log-entry ${options.className}` : "log-entry";
    if (options.color) entry.style.color = options.color;

    if (options.prefix) {
      const strong = document.createElement("strong");
      strong.textContent = options.prefix + " ";
      entry.appendChild(strong);
    }

    if (options.badges && options.badges.length > 0) {
      options.badges.forEach(b => {
        const badge = document.createElement("span");
        badge.className = b.className || "skill-badge";
        badge.textContent = b.text;
        if (b.style) Object.assign(badge.style, b.style);
        entry.appendChild(badge);
        entry.appendChild(document.createTextNode(" "));
      });
    }

    const textNode = document.createElement("span");
    textNode.textContent = message;
    entry.appendChild(textNode);

    logBox.appendChild(entry);
    logBox.scrollTop = logBox.scrollHeight;
    return entry;
  }

  const PRESET_RULES = {
    "cs": "3D FPS 射击规则：Three.js 3D WebGL PBR 渲染。鼠标控制第一人称准星视角，WASD移动，空格跳跃。左键开火射击，R键换弹。敌人具备 3D 寻路与巡逻追击 AI。Hitbox 区分头部(4x爆头暴击)与躯干伤害。消灭全图敌方特战队即获胜。",
    "我的世界": "3D 体素沙盒规则：Three.js 3D 空间三维网格。WASD移动，鼠标环顾，空格跳跃与重力物理。左键破坏方块，右键放置方块，数字键1-4切换草方块/泥土/石块/砖块材质。支持无限创造与建造。",
    "梦幻西游": "回合制 RPG 战斗规则：3v3 双方阵营站位对决。玩家可下达普通攻击、大唐官府【横扫千军(三连击)】、魔王寨【三昧真火(法暴)】、化生寺【普渡众生(群疗)】等指令。严密回合状态机循环，暴击飘字与胜负结算。",
    "开心消消乐": "经典三消规则：8x8 宝石网格，点击/拖拽相邻宝石交换位置。三连消除并触发重力掉落填充；四连生成范围炸弹，五连生成魔力鸟全屏特效。在限制步数内达成目标得分通关。",
    "象棋": "正统象棋棋规：车直冲、马走日带蹩马腿、相走田塞象眼不跨河、仕走斜线、帅走直角不照面、炮隔山打、兵过河横走、红方先行、绝杀判定。",
    "斗地主": "正规扑克斗地主：3人对局、叫地主底牌3张、单牌/对子/三张/炸弹压制规则、AI智能出牌与率先打完判定胜利。",
    "扫雷": "正统扫雷规则：10x10网格矩阵，随机埋设15颗地雷。左键点击翻开方块，周围无雷时自动递归连锁展开；右键插旗标记地雷；排完所有非雷方块即获胜。",
    "2048": "2048规则：4x4网格，方向键滑动方块，相同数字碰撞合并相加(2+2=4)，每次滑动随机生成新方块，合成2048获胜。",
    "五子棋": "五子棋规则：15x15网格、黑先白后、横竖斜任意方向5子连珠即获胜、禁止重复落子。",
    "贪吃蛇": "街机贪吃蛇：20x20空间矩阵、方向键控制蛇头、吃苹果身体增长、撞墙或咬自身死亡判定。",
    "打砖块": "物理弹球打砖块：挡板左右移动、多层彩色砖块消除、球体物理反弹与坠底死亡判定。"
  };

  const PRESET_TITLES = {
    "cs": "反恐前线：幽灵突击 3D",
    "我的世界": "我的世界：无尽体素 3D",
    "梦幻西游": "梦幻神魔录：大闹天宫",
    "开心消消乐": "开心消消乐：森林大冒险",
    "象棋": "正统中国象棋",
    "斗地主": "经典斗地主",
    "扫雷": "经典扫雷",
    "2048": "2048 数字方块"
  };

  genreSelect.addEventListener("change", () => {
    const val = genreSelect.value;
    if (PRESET_RULES[val]) {
      rulesInput.value = PRESET_RULES[val];
      gameInput.value = PRESET_TITLES[val] || ("正统" + val);
    }
  });

  // 智能体全网检索规则功能 (使用 textContent 零拼接)
  btnResearch.addEventListener("click", () => {
    const query = gameInput.value.trim();
    if (!query) {
      alert("请先输入想要调研的游戏名称！");
      return;
    }
    btnResearch.disabled = true;
    clearContainer(logBox);
    appendLog(`🔍 [主策划 & 叙事专家] 启动全网规则检索与竞品机制调研：《${query}》...`, { className: "highlight" });

    clearAllActiveAgents();
    const designerCard = document.getElementById("agent-card-lead_game_designer");
    if (designerCard) {
      designerCard.classList.add("active-working");
      designerCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    fetch("/api/research_rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    })
      .then(res => res.json())
      .then(res => {
        btnResearch.disabled = false;
        rulesInput.value = res.extracted_rules || "";
        if (res.title) gameInput.value = res.title;

        appendLog(`数据来源: ${res.source || "网络检索"}`, { prefix: "✅ [规则提炼完成]" });
        appendLog(`📜 提炼规则: ${res.extracted_rules || ""}`, { color: "#ffd700" });
      })
      .catch(err => {
        btnResearch.disabled = false;
        appendLog(`❌ 调研失败: ${String(err)}`, { color: "#ff3366" });
      });
  });

  // 1. 加载 49+ 个智能体名录 (使用 DOM createElement 与 textContent 构造)
  fetch("/api/agents")
    .then(res => res.json())
    .then(data => {
      const depts = {};
      data.forEach(a => {
        depts[a.department_name] = depts[a.department_name] || [];
        depts[a.department_name].push(a);
      });

      clearContainer(agentList);
      Object.entries(depts).forEach(([dName, agents]) => {
        const deptGroup = document.createElement("div");
        deptGroup.className = "dept-group";

        const deptTitle = document.createElement("div");
        deptTitle.className = "dept-name";
        deptTitle.textContent = `${dName} (${agents.length})`;
        deptGroup.appendChild(deptTitle);

        agents.forEach(a => {
          const item = document.createElement("div");
          item.className = "agent-item";
          item.id = `agent-card-${a.id}`;

          const header = document.createElement("div");
          header.className = "agent-name";

          const nameSpan = document.createElement("span");
          nameSpan.textContent = a.name;
          header.appendChild(nameSpan);

          const tagSpan = document.createElement("span");
          tagSpan.className = "agent-tag";
          tagSpan.textContent = "工作中";
          header.appendChild(tagSpan);

          const roleDiv = document.createElement("div");
          roleDiv.className = "agent-role";
          roleDiv.textContent = a.role;

          item.appendChild(header);
          item.appendChild(roleDiv);
          deptGroup.appendChild(item);
        });

        agentList.appendChild(deptGroup);
      });
    });

  // 2. 逐步流式推演协同流水线
  btnCreate.addEventListener("click", () => {
    const title = gameInput.value.trim() || "反恐前线：幽灵突击 3D";
    const genre = genreSelect.value;
    const custom_rules = rulesInput.value.trim();

    btnCreate.disabled = true;
    clearContainer(logBox);
    appendLog(`⚡ [Pipeline] 启动 12 个生命周期 Hooks 流水线：《${title}》(${genre}) 专家入驻开发...`, { className: "highlight" });
    progressBar.style.width = "0%";
    hookStageText.textContent = "立项筹备中...";

    fetch("/api/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, genre, custom_rules })
    })
      .then(res => res.json())
      .then(res => {
        const steps = res.steps || [];
        playWorkflowSteps(steps, 0, () => {
          btnCreate.disabled = false;
          progressBar.style.width = "100%";
          hookStageText.textContent = "✅ 商业工程交付就绪 (Godot 4已导出)";
          activeAgentCount.textContent = "全部就绪";
          clearAllActiveAgents();

          reloadGame();
        });
      })
      .catch(err => {
        btnCreate.disabled = false;
        appendLog(`❌ 生成失败: ${String(err)}`, { color: "#ff3366" });
      });
  });

  function playWorkflowSteps(steps, index, onComplete) {
    if (index >= steps.length) {
      if (onComplete) onComplete();
      return;
    }

    const step = steps[index];
    const progress = Math.round(((index + 1) / steps.length) * 100);
    progressBar.style.width = progress + "%";
    hookStageText.textContent = `[${index + 1}/12] ${step.phase} (${step.hook})`;

    // 高亮正在工作的智能体
    clearAllActiveAgents();
    if (step.active_agents && step.active_agents.length > 0) {
      activeAgentCount.textContent = `🔥 ${step.active_agents.length} 位专家协同中`;
      step.active_agents.forEach(aId => {
        const card = document.getElementById("agent-card-" + aId);
        if (card) {
          card.classList.add("active-working");
          card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      });
    }

    // 日志追加：纯 DOM 构造安全追加
    const badges = [];
    if (step.used_skills && step.used_skills.length > 0) {
      step.used_skills.forEach(s => {
        badges.push({ text: s, className: "skill-badge" });
      });
    }
    if (step.knowledge_module) {
      badges.push({
        text: `📚 ${step.knowledge_module}`,
        className: "skill-badge",
        style: { background: "#093b4f", color: "#00eeff", border: "1px solid #00eeff" }
      });
    }

    appendLog(step.log || "", {
      prefix: `[Hook: ${step.hook}]`,
      badges: badges
    });

    setTimeout(() => {
      playWorkflowSteps(steps, index + 1, onComplete);
    }, 320);
  }

  function clearAllActiveAgents() {
    document.querySelectorAll(".agent-item.active-working").forEach(el => {
      el.classList.remove("active-working");
    });
  }

  window.reloadGame = function() {
    gameFrame.src = "about:blank";
    setTimeout(() => {
      gameFrame.src = "/output/index.html?v=" + Date.now();
      gameFrame.focus();
    }, 120);
  };
});
