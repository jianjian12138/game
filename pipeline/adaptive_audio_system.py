#!/usr/bin/env python3
"""
pipeline/adaptive_audio_system.py: 交互式自适应多轨动态音频引擎 (Adaptive Dynamic Audio Engine)
解决游戏在听觉心流与动态混音维度的缺陷：
1. VerticalLayerMixer: 四层垂直分层 BGM 状态机 (Atmosphere, Rhythm, Combat, Climax)，根据威胁等级平滑交叉淡入淡出。
2. InteractiveDSPFilters: 实时低通滤波 (LPF) 频点调制 (血量 < 30% 呈现濒死低沉混音) 与 3D 空间音频定位 (HRTF Panner)。
3. ProceduralMelodySynthesizer: 纯算法程序化和弦与调式音阶生成，输出 100% 免外部音频文件的纯 WebAudio 驱动脚本。
4. GodotBusLayoutExporter: 自动生成 Godot 4 `default_bus_layout.tres` 工业标准音频总线架构。
"""

import os
import sys
import math
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# 调式与和弦算法 (纯数学实现)
# -----------------------------------------------------------------------------
SCALES = {
    "pentatonic": [0, 2, 4, 7, 9],           # 五声音阶 (东方/恬静)
    "dorian": [0, 2, 3, 5, 7, 9, 10],         # 多利亚调式 (科幻/探险)
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11], # 和声小调 (史诗/战斗)
    "cyberpunk": [0, 1, 4, 5, 7, 8, 10]       # 弗里吉亚主调 (赛博朋克/危机)
}

def midi_to_freq(midi_note: int) -> float:
    """MIDI 音高转赫兹 (A4 = 69 = 440.0Hz)"""
    return round(440.0 * (2.0 ** ((midi_note - 69) / 12.0)), 2)

# -----------------------------------------------------------------------------
# 垂直多层自适应状态机
# -----------------------------------------------------------------------------
@dataclass
class AudioLayer:
    layer_id: str
    name: str
    description: str
    base_notes: List[int]
    instrument: str  # "pad", "bass", "lead", "alarm"
    threshold_threat: float  # 激活该层的威胁度阈值 (0.0 ~ 1.0)
    target_volume: float = 0.0

class VerticalLayerMixer:
    """垂直分层动态音频状态机管理器"""
    @staticmethod
    def get_preset_layers(theme: str = "cyberpunk") -> List[AudioLayer]:
        scale = SCALES.get(theme, SCALES["dorian"])
        root = 48 # C3
        return [
            AudioLayer(
                layer_id="layer_atmosphere",
                name="Atmosphere (环境底噪)",
                description="低频环境和弦垫音，常态全量播放",
                base_notes=[root, root+scale[2], root+scale[4]],
                instrument="sine_pad",
                threshold_threat=0.0,
                target_volume=1.0
            ),
            AudioLayer(
                layer_id="layer_rhythm",
                name="Tension Rhythm (行进节拍)",
                description="中频脉冲低音与踩镲节奏，在发现敌人或进入警戒区时浮现",
                base_notes=[root-12, root-12+scale[1], root-12+scale[3]],
                instrument="square_bass",
                threshold_threat=0.25,
                target_volume=0.0
            ),
            AudioLayer(
                layer_id="layer_combat",
                name="Combat Lead (激战交响)",
                description="快速琶音与高频电音主音，在激烈正面交火时主导听觉",
                base_notes=[root+12+scale[0], root+12+scale[2], root+12+scale[4], root+12+scale[6]],
                instrument="sawtooth_lead",
                threshold_threat=0.60,
                target_volume=0.0
            ),
            AudioLayer(
                layer_id="layer_climax",
                name="Climax Alert (濒危高潮)",
                description="紧张刺耳的短音脉冲与心跳重音，在 Boss 战或残血时爆发",
                base_notes=[root+24+scale[0], root+24+scale[1]],
                instrument="triangle_alarm",
                threshold_threat=0.85,
                target_volume=0.0
            ),
        ]

    @staticmethod
    def compute_layer_volumes(threat_level: float) -> Dict[str, float]:
        """根据当前威胁等级 (0.0 ~ 1.0) 计算四轨各自音量权重"""
        clamped = max(0.0, min(1.0, threat_level))
        vols = {}
        # Atmosphere: 常驻，但在极度激战时微降以给主旋律让频
        vols["layer_atmosphere"] = round(max(0.3, 1.0 - clamped * 0.5), 2)
        # Rhythm: 0.2 ~ 0.5 线性爬坡
        if clamped < 0.2: vols["layer_rhythm"] = 0.0
        elif clamped < 0.5: vols["layer_rhythm"] = round((clamped - 0.2) / 0.3, 2)
        else: vols["layer_rhythm"] = 1.0
        # Combat: 0.5 ~ 0.8 线性爬坡
        if clamped < 0.5: vols["layer_combat"] = 0.0
        elif clamped < 0.8: vols["layer_combat"] = round((clamped - 0.5) / 0.3, 2)
        else: vols["layer_combat"] = 1.0
        # Climax: 0.8 ~ 1.0 激增
        if clamped < 0.8: vols["layer_climax"] = 0.0
        else: vols["layer_climax"] = round((clamped - 0.8) / 0.2, 2)
        return vols

# -----------------------------------------------------------------------------
# WebAudio 纯前端自适应合成驱动生成器 (零音频文件依赖)
# -----------------------------------------------------------------------------
class WebAudioCodeGenerator:
    @staticmethod
    def generate_engine_script(theme: str = "cyberpunk") -> str:
        """生成开箱即用的前端 WebAudio 驱动脚本 (带 LPF 低通滤波、3D 空间音频和 4 轨动态交叉混音)"""
        layers = VerticalLayerMixer.get_preset_layers(theme)
        layers_meta_json = json.dumps([
            {
                "id": l.layer_id,
                "instrument": l.instrument,
                "frequencies": [midi_to_freq(n) for n in l.base_notes],
                "threshold": l.threshold_threat
            }
            for l in layers
        ], indent=2)

        return f"""// ============================================================================
// AdaptiveDynamicAudioEngine v7.0 - 纯前端免外部素材自适应音频引擎
// 支持: 4层垂直淡入淡出 BGM、濒死 LPF 低通滤波、3D HRTF 空间音频声场
// ============================================================================
(function(window) {{
  class AdaptiveAudioEngine {{
    constructor() {{
      this.ctx = null;
      this.masterGain = null;
      this.lowPassFilter = null;
      this.layers = [];
      this.layerNodes = {{}};
      this.currentThreat = 0.0;
      this.currentHP = 1.0; // 0.0 ~ 1.0
      this.isStarted = false;
      this.layersConfig = {layers_meta_json};
    }}

    init() {{
      if (this.ctx) return;
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContext();

      // 1. 主输出链与 DSP 滤波器
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 0.85;

      this.lowPassFilter = this.ctx.createBiquadFilter();
      this.lowPassFilter.type = 'lowpass';
      this.lowPassFilter.frequency.value = 20000; // 默认全通
      this.lowPassFilter.Q.value = 1.0;

      // 拓扑: Layers -> LowPassFilter -> MasterGain -> Destination
      this.lowPassFilter.connect(this.masterGain);
      this.masterGain.connect(this.ctx.destination);

      // 2. 初始化 4 层音轨振荡器组与独立 GainNode
      this.layersConfig.forEach(cfg => {{
        const gNode = this.ctx.createGain();
        gNode.gain.value = cfg.threshold === 0.0 ? 0.8 : 0.0;
        gNode.connect(this.lowPassFilter);
        this.layerNodes[cfg.id] = {{ gainNode: gNode, oscillators: [], config: cfg }};
      }});

      console.log('🎵 [AdaptiveAudio] 交互式自适应音频拓扑已就绪 (免素材程序化合成)');
    }}

    startMusic() {{
      if (!this.ctx) this.init();
      if (this.ctx.state === 'suspended') this.ctx.resume();
      if (this.isStarted) return;
      this.isStarted = true;

      // 启动各层合成回路
      Object.keys(this.layerNodes).forEach(layerId => {{
        const item = this.layerNodes[layerId];
        item.config.frequencies.forEach((freq, idx) => {{
          const osc = this.ctx.createOscillator();
          osc.type = item.config.instrument.includes('sawtooth') ? 'sawtooth' :
                     item.config.instrument.includes('square') ? 'square' :
                     item.config.instrument.includes('triangle') ? 'triangle' : 'sine';
          osc.frequency.value = freq;
          // 微量失谐 (Detune) 增加空间丰满度
          osc.detune.value = (idx - 1) * 7.5;
          osc.connect(item.gainNode);
          osc.start();
          item.oscillators.push(osc);
        }});
      }});
      console.log('▶️ [AdaptiveAudio] 自适应背景心流旋律启程');
    }}

    // 设置游戏威胁度 (0.0 ~ 1.0) 触发平滑多轨交叉淡入淡出
    setThreatLevel(threat) {{
      if (!this.ctx) return;
      this.currentThreat = Math.max(0.0, Math.min(1.0, threat));
      const now = this.ctx.currentTime;
      const smoothTime = 1.5; // 1.5秒线性过渡

      // 计算各轨理论音量
      let atmVol = Math.max(0.3, 1.0 - this.currentThreat * 0.5);
      let rhythmVol = this.currentThreat < 0.2 ? 0.0 : (this.currentThreat - 0.2) / 0.3;
      let combatVol = this.currentThreat < 0.5 ? 0.0 : (this.currentThreat - 0.5) / 0.3;
      let climaxVol = this.currentThreat < 0.8 ? 0.0 : (this.currentThreat - 0.8) / 0.2;

      this._fadeGain('layer_atmosphere', Math.min(1.0, atmVol), now, smoothTime);
      this._fadeGain('layer_rhythm', Math.min(1.0, Math.max(0, rhythmVol)), now, smoothTime);
      this._fadeGain('layer_combat', Math.min(1.0, Math.max(0, combatVol)), now, smoothTime);
      this._fadeGain('layer_climax', Math.min(1.0, Math.max(0, climaxVol)), now, smoothTime);
    }}

    _fadeGain(layerId, target, now, dur) {{
      if (this.layerNodes[layerId]) {{
        const g = this.layerNodes[layerId].gainNode.gain;
        g.cancelScheduledValues(now);
        g.linearRampToValueAtTime(Math.max(0.0001, target), now + dur);
      }}
    }}

    // 监测角色血量: 当 HP < 30% 时开启低沉低通滤波，模拟濒死心跳听觉
    setHealthRatio(hpRatio) {{
      if (!this.lowPassFilter || !this.ctx) return;
      this.currentHP = Math.max(0.0, Math.min(1.0, hpRatio));
      const now = this.ctx.currentTime;
      let targetFreq = 20000;
      if (this.currentHP < 0.3) {{
        // 从 350Hz 到 1800Hz 渐变
        targetFreq = 350 + (this.currentHP / 0.3) * 1500;
      }}
      this.lowPassFilter.frequency.cancelScheduledValues(now);
      this.lowPassFilter.frequency.exponentialRampToValueAtTime(Math.max(100, targetFreq), now + 0.4);
    }}

    // 触发具备 HRTF 空间三维方位的 3D 爆炸/射击音效
    playSpatialSFX(type, x, y, z) {{
      if (!this.ctx) return;
      const now = this.ctx.currentTime;
      const panner = this.ctx.createPanner();
      panner.panningModel = 'HRTF';
      panner.distanceModel = 'inverse';
      panner.positionX.value = x || 0;
      panner.positionY.value = y || 0;
      panner.positionZ.value = z || -1;

      const osc = this.ctx.createOscillator();
      const sfxGain = this.ctx.createGain();

      if (type === 'explosion') {{
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(140, now);
        osc.frequency.exponentialRampToValueAtTime(25, now + 0.4);
        sfxGain.gain.setValueAtTime(0.9, now);
        sfxGain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
      }} else if (type === 'laser') {{
        osc.type = 'square';
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(110, now + 0.15);
        sfxGain.gain.setValueAtTime(0.6, now);
        sfxGain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      }} else {{
        osc.type = 'sine';
        osc.frequency.setValueAtTime(520, now);
        sfxGain.gain.setValueAtTime(0.5, now);
        sfxGain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
      }}

      osc.connect(sfxGain);
      sfxGain.connect(panner);
      panner.connect(this.masterGain);
      osc.start(now);
      osc.stop(now + 0.5);
    }}
  }}

  window.AdaptiveAudio = new AdaptiveAudioEngine();
}})(window);
"""

# -----------------------------------------------------------------------------
# Godot 4 工业音频总线导出器
# -----------------------------------------------------------------------------
class GodotBusLayoutExporter:
    @staticmethod
    def export(output_file: Path) -> str:
        """输出符合 Godot 4 标准的 default_bus_layout.tres"""
        content = """[gd_resource type="AudioBusLayout" load_steps=3 format=3]

[sub_resource type="AudioEffectLowPassFilter" id="AudioEffectLowPassFilter_hp"]
resource_name = "AdrenalineLowPass"
cutoff_hz = 20500.0
resonance = 0.5

[sub_resource type="AudioEffectLimiter" id="AudioEffectLimiter_safe"]
resource_name = "MasterLimiter"
ceiling_db = -0.1
threshold_db = -2.0

[resource]
bus/0/name = &"Master"
bus/0/solo = false
bus/0/mute = false
bus/0/bypass_fx = false
bus/0/volume_db = 0.0
bus/0/effect/0/effect = SubResource("AudioEffectLimiter_safe")
bus/0/effect/0/enabled = true

bus/1/name = &"Music"
bus/1/solo = false
bus/1/mute = false
bus/1/bypass_fx = false
bus/1/volume_db = -3.0
bus/1/send = &"Master"
bus/1/effect/0/effect = SubResource("AudioEffectLowPassFilter_hp")
bus/1/effect/0/enabled = true

bus/2/name = &"SFX"
bus/2/solo = false
bus/2/mute = false
bus/2/bypass_fx = false
bus/2/volume_db = 0.0
bus/2/send = &"Master"
"""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")
        return str(output_file)

# -----------------------------------------------------------------------------
# 顶层门面类
# -----------------------------------------------------------------------------
class AdaptiveAudioSystem:
    @staticmethod
    def generate_audio_suite(output_dir: Optional[str] = None, theme: str = "cyberpunk") -> Dict[str, Any]:
        """一键生成交互式自适应音频套件 (前端 WebAudio 驱动 + Godot 4 音频总线配置文件)"""
        out_root = Path(output_dir) if output_dir else ROOT / "output" / "dist" / "audio_suite"
        out_root.mkdir(parents=True, exist_ok=True)

        js_file = out_root / "adaptive_audio_engine.js"
        js_code = WebAudioCodeGenerator.generate_engine_script(theme)
        js_file.write_text(js_code, encoding="utf-8")

        godot_bus_file = out_root / "default_bus_layout.tres"
        GodotBusLayoutExporter.export(godot_bus_file)

        layers = VerticalLayerMixer.get_preset_layers(theme)
        threat_samples = {
            "threat_0.1": VerticalLayerMixer.compute_layer_volumes(0.1),
            "threat_0.4": VerticalLayerMixer.compute_layer_volumes(0.4),
            "threat_0.7": VerticalLayerMixer.compute_layer_volumes(0.7),
            "threat_0.95": VerticalLayerMixer.compute_layer_volumes(0.95)
        }

        return {
            "status": "SUCCESS",
            "theme": theme,
            "layers_count": len(layers),
            "layers": [l.name for l in layers],
            "webaudio_js": str(js_file),
            "godot_bus_tres": str(godot_bus_file),
            "threat_volume_curve": threat_samples
        }

if __name__ == "__main__":
    res = AdaptiveAudioSystem.generate_audio_suite()
    print("=== AdaptiveAudioSystem: 自适应多轨音频套件构建完毕 ===")
    print("  主题:", res["theme"])
    print("  分轨数:", res["layers_count"])
    print("  WebAudio 脚本:", res["webaudio_js"])
    print("  Godot 音频总线:", res["godot_bus_tres"])
    print("  动态混音采样:", res["threat_volume_curve"])
