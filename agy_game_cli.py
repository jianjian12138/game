"""
Antigravity Game Platform — Master Unified Developer CLI
=========================================================
Unified command-line interface for:
  - Querying the 34 Parts in Ford-T Catalog
  - Assembling custom multi-genre game architectures
  - Running Card & Roguelike Monte Carlo balancing simulations
  - Executing Commercial Release Gate audits
  - Managing playable archetype templates
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure root directory in sys.path
ROOT_DIR = str(Path(__file__).resolve().parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.ford_t_game_parts_hub import ModularGameAssembler
from pipeline.card_balance_simulator import CardBalanceSimulator
from pipeline.roguelike_synergy_balancer import RoguelikeSynergyBalancer
from pipeline.release_gate import ReleaseGate
from pipeline.wechat_packager import WeChatPackager


def cmd_list_parts(args):
    assembler = ModularGameAssembler()
    catalog = assembler.catalog

    print("================================================================")
    print(f"FORD-T GAME PARTS CATALOG - {len(catalog)} PRE-FABRICATED PARTS")
    print("================================================================")

    categories = {}
    for key, part in catalog.items():
        cat = getattr(part, "category", "CORE")
        categories.setdefault(cat, []).append((key, part.name))

    for cat, items in sorted(categories.items()):
        print(f"\n[{cat}] ({len(items)} parts):")
        for key, name in sorted(items):
            print(f"  - {key:<20} -> {name}")
    print("\n================================================================")


def cmd_assemble(args):
    assembler = ModularGameAssembler()
    parts = [p.strip() for p in args.parts.split(",") if p.strip()]
    try:
        res = assembler.assemble(title=args.title, selected_part_keys=parts)
        print(f"SUCCESS: Assembled game '{res['title']}' with {res['parts_count']} parts:")
        for p in res["active_parts"]:
            print(f"  [+] Mounted: {p}")
    except KeyError as e:
        print(f"ASSEMBLY ERROR: {e}")
        sys.exit(1)


def cmd_balance(args):
    btype = args.type.lower()
    if btype == "card":
        print("Running Card Archetype Balance Simulation...")
        sim = CardBalanceSimulator()
        matrix = sim.run_matrix(games_per_pair=args.games)
        for m in matrix:
            print(f"  [{m['deck_a']} vs {m['deck_b']}]: {m['winrate_a']}% / {m['winrate_b']}% -> {m['assessment']}")
    elif btype in ["rogue", "roguelike"]:
        print("Running Roguelike Synergy Balance Simulation...")
        balancer = RoguelikeSynergyBalancer()
        res = balancer.simulate_runs(num_runs=args.games, items_per_run=6)
        print(f"  Runs: {res['num_runs']} | Avg Power: {res['avg_power_score']} | OP Ratio: {res['op_run_ratio_pct']}% -> {res['status']}")
    else:
        print(f"Unknown balance type: {btype}. Supported: 'card', 'roguelike'")


def cmd_audit(args):
    gate = ReleaseGate()
    tests_ok, suite_res = gate.run_all_validations()
    budget = gate.audit_package_budget()
    passed = tests_ok and budget["compliant"]
    print(f"RELEASE GATE STATUS: {'APPROVED' if passed else 'BLOCKED'}")
    for s in suite_res:
        status = "OK" if s["passed"] else "FAIL"
        print(f"  {s['suite']:<45}: {status} ({s['elapsed_sec']}s)")
    print(f"WeChat Subpackage: {budget['first_package_mb']}MB / 4.0MB ({budget['ratio_pct']}%)")
    sys.exit(0 if passed else 1)


def cmd_templates(args):
    print("================================================================")
    print("AI-NATIVE PLAYABLE ARCHETYPE TEMPLATES")
    print("================================================================")
    print("1. Card Roguelike (Spire-like):")
    print("   Engine: templates/card_roguelike/card_game_engine.py")
    print("   HTML5:  templates/card_roguelike/index.html")
    print("2. Survivor Danmaku (Bullet Hell):")
    print("   Engine: templates/survivor_danmaku/danmaku_engine.py")
    print("   HTML5:  templates/survivor_danmaku/index.html")
    print("3. Combat Arena Showcase:")
    print("   HTML5:  build/playable_showcase.html")
    print("================================================================")


def cmd_wechat_pack(args):
    tpl_map = {
        "survivor": "templates/survivor_danmaku/index.html",
        "danmaku": "templates/survivor_danmaku/index.html",
        "survivor_danmaku": "templates/survivor_danmaku/index.html",
        "card": "templates/card_roguelike/index.html",
        "card_roguelike": "templates/card_roguelike/index.html",
        "showcase": "build/playable_showcase.html",
    }
    src = tpl_map.get(args.template.lower())
    if not src:
        src_path = Path(args.template)
        if not src_path.exists():
            print(f"Error: Template or file '{args.template}' not found.")
            sys.exit(1)
    else:
        src_path = Path(ROOT_DIR) / src

    out_dir = Path(ROOT_DIR) / args.out
    packager = WeChatPackager()
    res = packager.bundle(
        src_path,
        out_dir,
        project_name=args.name,
        orientation=args.orientation
    )
    print("SUCCESS: WeChat Mini-Game bundled:")
    print(f"  Target: {res['output_dir']}")
    print(f"  Size:   {res['size_mb']}MB / {res['max_mb']}MB (Compliant: {res['compliant']})")
    print(f"  Files:  {', '.join(res['files_generated'])}")


def main():
    parser = argparse.ArgumentParser(description="Antigravity AI-Native Game Engine Platform CLI")
    subparsers = parser.add_subparsers(dest="command")

    # list-parts
    subparsers.add_parser("list-parts", help="List all 34 parts in Ford-T catalog")

    # assemble
    p_assemble = subparsers.add_parser("assemble", help="Assemble game from parts")
    p_assemble.add_argument("title", help="Game Title")
    p_assemble.add_argument("--parts", required=True, help="Comma-separated part keys")

    # balance
    p_balance = subparsers.add_parser("balance", help="Run balance simulations")
    p_balance.add_argument("--type", default="card", choices=["card", "roguelike"], help="Simulator type")
    p_balance.add_argument("--games", type=int, default=100, help="Number of games/runs")

    # audit
    subparsers.add_parser("audit", help="Run full commercial release gate audit")

    # templates
    subparsers.add_parser("templates", help="List built-in playable archetype templates")

    # wechat-pack
    p_wx = subparsers.add_parser("wechat-pack", help="Bundle HTML template into WeChat Mini-Game")
    p_wx.add_argument("--template", default="survivor_danmaku", help="Template name (survivor_danmaku, card_roguelike, showcase) or HTML path")
    p_wx.add_argument("--out", default="dist/wechat", help="Output directory")
    p_wx.add_argument("--name", default="antigravity-wechat-game", help="Project name")
    p_wx.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"], help="Screen orientation")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "list-parts":
        cmd_list_parts(args)
    elif args.command == "assemble":
        cmd_assemble(args)
    elif args.command == "balance":
        cmd_balance(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "templates":
        cmd_templates(args)
    elif args.command == "wechat-pack":
        cmd_wechat_pack(args)


if __name__ == "__main__":
    main()

