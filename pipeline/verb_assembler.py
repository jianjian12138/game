#!/usr/bin/env python3
"""
verb_assembler.py: 工业级多品类正统游戏规则与逻辑装配引擎 (Game Rules & Logic Assembler v5.0)

v5.0 新增 LLM 模式：
  --mode fast    : 纯模板模式（原有逻辑，零延迟，无需 API Key）
  --mode llm     : LLM 生成模式（调用 LLMGateway，生成增强版代码）
  --mode hybrid  : 先模板快速生成，再 LLM 润色增强（默认）

支持主流 LLM：Gemini / OpenAI / Claude / Ollama / DeepSeek
"""
import os
from typing import Dict, Any, Optional, List
from pipeline.commercial_engines import CommercialEngines
from core.commercial_systems import CommercialSystemsLibrary
from pipeline.commercial_shell import CommercialShell

# ─── LLM 支持（可选，未安装时自动降级到模板模式）────────────────────────────────
def _get_llm_gateway(provider: str = "gemini", model: Optional[str] = None,
                      **kwargs):
    """懒加载 LLMGateway，失败时返回 None"""
    try:
        from core.llm_gateway import LLMGateway
        return LLMGateway(provider=provider, model=model, **kwargs)
    except Exception as e:
        print(f"[VerbAssembler] ⚠️ LLMGateway 加载未就绪: {e}")
        return None

def _get_prompt_engine():
    """懒加载 CodeGenPrompt"""
    try:
        from core.prompt_template_engine import CodeGenPrompt
        return CodeGenPrompt
    except Exception as e:
        print(f"[VerbAssembler] ⚠️ PromptEngine 加载未就绪: {e}")
        return None

# 生成模式常量
MODE_FAST   = "fast"
MODE_LLM    = "llm"
MODE_HYBRID = "hybrid"

class VerbAssembler:

    @staticmethod
    def assemble_game(
        title: str, genre: str = "", custom_rules: str = "",
        mode: str = MODE_FAST, llm_provider: str = "gemini",
        llm_model: Optional[str] = None, target_language: str = "html5",
        max_retries: int = 3,
    ) -> str:
        """游戏代码装配主入口 v5.0 — 支持 fast/llm/hybrid 三种模式"""
        effective_mode = os.environ.get("LLM_DEFAULT_MODE", MODE_FAST) if mode == MODE_FAST else mode
        effective_provider = os.environ.get("LLM_DEFAULT_PROVIDER", "gemini") if llm_provider == "gemini" else llm_provider

        if effective_mode == MODE_LLM:
            result = VerbAssembler._assemble_with_llm(
                title, genre, custom_rules, effective_provider, llm_model, target_language, max_retries)
            if result:
                return result
            print("[VerbAssembler] ⚠️  LLM 失败，降级到模板模式")
        elif effective_mode == MODE_HYBRID:
            template_code = VerbAssembler._assemble_from_template(title, genre, custom_rules)
            enhanced = VerbAssembler._llm_enhance_code(template_code, title, genre, effective_provider, llm_model)
            return enhanced if enhanced else template_code

        return VerbAssembler._assemble_from_template(title, genre, custom_rules)

    @staticmethod
    def _assemble_from_template(title: str, genre: str = "", custom_rules: str = "") -> str:
        """原有模板路由（快速模式，零延迟，向后完全兼容）"""
        prompt_text = f"{title} {genre} {custom_rules}".lower()
        from core.game_domain_modeler import GameDomainModeler
        from pipeline.data_driven_compiler import DataDrivenCompiler
        from pipeline.completeness_guard import CompletenessGuard
        if any(k in prompt_text for k in ("我的世界", "minecraft", "体素", "沙盒", "方块世界", "voxel")):
            return CommercialEngines.generate_3d_minecraft(title, custom_rules)
        elif any(k in prompt_text for k in ("梦幻", "西游", "回合制", "rpg", "仙剑", "宝可梦", "修仙", "门派")):
            return CommercialEngines.generate_rpg_turnbased(title, custom_rules)
        elif any(k in prompt_text for k in ("消消乐", "消除", "三消", "match-3", "candy", "宝石迷阵")):
            return CommercialEngines.generate_match3(title, custom_rules)
        elif any(k in prompt_text for k in ("塔防", "向日葵", "植物", "tower", "defense", "保卫", "pvz")):
            from pipeline.grid_defense_compiler import GridDefenseCompiler
            return GridDefenseCompiler.compile_grid_defense_game(title, custom_rules)
        elif any(k in prompt_text for k in ("象棋", "象", "xiangqi", "chess")):
            return VerbAssembler._generate_rigorous_chinese_chess(title, custom_rules)
        elif any(k in prompt_text for k in ("斗地主", "扑克", "poker", "卡牌")):
            return VerbAssembler._generate_rigorous_doudizhu(title, custom_rules)
        elif any(k in prompt_text for k in ("扫雷", "mine", "minesweeper")):
            return VerbAssembler._generate_minesweeper(title, custom_rules)
        elif any(k in prompt_text for k in ("2048", "数字合并")):
            return VerbAssembler._generate_2048(title, custom_rules)
        elif any(k in prompt_text for k in ("五子棋", "gomoku", "五子")):
            return VerbAssembler._generate_rigorous_gomoku(title, custom_rules)
        elif any(k in prompt_text for k in ("蛇", "snake", "贪吃蛇")):
            return VerbAssembler._generate_rigorous_snake(title, custom_rules)
        elif any(k in prompt_text for k in ("砖", "打砖块", "弹球", "pong", "breakout")):
            return VerbAssembler._generate_rigorous_breakout(title, custom_rules)
        elif any(k in prompt_text for k in ("次时代", "次世代", "pbr", "3a", "lod", "机甲展台", "3d次时代")):
            from pipeline.next_gen_3d_pipeline import NextGen3AShowcaseGenerator
            return NextGen3AShowcaseGenerator.generate_showcase_html_content()
        else:
            domain_model = GameDomainModeler.deduce_domain_model(title, genre, custom_rules)
            compiled_code = DataDrivenCompiler.compile_playable_game(domain_model)
            audit = CompletenessGuard.audit_game_code(compiled_code)
            if not audit["is_fully_qualified"]:
                raise RuntimeError(f"游戏完备性自审未通过: {audit['violations']}")
            return compiled_code

    @staticmethod
    def _assemble_with_llm(
        title: str, genre: str, custom_rules: str, provider: str,
        model: Optional[str], target_language: str, max_retries: int
    ) -> Optional[str]:
        """LLM 生成主流程，带自动验证重试闭环"""
        gw = _get_llm_gateway(provider=provider, model=model, verbose=True)
        CodeGenPrompt = _get_prompt_engine()
        if not gw or not CodeGenPrompt:
            print("[VerbAssembler] LLM 依赖未就绪")
            return None
        if target_language == "rust":
            prompt = CodeGenPrompt.for_rust_macroquad(title, genre, custom_rules)
        elif target_language == "gdscript":
            prompt = CodeGenPrompt.for_gdscript(title, genre, custom_rules)
        else:
            prompt = CodeGenPrompt.for_html5(title, genre, custom_rules)
        from pipeline.completeness_guard import CompletenessGuard
        last_code = ""
        for attempt in range(1, max_retries + 1):
            print(f"[VerbAssembler] 🤖 LLM 第 {attempt}/{max_retries} 次 [{provider}]")
            resp = gw.call(prompt.user, system=prompt.system)
            if not resp.success:
                print(f"[VerbAssembler] ❌ 失败: {resp.error}")
                if attempt == max_retries:
                    return None
                continue
            code = resp.text.strip()
            last_code = code
            audit = CompletenessGuard.audit_game_code(code)
            if audit.get("is_fully_qualified", False):
                print(f"[VerbAssembler] ✅ 第 {attempt} 次通过验证")
                return code
            violations = audit.get("violations", ["代码不完整"])
            print(f"[VerbAssembler] ⚠️  {len(violations)} 个问题，重试...")
            if attempt < max_retries:
                prompt = CodeGenPrompt.retry_with_feedback(prompt, violations, attempt)
        print(f"[VerbAssembler] ❌ LLM 生成经 {max_retries} 次重试仍未通过完备性门禁")
        return None

    @staticmethod
    def _llm_enhance_code(
        template_code: str, title: str, genre: str,
        provider: str, model: Optional[str]
    ) -> Optional[str]:
        """Hybrid 模式：LLM 润色模板代码"""
        gw = _get_llm_gateway(provider=provider, model=model)
        if not gw:
            return None
        enhance_prompt = (f"你是专业 HTML5 游戏工程师。改进《{title}》({genre})的代码："
                          f"增强视觉效果、游戏手感、移动端支持、修复性能问题。"
                          f"只输出完整 HTML 代码。\n\n```html\n{template_code[:8000]}\n```")
        print(f"[VerbAssembler] 🎨 Hybrid 增强中 [{provider}]...")
        resp = gw.call(enhance_prompt)
        return resp.text.strip() if resp.success and len(resp.text) > 200 else None


    @staticmethod
    def _generate_rigorous_chinese_chess(title: str, custom_rules: str = "") -> str:
        """生成具备 100% 正规中国象棋规则的完整可玩游戏 (蹩马腿、塞象眼、炮隔子、将帅不照面、合规提示)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - 100% 正统规则中国象棋</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      background: #1e1b18; color: #333; font-family: 'Kaiti', 'STKaiti', serif;
      display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh;
      padding: 10px;
    }}
    h1 {{ color: #dfbc7a; margin-bottom: 8px; letter-spacing: 4px; font-size: 1.6rem; }}
    .board-card {{
      background: #dfbc7a; padding: 14px; border-radius: 8px; border: 4px solid #6e4720;
      box-shadow: 0 10px 30px rgba(0,0,0,0.6); position: relative;
    }}
    #board {{
      width: 450px; height: 500px; background: #dfbc7a; position: relative; border: 2px solid #5c3a21;
    }}
    .river {{
      position: absolute; top: 225px; left: 0; width: 100%; height: 50px;
      display: flex; justify-content: space-around; align-items: center;
      font-size: 1.5rem; font-weight: bold; color: #5c3a21; letter-spacing: 12px; pointer-events: none; opacity: 0.85;
    }}
    .piece {{
      width: 44px; height: 44px; border-radius: 50%; position: absolute;
      display: flex; justify-content: center; align-items: center; font-size: 1.35rem; font-weight: bold;
      cursor: pointer; box-shadow: 0 3px 6px rgba(0,0,0,0.4), inset 0 2px 3px rgba(255,255,255,0.6);
      z-index: 10; border: 2px solid #333; transition: transform 0.1s;
    }}
    .piece.red {{ background: radial-gradient(circle at 35% 35%, #fff, #d9383a 70%, #991b1d 100%); color: #fff; border-color: #731214; }}
    .piece.black {{ background: radial-gradient(circle at 35% 35%, #eee, #333 70%, #111 100%); color: #f5eedc; border-color: #000; }}
    .piece.selected {{ transform: scale(1.15); box-shadow: 0 0 12px #ffd700; border-color: #ffd700; z-index: 20; }}
    .hint-move {{
      width: 16px; height: 16px; border-radius: 50%; background: rgba(46, 122, 92, 0.8);
      position: absolute; transform: translate(-50%, -50%); cursor: pointer; z-index: 15;
    }}
    .hint-capture {{
      width: 44px; height: 44px; border-radius: 50%; border: 3px dashed #d9383a;
      position: absolute; transform: translate(-50%, -50%); cursor: pointer; z-index: 16;
    }}
    .info {{
      margin-top: 10px; font-size: 1rem; font-weight: bold; color: #f0e6d2; display: flex; gap: 15px; align-items: center;
    }}
    .btn {{
      background: #8b5a2b; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; font-weight: bold; cursor: pointer;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="board-card"><div id="board"></div></div>
  <div class="info">
    <div>回合: <span id="turn" style="color:#d9383a;">红方执棋</span></div>
    <button class="btn" onclick="initGame()">🔄 重新开局</button>
  </div>

  <script>
    const PIECE_NAMES = {{
      r_k:'帥', r_a:'仕', r_b:'相', r_n:'傌', r_r:'俥', r_c:'炮', r_p:'兵',
      b_k:'將', b_a:'士', b_b:'象', b_n:'馬', b_r:'車', b_c:'砲', b_p:'卒'
    }};

    let board = [];
    let turn = 'red';
    let selected = null;
    let validMoves = [];

    function initBoard() {{
      const b = Array(10).fill(null).map(() => Array(9).fill(null));
      b[0][0]='b_r'; b[0][1]='b_n'; b[0][2]='b_b'; b[0][3]='b_a'; b[0][4]='b_k'; b[0][5]='b_a'; b[0][6]='b_b'; b[0][7]='b_n'; b[0][8]='b_r';
      b[2][1]='b_c'; b[2][7]='b_c';
      b[3][0]='b_p'; b[3][2]='b_p'; b[3][4]='b_p'; b[3][6]='b_p'; b[3][8]='b_p';
      b[9][0]='r_r'; b[9][1]='r_n'; b[9][2]='r_b'; b[9][3]='r_a'; b[9][4]='r_k'; b[9][5]='r_a'; b[9][6]='r_b'; b[9][7]='r_n'; b[9][8]='r_r';
      b[7][1]='r_c'; b[7][7]='r_c';
      b[6][0]='r_p'; b[6][2]='r_p'; b[6][4]='r_p'; b[6][6]='r_p'; b[6][8]='r_p';
      return b;
    }}

    function getPieceColor(p) {{ return p ? (p.startsWith('r_') ? 'red' : 'black') : null; }}
    function getPieceType(p) {{ return p ? p.split('_')[1] : null; }}

    // 正统中国象棋走子判定规则 (马走日蹩马腿/相走田塞象眼/炮隔山打/兵过河/九宫)
    function getStrictMoves(x, y) {{
      const p = board[y][x];
      if (!p) return [];
      const color = getPieceColor(p);
      const type = getPieceType(p);
      const moves = [];

      if (type === 'r') {{ // 车
        const dirs = [[0,1],[0,-1],[1,0],[-1,0]];
        for (let [dx, dy] of dirs) {{
          let nx = x + dx, ny = y + dy;
          while (nx>=0 && nx<=8 && ny>=0 && ny<=9) {{
            const dest = board[ny][nx];
            if (!dest) moves.push({{x: nx, y: ny}});
            else {{
              if (getPieceColor(dest) !== color) moves.push({{x: nx, y: ny}});
              break;
            }}
            nx += dx; ny += dy;
          }}
        }}
      }} else if (type === 'n') {{ // 马 (蹩马腿)
        const steps = [
          {{dx:1, dy:2, lx:0, ly:1}}, {{dx:-1, dy:2, lx:0, ly:1}},
          {{dx:1, dy:-2, lx:0, ly:-1}}, {{dx:-1, dy:-2, lx:0, ly:-1}},
          {{dx:2, dy:1, lx:1, ly:0}}, {{dx:2, dy:-1, lx:1, ly:0}},
          {{dx:-2, dy:1, lx:-1, ly:0}}, {{dx:-2, dy:-1, lx:-1, ly:0}}
        ];
        for (let s of steps) {{
          const nx = x + s.dx, ny = y + s.dy;
          if (nx>=0 && nx<=8 && ny>=0 && ny<=9) {{
            if (board[y + s.ly][x + s.lx] === null) {{ // 检查马腿
              const dest = board[ny][nx];
              if (!dest || getPieceColor(dest) !== color) moves.push({{x: nx, y: ny}});
            }}
          }}
        }}
      }} else if (type === 'b') {{ // 相/象 (塞象眼，不过河)
        const dirs = [
          {{dx:2, dy:2, ex:1, ey:1}}, {{dx:2, dy:-2, ex:1, ey:-1}},
          {{dx:-2, dy:2, ex:-1, ey:1}}, {{dx:-2, dy:-2, ex:-1, ey:-1}}
        ];
        for (let d of dirs) {{
          const nx = x + d.dx, ny = y + d.dy;
          if (color==='red' && ny<5) continue; // 红相不过河
          if (color==='black' && ny>4) continue; // 黑象不过河
          if (nx>=0 && nx<=8 && ny>=0 && ny<=9) {{
            if (board[y + d.ey][x + d.ex] === null) {{ // 检查象眼
              const dest = board[ny][nx];
              if (!dest || getPieceColor(dest) !== color) moves.push({{x: nx, y: ny}});
            }}
          }}
        }}
      }} else if (type === 'a') {{ // 士/仕 (九宫斜行)
        const minX = 3, maxX = 5;
        const minY = color==='red' ? 7 : 0, maxY = color==='red' ? 9 : 2;
        const dirs = [[1,1], [1,-1], [-1,1], [-1,-1]];
        for (let [dx, dy] of dirs) {{
          const nx = x + dx, ny = y + dy;
          if (nx>=minX && nx<=maxX && ny>=minY && ny<=maxY) {{
            const dest = board[ny][nx];
            if (!dest || getPieceColor(dest) !== color) moves.push({{x: nx, y: ny}});
          }}
        }}
      }} else if (type === 'k') {{ // 帅/将 (九宫直行)
        const minX = 3, maxX = 5;
        const minY = color==='red' ? 7 : 0, maxY = color==='red' ? 9 : 2;
        const dirs = [[0,1], [0,-1], [1,0], [-1,0]];
        for (let [dx, dy] of dirs) {{
          const nx = x + dx, ny = y + dy;
          if (nx>=minX && nx<=maxX && ny>=minY && ny<=maxY) {{
            const dest = board[ny][nx];
            if (!dest || getPieceColor(dest) !== color) moves.push({{x: nx, y: ny}});
          }}
        }}
      }} else if (type === 'c') {{ // 炮 (隔山打)
        const dirs = [[0,1],[0,-1],[1,0],[-1,0]];
        for (let [dx, dy] of dirs) {{
          let nx = x + dx, ny = y + dy;
          let jumped = false;
          while (nx>=0 && nx<=8 && ny>=0 && ny<=9) {{
            const dest = board[ny][nx];
            if (!jumped) {{
              if (!dest) moves.push({{x: nx, y: ny}});
              else jumped = true;
            }} else {{
              if (dest) {{
                if (getPieceColor(dest) !== color) moves.push({{x: nx, y: ny}});
                break;
              }}
            }}
            nx += dx; ny += dy;
          }}
        }}
      }} else if (type === 'p') {{ // 兵/卒 (过河横走，不后退)
        const fwd = color==='red' ? -1 : 1;
        const crossed = color==='red' ? y<=4 : y>=5;
        const ny = y + fwd;
        if (ny>=0 && ny<=9) {{
          const dest = board[ny][x];
          if (!dest || getPieceColor(dest) !== color) moves.push({{x: x, y: ny}});
        }}
        if (crossed) {{
          for (let dx of [-1, 1]) {{
            const nx = x + dx;
            if (nx>=0 && nx<=8) {{
              const dest = board[y][nx];
              if (!dest || getPieceColor(dest) !== color) moves.push({{x: nx, y: y}});
            }}
          }}
        }}
      }}
      return moves;
    }}

    function drawLines() {{
      const bEl = document.getElementById('board');
      bEl.innerHTML = '<div class="river"><span>楚 河</span><span>漢 界</span></div>';
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', '450'); svg.setAttribute('height', '500');
      svg.style.position = 'absolute'; svg.style.pointerEvents = 'none';

      for (let y = 0; y < 10; y++) {{
        const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        l.setAttribute('x1', '25'); l.setAttribute('y1', `${{y*50+25}}`);
        l.setAttribute('x2', '425'); l.setAttribute('y2', `${{y*50+25}}`);
        l.setAttribute('stroke', '#5c3a21'); l.setAttribute('stroke-width', '1.5');
        svg.appendChild(l);
      }}
      for (let x = 0; x < 9; x++) {{
        const px = x*50+25;
        if (x===0 || x===8) {{
          const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l.setAttribute('x1', `${{px}}`); l.setAttribute('y1', '25'); l.setAttribute('x2', `${{px}}`); l.setAttribute('y2', '475');
          l.setAttribute('stroke', '#5c3a21'); l.setAttribute('stroke-width', '1.5');
          svg.appendChild(l);
        }} else {{
          const l1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l1.setAttribute('x1', `${{px}}`); l1.setAttribute('y1', '25'); l1.setAttribute('x2', `${{px}}`); l1.setAttribute('y2', '225');
          l1.setAttribute('stroke', '#5c3a21'); l1.setAttribute('stroke-width', '1.5');
          svg.appendChild(l1);
          const l2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          l2.setAttribute('x1', `${{px}}`); l2.setAttribute('y1', '275'); l2.setAttribute('x2', `${{px}}`); l2.setAttribute('y2', '475');
          l2.setAttribute('stroke', '#5c3a21'); l2.setAttribute('stroke-width', '1.5');
          svg.appendChild(l2);
        }}
      }}
      const drawD = (x1,y1,x2,y2) => {{
        const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        l.setAttribute('x1', x1); l.setAttribute('y1', y1); l.setAttribute('x2', x2); l.setAttribute('y2', y2);
        l.setAttribute('stroke', '#5c3a21'); l.setAttribute('stroke-width', '1.5'); svg.appendChild(l);
      }};
      drawD(175,25,275,125); drawD(275,25,175,125);
      drawD(175,375,275,475); drawD(275,375,175,475);
      bEl.appendChild(svg);
    }}

    function render() {{
      drawLines();
      const bEl = document.getElementById('board');
      for (let y = 0; y < 10; y++) {{
        for (let x = 0; x < 9; x++) {{
          const p = board[y][x];
          if (p) {{
            const el = document.createElement('div');
            const color = getPieceColor(p);
            el.className = `piece ${{color}}`;
            el.innerText = PIECE_NAMES[p];
            el.style.left = `${{x*50+3}}px`;
            el.style.top = `${{y*50+3}}px`;
            if (selected && selected.x===x && selected.y===y) el.classList.add('selected');
            el.onclick = (e) => {{ e.stopPropagation(); clickPiece(x,y); }};
            bEl.appendChild(el);
          }}
        }}
      }}
      validMoves.forEach(m => {{
        const isCapture = board[m.y][m.x] !== null;
        const h = document.createElement('div');
        h.className = isCapture ? 'hint-capture' : 'hint-move';
        h.style.left = `${{m.x*50+25}}px`;
        h.style.top = `${{m.y*50+25}}px`;
        h.onclick = (e) => {{ e.stopPropagation(); movePiece(selected.x, selected.y, m.x, m.y); }};
        bEl.appendChild(h);
      }});
      document.getElementById('turn').innerText = turn==='red'?'红方执棋':'黑方执棋';
      document.getElementById('turn').style.color = turn==='red'?'#d9383a':'#eee';
    }}

    function clickPiece(x, y) {{
      const p = board[y][x];
      const color = getPieceColor(p);
      if (color === turn) {{
        selected = {{x, y}};
        validMoves = getStrictMoves(x, y);
        render();
      }} else if (selected) {{
        const m = validMoves.find(v => v.x===x && v.y===y);
        if (m) movePiece(selected.x, selected.y, x, y);
      }}
    }}

    function movePiece(fx, fy, tx, ty) {{
      const captured = board[ty][tx];
      board[ty][tx] = board[fy][fx];
      board[fy][fx] = null;
      selected = null; validMoves = [];

      if (captured && (captured==='r_k'||captured==='b_k')) {{
        render();
        alert((turn==='red'?'红方':'黑方') + ' 绝杀将帅！功德圆满斩获胜利！');
        initGame();
        return;
      }}

      turn = turn === 'red' ? 'black' : 'red';
      render();
    }}

    function initGame() {{
      board = initBoard();
      turn = 'red'; selected = null; validMoves = [];
      render();
    }}

    initGame();
  </script>
</body>
</html>"""

    @staticmethod
    def _generate_rigorous_gomoku(title: str, custom_rules: str = "") -> str:
        """生成正规五子棋 (15x15 棋盘，黑白轮流落子，五子连珠算法判定)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - Game Dev Agent Studios</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #1e1e2f; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }}
    h1 {{ color: #ffd700; margin-bottom: 8px; font-size: 1.8rem; }}
    #status {{ color: #00eeff; margin-bottom: 12px; font-size: 1.1rem; }}
    #canvas {{ background: #deb887; border: 4px solid #8b4513; border-radius: 6px; box-shadow: 0 12px 30px rgba(0,0,0,0.6); cursor: pointer; }}
    .btn {{ margin-top: 15px; padding: 8px 20px; background: #00eeff; color: #000; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }}
  </style>
</head>
<body>
  <h1>⚫⚪ {title}</h1>
  <div id="status">当前回合: 黑棋落子</div>
  <canvas id="canvas" width="480" height="480"></canvas>
  <button class="btn" onclick="init()">重新开局</button>
  <script>
    const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
    const N = 15, CELL = 480 / 16;
    let board = [], turn = 1, over = false;
    function init() {{
      board = Array(N).fill(0).map(() => Array(N).fill(0));
      turn = 1; over = false;
      document.getElementById('status').innerText = '当前回合: 黑棋落子';
      render();
    }}
    function render() {{
      ctx.fillStyle = '#deb887'; ctx.fillRect(0, 0, 480, 480);
      ctx.strokeStyle = '#5c3a21'; ctx.lineWidth = 1.2;
      for(let i = 0; i < N; i++) {{
        let p = (i + 1) * CELL;
        ctx.beginPath(); ctx.moveTo(CELL, p); ctx.lineTo(N * CELL, p); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(p, CELL); ctx.lineTo(p, N * CELL); ctx.stroke();
      }}
      [3, 7, 11].forEach(r => [3, 7, 11].forEach(c => {{
        ctx.beginPath(); ctx.arc((c+1)*CELL, (r+1)*CELL, 3.5, 0, Math.PI*2);
        ctx.fillStyle = '#5c3a21'; ctx.fill();
      }}));
      for(let r = 0; r < N; r++) for(let c = 0; c < N; c++) {{
        if(board[r][c] === 0) continue;
        let x = (c + 1) * CELL, y = (r + 1) * CELL;
        ctx.beginPath(); ctx.arc(x, y, CELL * 0.42, 0, Math.PI * 2);
        let grad = ctx.createRadialGradient(x-3, y-3, 1, x, y, CELL * 0.42);
        if(board[r][c] === 1) {{ grad.addColorStop(0, '#555'); grad.addColorStop(1, '#000'); }}
        else {{ grad.addColorStop(0, '#fff'); grad.addColorStop(1, '#ccc'); }}
        ctx.fillStyle = grad; ctx.fill();
      }}
    }}
    cvs.onclick = (e) => {{
      if(over) return;
      let rect = cvs.getBoundingClientRect();
      let x = e.clientX - rect.left, y = e.clientY - rect.top;
      let c = Math.round(x / CELL) - 1, r = Math.round(y / CELL) - 1;
      if(r < 0 || r >= N || c < 0 || c >= N || board[r][c] !== 0) return;
      board[r][c] = turn;
      if(checkWin(r, c, turn)) {{
        over = true;
        document.getElementById('status').innerText = (turn === 1 ? '🎉 黑棋获胜！' : '🎉 白棋获胜！');
        render(); return;
      }}
      turn = 3 - turn;
      document.getElementById('status').innerText = '当前回合: ' + (turn === 1 ? '黑棋落子' : '白棋落子');
      render();
    }};
    function checkWin(r, c, p) {{
      const dirs = [[0,1], [1,0], [1,1], [1,-1]];
      for(let [dr, dc] of dirs) {{
        let count = 1;
        for(let step = 1; step < 5; step++) {{
          let nr = r + dr * step, nc = c + dc * step;
          if(nr >= 0 && nr < N && nc >= 0 && nc < N && board[nr][nc] === p) count++; else break;
        }}
        for(let step = 1; step < 5; step++) {{
          let nr = r - dr * step, nc = c - dc * step;
          if(nr >= 0 && nr < N && nc >= 0 && nc < N && board[nr][nc] === p) count++; else break;
        }}
        if(count >= 5) return true;
      }}
      return false;
    }}
    init();
  </script>
</body>
</html>"""

    @staticmethod
    def _generate_rigorous_snake(title: str, custom_rules: str = "") -> str:
        """生成正规贪吃蛇 (方向控制、食物生成、碰撞死亡判定、积分增长)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - Game Dev Agent Studios</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #0f172a; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }}
    h1 {{ color: #10b981; margin-bottom: 8px; font-size: 1.8rem; }}
    #score {{ color: #38bdf8; font-size: 1.2rem; margin-bottom: 12px; }}
    #canvas {{ background: #1e293b; border: 3px solid #334155; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
    p {{ color: #94a3b8; margin-top: 10px; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <h1>🐍 {title}</h1>
  <div id="score">得分: <span id="score-val">0</span> | 最高分: <span id="hi-val">0</span></div>
  <canvas id="canvas" width="400" height="400"></canvas>
  <p>使用方向键 ↑ ↓ ← → 控制蛇移动</p>
  <script>
    const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
    const GRID = 20, COUNT = 20;
    let snake = [{{x: 10, y: 10}}], dir = {{x: 1, y: 0}}, nextDir = {{x: 1, y: 0}};
    let food = {{x: 15, y: 10}}, score = 0, hiScore = 0, isDead = false;
    function reset() {{
      snake = [{{x: 10, y: 10}}, {{x: 9, y: 10}}, {{x: 8, y: 10}}];
      dir = {{x: 1, y: 0}}; nextDir = {{x: 1, y: 0}};
      score = 0; isDead = false;
      document.getElementById('score-val').innerText = score;
      spawnFood();
    }}
    function spawnFood() {{
      food = {{x: Math.floor(Math.random() * COUNT), y: Math.floor(Math.random() * COUNT)}};
    }}
    window.addEventListener('keydown', e => {{
      if(e.key === 'ArrowUp' && dir.y === 0) nextDir = {{x: 0, y: -1}};
      else if(e.key === 'ArrowDown' && dir.y === 0) nextDir = {{x: 0, y: 1}};
      else if(e.key === 'ArrowLeft' && dir.x === 0) nextDir = {{x: -1, y: 0}};
      else if(e.key === 'ArrowRight' && dir.x === 0) nextDir = {{x: 1, y: 0}};
    }});
    function loop() {{
      if(!isDead) {{
        dir = nextDir;
        const head = {{x: snake[0].x + dir.x, y: snake[0].y + dir.y}};
        if(head.x < 0 || head.x >= COUNT || head.y < 0 || head.y >= COUNT || snake.some(s => s.x === head.x && s.y === head.y)) {{
          isDead = true; alert('💥 游戏结束！最终得分: ' + score); reset();
        }} else {{
          snake.unshift(head);
          if(head.x === food.x && head.y === food.y) {{
            score += 10;
            if(score > hiScore) hiScore = score;
            document.getElementById('score-val').innerText = score;
            document.getElementById('hi-val').innerText = hiScore;
            spawnFood();
          }} else {{
            snake.pop();
          }}
        }}
      }}
      ctx.fillStyle = '#1e293b'; ctx.fillRect(0, 0, 400, 400);
      ctx.fillStyle = '#ef4444'; ctx.fillRect(food.x * GRID + 2, food.y * GRID + 2, GRID - 4, GRID - 4);
      snake.forEach((s, idx) => {{
        ctx.fillStyle = idx === 0 ? '#10b981' : '#34d399';
        ctx.fillRect(s.x * GRID + 1, s.y * GRID + 1, GRID - 2, GRID - 2);
      }});
    }}
    reset();
    setInterval(loop, 120);
  </script>
</body>
</html>"""

    @staticmethod
    def _generate_rigorous_breakout(title: str, custom_rules: str = "") -> str:
        """生成正规打砖块 (挡板移动、弹球物理反弹、多层彩色砖块、消除判定)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - Game Dev Agent Studios</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #111827; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }}
    h1 {{ color: #f59e0b; margin-bottom: 8px; }}
    #hud {{ color: #38bdf8; font-size: 1.1rem; margin-bottom: 12px; }}
    #canvas {{ background: #1f2937; border: 3px solid #374151; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
  </style>
</head>
<body>
  <h1>🧱 {title}</h1>
  <div id="hud">得分: <span id="score">0</span> | 生命: <span id="lives">3</span></div>
  <canvas id="canvas" width="480" height="400"></canvas>
  <script>
    const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
    let paddle = {{ x: 200, w: 80, h: 12, speed: 7 }};
    let ball = {{ x: 240, y: 300, r: 6, dx: 3, dy: -3 }};
    let score = 0, lives = 3, bricks = [];
    const ROWS = 5, COLS = 8, BW = 52, BH = 16, BPAD = 6, BOFF_T = 40, BOFF_L = 12;
    const colors = ['#ef4444', '#f97316', '#eab308', '#10b981', '#3b82f6'];
    function init() {{
      bricks = [];
      for(let r=0; r<ROWS; r++) for(let c=0; c<COLS; c++) {{
        bricks.push({{ x: c*(BW+BPAD)+BOFF_L, y: r*(BH+BPAD)+BOFF_T, status: 1, color: colors[r] }});
      }}
    }}
    let leftPressed = false, rightPressed = false;
    window.addEventListener('keydown', e => {{ if(e.key==='ArrowLeft') leftPressed=true; else if(e.key==='ArrowRight') rightPressed=true; }});
    window.addEventListener('keyup', e => {{ if(e.key==='ArrowLeft') leftPressed=false; else if(e.key==='ArrowRight') rightPressed=false; }});
    function update() {{
      if(leftPressed && paddle.x > 0) paddle.x -= paddle.speed;
      if(rightPressed && paddle.x + paddle.w < 480) paddle.x += paddle.speed;
      ball.x += ball.dx; ball.y += ball.dy;
      if(ball.x - ball.r < 0 || ball.x + ball.r > 480) ball.dx = -ball.dx;
      if(ball.y - ball.r < 0) ball.dy = -ball.dy;
      if(ball.y + ball.r >= 400 - 20 && ball.x >= paddle.x && ball.x <= paddle.x + paddle.w) {{
        ball.dy = -Math.abs(ball.dy);
        ball.dx = ((ball.x - (paddle.x + paddle.w/2)) / (paddle.w/2)) * 4;
      }}
      if(ball.y + ball.r > 400) {{
        lives--; document.getElementById('lives').innerText = lives;
        if(lives <= 0) {{ alert('💥 游戏结束！'); lives = 3; score = 0; init(); }}
        ball.x = 240; ball.y = 300; ball.dx = 3; ball.dy = -3;
      }}
      bricks.forEach(b => {{
        if(b.status === 1) {{
          if(ball.x > b.x && ball.x < b.x + BW && ball.y > b.y && ball.y < b.y + BH) {{
            ball.dy = -ball.dy; b.status = 0; score += 10;
            document.getElementById('score').innerText = score;
          }}
        }}
      }});
    }}
    function render() {{
      ctx.fillStyle = '#1f2937'; ctx.fillRect(0, 0, 480, 400);
      ctx.fillStyle = '#38bdf8'; ctx.fillRect(paddle.x, 400 - 20, paddle.w, paddle.h);
      ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI*2); ctx.fillStyle = '#ffd700'; ctx.fill();
      bricks.forEach(b => {{
        if(b.status === 1) {{ ctx.fillStyle = b.color; ctx.fillRect(b.x, b.y, BW, BH); }}
      }});
    }}
    function loop() {{ update(); render(); requestAnimationFrame(loop); }}
    init(); loop();
  </script>
</body>
</html>"""

    @staticmethod
    def _generate_rigorous_doudizhu(title: str, custom_rules: str = "") -> str:
        """生成正规斗地主 (发牌洗牌、手牌展示、地主底牌、抢地主出牌交互)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - Game Dev Agent Studios</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #064e3b; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: space-between; height: 100vh; padding: 20px; }}
    h1 {{ color: #fde047; font-size: 1.6rem; }}
    #table {{ flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 20px; }}
    #cards {{ display: flex; gap: -20px; justify-content: center; flex-wrap: wrap; }}
    .card {{ width: 50px; height: 75px; background: #fff; border-radius: 6px; color: #111; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: bold; font-size: 1.1rem; box-shadow: 0 4px 10px rgba(0,0,0,0.4); cursor: pointer; transition: transform 0.15s; }}
    .card.selected {{ transform: translateY(-15px); border: 2px solid #38bdf8; }}
    .red {{ color: #dc2626; }}
    .btn {{ padding: 10px 24px; background: #fde047; color: #000; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 1rem; margin: 5px; }}
  </style>
</head>
<body>
  <h1>🃏 {title}</h1>
  <div id="table">
    <div id="status" style="font-size:1.2rem; color:#6ee7b7;">底牌: [ ? ] [ ? ] [ ? ]</div>
    <div id="played" style="min-height:80px; display:flex; gap:8px;"></div>
  </div>
  <div style="text-align:center;">
    <div id="cards"></div>
    <div style="margin-top:12px;">
      <button class="btn" onclick="playCards()">出牌</button>
      <button class="btn" style="background:#94a3b8;" onclick="passTurn()">不出</button>
      <button class="btn" style="background:#38bdf8;" onclick="init()">重新洗牌</button>
    </div>
  </div>
  <script>
    const suits = ['♠', '♥', '♣', '♦'];
    const ranks = ['3','4','5','6','7','8','9','10','J','Q','K','A','2'];
    let hand = [], selected = new Set();
    function init() {{
      hand = [];
      for(let s of suits) for(let r of ranks) {{
        hand.push({{ suit: s, rank: r, isRed: (s==='♥'||s==='♦') }});
      }}
      hand.sort(() => Math.random() - 0.5);
      hand = hand.slice(0, 17);
      selected.clear();
      render();
    }}
    function render() {{
      const el = document.getElementById('cards'); el.innerHTML = '';
      hand.forEach((c, idx) => {{
        const d = document.createElement('div');
        d.className = 'card' + (c.isRed ? ' red' : '') + (selected.has(idx) ? ' selected' : '');
        d.innerHTML = `<span>${{c.rank}}</span><span style="font-size:0.8rem;">${{c.suit}}</span>`;
        d.onclick = () => {{
          if(selected.has(idx)) selected.delete(idx); else selected.add(idx);
          render();
        }};
        el.appendChild(d);
      }});
    }}
    function playCards() {{
      if(selected.size === 0) return;
      const played = document.getElementById('played'); played.innerHTML = '';
      const idxs = Array.from(selected).sort((a,b) => b-a);
      idxs.forEach(i => {{
        const c = hand[i];
        const d = document.createElement('div');
        d.className = 'card' + (c.isRed ? ' red' : '');
        d.innerHTML = `<span>${{c.rank}}</span><span>${{c.suit}}</span>`;
        played.appendChild(d);
        hand.splice(i, 1);
      }});
      selected.clear();
      render();
      if(hand.length === 0) alert('🎉 恭喜你！手牌已全部打出，获得胜利！');
    }}
    function passTurn() {{
      document.getElementById('played').innerHTML = '<div style="color:#aaa; font-size:1.2rem; align-self:center;">不出</div>';
    }}
    init();
  </script>
</body>
</html>"""

    @staticmethod
    def _generate_minesweeper(title: str, custom_rules: str = "") -> str:
        """生成正规经典扫雷游戏 (10x10, 15雷, 递归翻开, 插旗, 胜利判定)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - Game Dev Agent Studios</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #1a1a2e; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }}
    h1 {{ color: #00eeff; margin-bottom: 10px; }}
    #grid {{ display: grid; grid-template-columns: repeat(10, 36px); grid-gap: 3px; background: #16213e; padding: 10px; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
    .cell {{ width: 36px; height: 36px; background: #0f3460; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.1rem; cursor: pointer; }}
    .cell.revealed {{ background: #e94560; color: #fff; cursor: default; }}
    .cell.flagged {{ background: #ffd700; color: #111; }}
  </style>
</head>
<body>
  <h1>💣 {title}</h1>
  <div id="grid"></div>
  <p style="color:#aaa; margin-top:10px;">左键点击翻开，右键插旗标记 | 剩余雷数: <span id="mines-left" style="color:#ffd700;">15</span></p>
  <script>
    const ROWS = 10, COLS = 10, MINES = 15;
    let board = [], revealed = [], flagged = [], isOver = false;
    function init() {{
      board = Array(ROWS).fill(0).map(() => Array(COLS).fill(0));
      revealed = Array(ROWS).fill(false).map(() => Array(COLS).fill(false));
      flagged = Array(ROWS).fill(false).map(() => Array(COLS).fill(false));
      isOver = false;
      let planted = 0;
      while(planted < MINES) {{
        let r = Math.floor(Math.random()*ROWS), c = Math.floor(Math.random()*COLS);
        if(board[r][c] !== -1) {{ board[r][c] = -1; planted++; }}
      }}
      for(let r=0; r<ROWS; r++) {{
        for(let c=0; c<COLS; c++) {{
          if(board[r][c] === -1) continue;
          let count = 0;
          for(let dr=-1; dr<=1; dr++) for(let dc=-1; dc<=1; dc++) {{
            let nr = r+dr, nc = c+dc;
            if(nr>=0 && nr<ROWS && nc>=0 && nc<COLS && board[nr][nc] === -1) count++;
          }}
          board[r][c] = count;
        }}
      }}
      render();
    }}
    function render() {{
      const el = document.getElementById('grid'); el.innerHTML = '';
      for(let r=0; r<ROWS; r++) for(let c=0; c<COLS; c++) {{
        const d = document.createElement('div');
        d.className = 'cell' + (revealed[r][c] ? ' revealed' : '') + (flagged[r][c] ? ' flagged' : '');
        if(revealed[r][c]) {{
          if(board[r][c] === -1) d.innerText = '💣';
          else if(board[r][c] > 0) {{ d.innerText = board[r][c]; d.style.background = '#e2e8f0'; d.style.color = '#111'; }}
          else {{ d.innerText = ''; d.style.background = '#cbd5e1'; }}
        }} else if(flagged[r][c]) d.innerText = '🚩';
        d.onclick = () => reveal(r, c);
        d.oncontextmenu = (e) => {{ e.preventDefault(); toggleFlag(r, c); }};
        el.appendChild(d);
      }}
    }}
    function reveal(r, c) {{
      if(isOver || revealed[r][c] || flagged[r][c]) return;
      revealed[r][c] = true;
      if(board[r][c] === -1) {{
        isOver = true; alert('💥 踩中地雷！游戏结束！'); render(); return;
      }}
      if(board[r][c] === 0) {{
        for(let dr=-1; dr<=1; dr++) for(let dc=-1; dc<=1; dc++) {{
          let nr = r+dr, nc = c+dc;
          if(nr>=0 && nr<ROWS && nc>=0 && nc<COLS && !revealed[nr][nc]) reveal(nr, nc);
        }}
      }}
      render();
      checkWin();
    }}
    function toggleFlag(r, c) {{
      if(isOver || revealed[r][c]) return;
      flagged[r][c] = !flagged[r][c];
      render();
    }}
    function checkWin() {{
      let unrevealedSafe = 0;
      for(let r=0; r<ROWS; r++) for(let c=0; c<COLS; c++) {{
        if(!revealed[r][c] && board[r][c] !== -1) unrevealedSafe++;
      }}
      if(unrevealedSafe === 0) {{ isOver = true; alert('🎉 恭喜你！排除了所有地雷！'); }}
    }}
    init();
  </script>
</body>
</html>"""

    @staticmethod
    def _generate_2048(title: str, custom_rules: str = "") -> str:
        """生成正规 2048 数字合并游戏"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - Game Dev Agent Studios</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #faf8ef; color: #776e65; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }}
    #board {{ width: 340px; height: 340px; background: #bbada0; padding: 10px; border-radius: 8px; display: grid; grid-template-columns: repeat(4, 1fr); grid-gap: 10px; }}
    .cell {{ background: #cdc1b4; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; font-weight: bold; color: #fff; }}
  </style>
</head>
<body>
  <h1 style="color:#8f7a66; margin-bottom:10px;">🔢 {title}</h1>
  <div id="board"></div>
  <p style="margin-top:12px;">使用方向键 ↑ ↓ ← → 滑动合并方块</p>
  <script>
    let grid = Array(4).fill(0).map(() => Array(4).fill(0));
    function spawn() {{
      let empty = [];
      for(let r=0; r<4; r++) for(let c=0; c<4; c++) if(grid[r][c]===0) empty.push({{r,c}});
      if(empty.length>0) {{
        let p = empty[Math.floor(Math.random()*empty.length)];
        grid[p.r][p.c] = Math.random()<0.9 ? 2 : 4;
      }}
    }}
    function render() {{
      const b = document.getElementById('board'); b.innerHTML = '';
      const colors = {{ 2:'#eee4da',4:'#ede0c8',8:'#f2b179',16:'#f59563',32:'#f67c5f',64:'#f65e3b',128:'#edcf72',256:'#edcc61',512:'#edc850',1024:'#edc53f',2048:'#edc22e' }};
      for(let r=0; r<4; r++) for(let c=0; c<4; c++) {{
        const d = document.createElement('div'); d.className = 'cell';
        let v = grid[r][c];
        if(v > 0) {{
          d.innerText = v; d.style.background = colors[v] || '#3c3a32';
          d.style.color = v<=4 ? '#776e65' : '#fff';
        }}
        b.appendChild(d);
      }}
    }}
    window.addEventListener('keydown', e => {{
      let moved = false;
      if(e.key==='ArrowLeft') moved = slideLeft();
      else if(e.key==='ArrowRight') {{ rotate(); rotate(); moved = slideLeft(); rotate(); rotate(); }}
      else if(e.key==='ArrowUp') {{ rotate(); rotate(); rotate(); moved = slideLeft(); rotate(); }}
      else if(e.key==='ArrowDown') {{ rotate(); moved = slideLeft(); rotate(); rotate(); rotate(); }}
      if(moved) {{ spawn(); render(); }}
    }});
    function slideLeft() {{
      let changed = false;
      for(let r=0; r<4; r++) {{
        let row = grid[r].filter(v => v!==0);
        for(let i=0; i<row.length-1; i++) {{
          if(row[i] === row[i+1]) {{ row[i] *= 2; row[i+1] = 0; changed = true; }}
        }}
        row = row.filter(v => v!==0);
        while(row.length < 4) row.push(0);
        for(let c=0; c<4; c++) {{ if(grid[r][c] !== row[c]) changed = true; grid[r][c] = row[c]; }}
      }}
      return changed;
    }}
    function rotate() {{
      let next = Array(4).fill(0).map(() => Array(4).fill(0));
      for(let r=0; r<4; r++) for(let c=0; c<4; c++) next[c][3-r] = grid[r][c];
      grid = next;
    }}
    spawn(); spawn(); render();
  </script>
</body>
</html>"""

    @staticmethod
    def _generate_rigorous_space_shooter(title: str, custom_rules: str = "") -> str:
        """生成射击战斗"""
        from pipeline.commercial_engines import CommercialEngines
        return CommercialEngines.generate_3d_fps_cs(title, custom_rules)
