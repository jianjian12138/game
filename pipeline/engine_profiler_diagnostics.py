# =================================================================
# 📊 Game-Agent: 工业级全景运行时性能分析器 (engine_profiler_diagnostics.py)
# 对应 ThisisGame/cpp-game-engine-book 第 16 章 & 极客时间性能工程
# 实时监测 FPS、帧耗时(ms)、DrawCalls、合批率(%)、视锥裁剪实体数与内存
# =================================================================

from typing import Dict, Any

class EngineProfiler:
    """Python 端性能指标契约与校验器"""
    def __init__(self):
        self.fps_budget_ms = 16.67 # 60fps
        self.draw_call_budget = 25
        self.batch_ratio_threshold = 80.0

    def evaluate_frame_metrics(self, fps: float, frame_time_ms: float, draw_calls: int, batch_ratio: float) -> Dict[str, Any]:
        fps_pass = fps >= 55.0
        time_pass = frame_time_ms <= self.fps_budget_ms
        dc_pass = draw_calls <= self.draw_call_budget
        batch_pass = batch_ratio >= self.batch_ratio_threshold

        all_pass = fps_pass and time_pass and dc_pass and batch_pass
        return {
            "all_pass": all_pass,
            "fps_pass": fps_pass,
            "time_pass": time_pass,
            "dc_pass": dc_pass,
            "batch_pass": batch_pass,
            "summary": "PERFECT_60FPS_BATCHED" if all_pass else "PERFORMANCE_BUDGET_EXCEEDED"
        }

def generate_profiler_hud_js() -> str:
    """生成工业级全景实时分析器与 HUD 运行时 JavaScript"""
    return """
// =================================================================
// 📊 工业级引擎全景分析器与 HUD 仪表盘 (Engine Profiler & Diagnostics)
// 遵循 ThisisGame/cpp-game-engine-book 第 16 章 & 极客时间系统工程标准
// =================================================================

class EngineProfilerHUD {
    constructor() {
        this.visible = true;
        this.frameCount = 0;
        this.fps = 60;
        this.lastFpsUpdate = performance.now();
        this.framesThisSecond = 0;

        this.frameStart = 0;
        this.updateTime = 0;
        this.cullingTime = 0;
        this.renderTime = 0;
        this.totalFrameTime = 0;

        this.totalEntities = 0;
        this.culledCount = 0;
        this.drawCalls = 0;
        this.batchRatio = 0;

        this.container = null;
        this.initDOM();
        this.bindEvents();
    }

    initDOM() {
        if (typeof document === 'undefined') return;
        const div = document.createElement('div');
        div.id = 'engine-profiler-hud';
        div.style.position = 'fixed';
        div.style.top = '12px';
        div.style.left = '12px';
        div.style.padding = '10px 14px';
        div.style.background = 'rgba(10, 15, 26, 0.85)';
        div.style.backdropFilter = 'blur(10px)';
        div.style.border = '1px solid rgba(0, 240, 255, 0.3)';
        div.style.borderRadius = '8px';
        div.style.fontFamily = "'JetBrains Mono', Consolas, monospace";
        div.style.fontSize = '11px';
        div.style.color = '#e0e6ed';
        div.style.zIndex = '99999';
        div.style.boxShadow = '0 8px 32px rgba(0,0,0,0.6)';
        div.style.pointerEvents = 'none';
        div.style.lineHeight = '1.5';
        div.innerHTML = `
            <div style="font-weight: bold; color: #00f0ff; margin-bottom: 4px; display: flex; justify-content: space-between;">
                <span>⚙️ ENGINE PROFILER</span>
                <span style="color: #64748b; font-size: 10px;">[P] Toggle</span>
            </div>
            <div style="display: grid; grid-template-columns: 80px 1fr; gap: 2px;">
                <span style="color: #94a3b8;">FPS:</span><span id="prof-fps" style="color: #10b981; font-weight: bold;">60</span>
                <span style="color: #94a3b8;">FrameTime:</span><span id="prof-ft">0.0 ms</span>
                <span style="color: #94a3b8;">DrawCalls:</span><span id="prof-dc" style="color: #38bdf8;">0</span>
                <span style="color: #94a3b8;">Batched:</span><span id="prof-br" style="color: #a855f7; font-weight: bold;">0%</span>
                <span style="color: #94a3b8;">Entities:</span><span id="prof-ent">0</span>
                <span style="color: #94a3b8;">Culled:</span><span id="prof-cul" style="color: #f59e0b;">0</span>
            </div>
        `;
        document.body.appendChild(div);
        this.container = div;
    }

    bindEvents() {
        if (typeof window === 'undefined') return;
        window.addEventListener('keydown', (e) => {
            if (e.key === 'p' || e.key === 'P') {
                this.visible = !this.visible;
                if (this.container) this.container.style.display = this.visible ? 'block' : 'none';
            }
        });
    }

    beginFrame() {
        this.frameStart = performance.now();
        this.framesThisSecond++;
        if (this.frameStart - this.lastFpsUpdate >= 1000) {
            this.fps = this.framesThisSecond;
            this.framesThisSecond = 0;
            this.lastFpsUpdate = this.frameStart;
        }
    }

    recordUpdate(ms) { this.updateTime = ms; }
    recordCulling(ms, culledCount) { this.cullingTime = ms; this.culledCount = culledCount; }
    recordRender(ms, drawCalls, batchRatio) {
        this.renderTime = ms;
        this.drawCalls = drawCalls;
        this.batchRatio = batchRatio;
    }

    endFrame(totalEntities) {
        const now = performance.now();
        this.totalFrameTime = now - this.frameStart;
        this.totalEntities = totalEntities;
        this.frameCount++;

        if (this.visible && this.frameCount % 5 === 0 && this.container) {
            const elFps = document.getElementById('prof-fps');
            const elFt = document.getElementById('prof-ft');
            const elDc = document.getElementById('prof-dc');
            const elBr = document.getElementById('prof-br');
            const elEnt = document.getElementById('prof-ent');
            const elCul = document.getElementById('prof-cul');

            if (elFps) {
                elFps.innerText = `${this.fps}`;
                elFps.style.color = this.fps >= 55 ? '#10b981' : (this.fps >= 30 ? '#f59e0b' : '#ef4444');
            }
            if (elFt) elFt.innerText = `${this.totalFrameTime.toFixed(2)} ms`;
            if (elDc) elDc.innerText = `${this.drawCalls}`;
            if (elBr) elBr.innerText = `${this.batchRatio}%`;
            if (elEnt) elEnt.innerText = `${this.totalEntities}`;
            if (elCul) elCul.innerText = `${this.culledCount}`;
        }
    }
}
"""
