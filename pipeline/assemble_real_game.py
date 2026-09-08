"""
pipeline/assemble_real_game.py: 赛博幸存者高精资产装配器
提供 SpriteSheetEngine 与赛博世界瓦片地图装配能力。
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from pipeline.sprite_asset_engine import SpriteAssetEngine
except ImportError:
    SpriteAssetEngine = None

def assemble_master_template(output_path: Path = None) -> bool:
    """装配赛博幸存者完整模板 (幂等操作，禁止直接覆写源模板)"""
    template_file = ROOT / "pipeline" / "templates" / "cyber_survivor_master.html"
    if not template_file.exists():
        return False

    html = template_file.read_text(encoding="utf-8")
    if SpriteAssetEngine:
        sprite_engine_js = SpriteAssetEngine.get_sprite_engine_js()
        script_marker = "<script>\n"
        if "const SpriteSheetEngine =" not in html and script_marker in html:
            html = html.replace(script_marker, script_marker + sprite_engine_js + "\n", 1)

    dest = output_path or (ROOT / "output" / "assembled_cyber_survivor.html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return True

if __name__ == "__main__":
    assemble_master_template()
