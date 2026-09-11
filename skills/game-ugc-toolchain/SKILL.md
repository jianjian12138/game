---
name: game-ugc-toolchain
description: |
  玩家创作与UGC工具链（UGC Toolchain & Community Sharing）工程规范。
  专治自制关卡缺少校验导致卡关死循环、谱面未对齐节拍、自定义赛道脱轨断路、
  分享口令体积过大无法在聊天软件传播等痛点。涵盖关卡编辑器（LevelEditor）、
  节奏谱面编辑器（ChartEditorTool）、竞速赛道编辑器（TrackEditorTool）、
  加密完整性打包器（UGCPackage）及极简压缩分享口令（UGCShare）。
---

# 玩家创作与UGC工具链工程规范

## 1. 核心套件矩阵

- **LevelEditor (`core/ugc/level_editor.py`)**：
  2D网格/自由实体布设，强制前置可玩性合法性校验（必须有且仅有1个玩家出生点，至少1个通关终点）。
- **ChartEditorTool (`core/ugc/chart_editor_tool.py`)**：
  音游玩家UGC谱面制作，支持 1/4, 1/8, 1/16 拍节拍自动吸附量化与左右手轨道镜像反转。
- **TrackEditorTool (`core/ugc/track_editor_tool.py`)**：
  竞速赛道控制点样条编辑，支持闭环回路校验与总路程里程结算。
- **UGCPackage (`core/ugc/ugc_package.py`)**：
  带 SHA-256 签名指纹的元数据信封打包，彻底杜绝数据在传输或篡改中损坏。
- **UGCShare (`core/ugc/ugc_share.py`)**：
  采用 Zlib Level 9 深度压缩与 URL-Safe Base64 编码，生成形如 `UGC:eJy...` 的轻量短口令，无缝贴合微信与剪贴板一键分享导入。
