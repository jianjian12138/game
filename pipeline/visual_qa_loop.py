#!/usr/bin/env python3
"""
visual_qa_loop.py: 自动化 Visual QA 视觉审计与自愈循环
对生成的游戏代码进行语法健全性、Canvas 渲染流水线、Web Audio 音频上下文与 60fps 循环闭环自愈审计与真实修复。
"""
import re
from typing import Dict, List, Any

class VisualQALoop:
    """自动化 Visual QA 视觉审美与结构化语法完整性门禁"""

    @staticmethod
    def audit_and_heal(html_code: str) -> Dict[str, Any]:
        issues = []
        applied_fixes = []
        healed_code = html_code

        # 0. 结构完整性检查 (DOCTYPE, html, body, viewport)
        has_viewport = "viewport-fit=cover" in healed_code or "viewport" in healed_code
        if not has_viewport:
            issues.append({"type": "VIEWPORT_META_MISSING", "severity": "MEDIUM", "msg": "缺少移动端全屏安全区 viewport 声明"})
            if "<head>" in healed_code:
                vp_patch = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">\n'
                healed_code = healed_code.replace("<head>", f"<head>\n{vp_patch}", 1)
                applied_fixes.append("VIEWPORT_META_INJECTED")

        # 检查闭合标签结构完整度
        open_tags = len(re.findall(r'<div\b[^>]*>', healed_code))
        close_tags = len(re.findall(r'</div>', healed_code))
        if open_tags > close_tags and "</body>" in healed_code:
            missing_divs = "</div>" * (open_tags - close_tags)
            healed_code = healed_code.replace("</body>", f"{missing_divs}</body>", 1)
            applied_fixes.append("UNCLOSED_DIV_TAGS_REPAIRED")

        # 1. 检查 Canvas 渲染上下文
        has_context = "getContext('2d')" in healed_code or 'getContext("2d")' in healed_code or "WebGLRenderingContext" in healed_code or "webgl" in healed_code.lower()
        if not has_context:
            issues.append({"type": "RENDER_CONTEXT_MISSING", "severity": "CRITICAL", "msg": "缺少 2D/WebGL 渲染上下文"})
            if "</body>" in healed_code:
                canvas_patch = '<canvas id="gameCanvas" width="800" height="600" style="display:block;margin:0 auto;background:#05070e;"></canvas>\n'
                healed_code = healed_code.replace("</body>", f"{canvas_patch}</body>", 1)
            if "</script>" in healed_code:
                ctx_patch = "\nconst canvas = document.getElementById('gameCanvas') || document.createElement('canvas');\nconst ctx = canvas.getContext('2d');\n"
                healed_code = healed_code.replace("</script>", f"{ctx_patch}</script>", 1)
            applied_fixes.append("RENDER_CONTEXT_INJECTED")

        # 2. 检查 requestAnimationFrame 核心循环
        if "requestAnimationFrame" not in healed_code:
            issues.append({"type": "GAME_LOOP_MISSING", "severity": "HIGH", "msg": "缺少 requestAnimationFrame 60fps 主循环"})
            if "</script>" in healed_code:
                loop_patch = """
function _healedMainLoop(timestamp) {
    if (typeof update === 'function') update();
    if (typeof render === 'function') render();
    requestAnimationFrame(_healedMainLoop);
}
requestAnimationFrame(_healedMainLoop);
"""
                healed_code = healed_code.replace("</script>", f"{loop_patch}</script>", 1)
            applied_fixes.append("MAIN_LOOP_INJECTED")

        # 3. 检查 Web Audio API 用户手势解锁
        if "AudioContext" in healed_code and "addEventListener" not in healed_code:
            issues.append({"type": "AUDIO_AUTOPLAY_BLOCKED", "severity": "MEDIUM", "msg": "音频上下文未绑定用户交互事件，可能被浏览器策略静音"})
            if "</script>" in healed_code:
                audio_patch = """
window.addEventListener('pointerdown', () => {
    if (typeof audioCtx !== 'undefined' && audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}, { once: true });
"""
                healed_code = healed_code.replace("</script>", f"{audio_patch}</script>", 1)
            applied_fixes.append("AUDIO_UNLOCK_INJECTED")

        # 4. 检查键盘/触控输入事件监听
        if "keydown" not in healed_code and "pointerdown" not in healed_code and "touchstart" not in healed_code:
            issues.append({"type": "INPUT_LISTENER_MISSING", "severity": "CRITICAL", "msg": "未捕获玩家键盘、触控或鼠标输入事件"})
            if "</script>" in healed_code:
                input_patch = """
window._inputKeys = {};
window.addEventListener('keydown', e => { window._inputKeys[e.code] = true; });
window.addEventListener('keyup', e => { window._inputKeys[e.code] = false; });
"""
                healed_code = healed_code.replace("</script>", f"{input_patch}</script>", 1)
            applied_fixes.append("INPUT_LISTENER_INJECTED")

        # 5. 校验内联 JavaScript 语法完整性（括号平衡与字符串不逃逸）
        script_contents = re.findall(r'<script\b[^>]*>(.*?)</script>', healed_code, re.DOTALL)
        script_syntax_valid = True
        for sc in script_contents:
            curly_bal = sc.count('{') - sc.count('}')
            paren_bal = sc.count('(') - sc.count(')')
            if abs(curly_bal) > 2 or abs(paren_bal) > 2:
                script_syntax_valid = False
                issues.append({"type": "SCRIPT_SYNTAX_IMBALANCE", "severity": "HIGH", "msg": f"Script 标签代码括号失衡 ({{}}: {curly_bal}, (): {paren_bal})"})

        if len(issues) == 0:
            verdict = "PASSED"
            quality_tier = "STATIC_SYNTAX_PASS"
        elif len(applied_fixes) >= len(issues) or (len(issues) - len(applied_fixes) == 0 and script_syntax_valid):
            verdict = "HEALED"
            quality_tier = "HEALED_SYNTAX_PASS"
        else:
            verdict = "FAILED"
            quality_tier = "FAILED_SYNTAX"

        return {
            "status": "success",
            "verdict": verdict,
            "quality_tier": quality_tier,
            "syntax_valid": script_syntax_valid,
            "issues_count": len(issues),
            "issues": issues,
            "applied_fixes": applied_fixes,
            "fps_target": 60,
            "healed_code": healed_code
        }
