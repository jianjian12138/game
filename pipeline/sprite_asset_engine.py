"""
Sprite Asset Engine (精灵图集与像素美术资产管线)
对齐开源游戏标杆（Onslaught Arena / Pico-8 / Endesga-32），
提供零外部依赖的程序化像素图集编译、多帧逐帧动画、地牢瓦片集生成与 60FPS 极速渲染管线。
"""

from typing import Dict, Any

class SpriteAssetEngine:
    """像素精灵图集与瓦片引擎代码生成器"""

    @staticmethod
    def get_sprite_engine_js() -> str:
        """生成注入到 HTML/JS 游戏客户端的高保真精灵图集与地牢瓦片引擎"""
        return """
// =========================================================================
// 像素艺术精灵图集与地牢瓦片引擎 (Pixel-Art SpriteAtlas & Tilemap Engine)
// 对齐开源标杆 Onslaught Arena / Vampire Survivors，告别裸几何画圆！
// =========================================================================
const SpriteSheetEngine = {
  canvas: null,
  ctx: null,
  tileCanvas: null,
  tileCtx: null,

  // 16 色高对比赛博地牢像素色盘 (Pico-8 & Endesga-32 黄金微调版)
  PALETTE: {
    black: '#05070e',
    darkBlue: '#0c1527',
    deepSlate: '#19253d',
    stoneGray: '#334764',
    lightSlate: '#60799f',
    highlightWhite: '#edf2f9',
    pureWhite: '#ffffff',
    bloodRed: '#dc2626',
    neonRed: '#ef4444',
    fireOrange: '#f97316',
    goldYellow: '#fbbf24',
    cyberCyan: '#00f0ff',
    plasmaBlue: '#0284c7',
    slimeGreen: '#10b981',
    toxicPurple: '#a855f7',
    darkPurple: '#581c87'
  },

  // 精灵槽位定义 [col, row, width, height]
  SPRITES: {
    // 特工英雄 (32x32)
    hero_idle_0:   [0, 0, 32, 32],
    hero_walk_0:   [32, 0, 32, 32],
    hero_walk_1:   [64, 0, 32, 32],
    hero_walk_2:   [96, 0, 32, 32],
    hero_walk_3:   [128, 0, 32, 32],
    hero_attack_0: [160, 0, 32, 32],
    hero_hurt_0:   [192, 0, 32, 32],
    hero_die_0:    [224, 0, 32, 32],

    // 爬虫小怪 (24x24)
    crawler_walk_0: [0, 32, 24, 24],
    crawler_walk_1: [24, 32, 24, 24],
    crawler_hurt_0: [48, 32, 24, 24],

    // 重甲骷髅狂暴者 (32x32)
    enforcer_walk_0: [0, 56, 32, 32],
    enforcer_walk_1: [32, 56, 32, 32],
    enforcer_attack: [64, 56, 32, 32],
    enforcer_hurt:   [96, 56, 32, 32],

    // 浮空邪眼无人机 (24x24)
    drone_float_0: [0, 88, 24, 24],
    drone_float_1: [24, 88, 24, 24],
    drone_hurt_0:  [48, 88, 24, 24],

    // 烈焰自爆魔 (28x28)
    bomber_walk_0: [0, 112, 28, 28],
    bomber_walk_1: [28, 112, 28, 28],
    bomber_ignite: [56, 112, 28, 28],

    // 黄金宝箱 (24x24)
    chest_closed: [0, 140, 24, 24],
    chest_open:   [24, 140, 24, 24],

    // 补给水晶与掉落物 (16x16)
    gem_blue:  [0, 164, 16, 16],
    gem_gold:  [16, 164, 16, 16],
    gem_heal:  [32, 164, 16, 16],
    gem_mag:   [48, 164, 16, 16],

    // 歼灭领主 Boss (64x64)
    boss_stomp_0: [0, 180, 64, 64],
    boss_stomp_1: [64, 180, 64, 64],
    boss_rage_0:  [128, 180, 64, 64]
  },

  // 瓦片槽位定义 (32x32)
  TILES: {
    floor_stone_0: [0, 0, 32, 32],
    floor_cracked: [32, 0, 32, 32],
    floor_runic:   [64, 0, 32, 32],
    floor_grate:   [96, 0, 32, 32],
    wall_top:      [0, 32, 32, 32],
    wall_face:     [32, 32, 32, 32],
    wall_corner:   [64, 32, 32, 32],
    wall_torch:    [96, 32, 32, 32]
  },

  init: function() {
    // 1. 初始化精灵图集画布 (256x256)
    this.canvas = document.createElement('canvas');
    this.canvas.width = 256;
    this.canvas.height = 256;
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
    this.ctx.imageSmoothingEnabled = false;

    // 2. 初始化地牢瓦片画布 (128x64)
    this.tileCanvas = document.createElement('canvas');
    this.tileCanvas.width = 128;
    this.tileCanvas.height = 64;
    this.tileCtx = this.tileCanvas.getContext('2d', { willReadFrequently: true });
    this.tileCtx.imageSmoothingEnabled = false;

    // 3. 离线预烘焙图集
    this.bakeTiles();
    this.bakeSprites();
    console.log('🎨 [SpriteSheetEngine] 像素精灵图集与地牢瓦片集烘焙就绪！');
  },

  // 辅助像素绘制函数
  drawPixelMatrix: function(ctx, x, y, matrix, colorMap, scale = 1) {
    for (let r = 0; r < matrix.length; r++) {
      for (let c = 0; c < matrix[r].length; c++) {
        const char = matrix[r][c];
        if (char !== ' ' && colorMap[char]) {
          ctx.fillStyle = colorMap[char];
          ctx.fillRect(x + c * scale, y + r * scale, scale, scale);
        }
      }
    }
  },

  // 烘焙真实地牢瓦片
  bakeTiles: function() {
    const c = this.tileCtx;
    const P = this.PALETTE;

    // 1. 普通石板地面 (floor_stone_0)
    c.fillStyle = P.darkBlue;
    c.fillRect(0, 0, 32, 32);
    // 砖缝与明暗凹凸
    c.fillStyle = P.deepSlate;
    c.fillRect(1, 1, 14, 14); c.fillRect(17, 1, 14, 14);
    c.fillRect(1, 17, 30, 14);
    c.fillStyle = P.stoneGray;
    c.fillRect(2, 2, 12, 1); c.fillRect(18, 2, 12, 1); c.fillRect(2, 18, 28, 1);
    c.fillStyle = P.black;
    c.fillRect(0, 0, 32, 1); c.fillRect(0, 16, 32, 1); c.fillRect(16, 0, 1, 16);

    // 2. 裂纹石板地面 (floor_cracked)
    c.drawImage(this.tileCanvas, 0, 0, 32, 32, 32, 0, 32, 32);
    c.fillStyle = P.black;
    // 绘制裂纹线
    c.fillRect(40, 6, 2, 8); c.fillRect(42, 14, 6, 2); c.fillRect(48, 16, 4, 6);
    c.fillStyle = P.cyberCyan;
    c.fillRect(44, 15, 2, 2); // 缝隙微弱溢出的赛博荧光

    // 3. 赛博符文能量地砖 (floor_runic)
    c.drawImage(this.tileCanvas, 0, 0, 32, 32, 64, 0, 32, 32);
    c.strokeStyle = P.cyberCyan;
    c.lineWidth = 1;
    c.strokeRect(64 + 6.5, 6.5, 19, 19);
    c.fillStyle = P.cyberCyan;
    c.fillRect(64 + 14, 14, 4, 4);

    // 4. 金属格栅散热板 (floor_grate)
    c.fillStyle = P.black;
    c.fillRect(96, 0, 32, 32);
    c.fillStyle = P.deepSlate;
    c.fillRect(98, 2, 28, 28);
    c.fillStyle = P.black;
    for (let i = 0; i < 6; i++) {
      c.fillRect(100, 4 + i * 4, 24, 2);
    }

    // 5. 墙顶 (wall_top)
    c.fillStyle = P.black;
    c.fillRect(0, 32, 32, 32);
    c.fillStyle = P.stoneGray;
    c.fillRect(2, 34, 28, 28);
    c.fillStyle = P.lightSlate;
    c.fillRect(2, 34, 28, 2); c.fillRect(2, 34, 2, 28);

    // 6. 墙面带下沉阴影 (wall_face)
    c.fillStyle = P.darkBlue;
    c.fillRect(32, 32, 32, 32);
    c.fillStyle = P.black;
    c.fillRect(32, 32, 32, 8); // 顶部深色投射阴影
    c.fillStyle = P.deepSlate;
    c.fillRect(34, 42, 28, 20);

    // 7. 墙角柱 (wall_corner)
    c.fillStyle = P.deepSlate;
    c.fillRect(64, 32, 32, 32);
    c.fillStyle = P.lightSlate;
    c.fillRect(66, 34, 4, 26);
    c.fillStyle = P.black;
    c.fillRect(90, 34, 4, 26);

    // 8. 墙面全息火炬 (wall_torch)
    c.drawImage(this.tileCanvas, 32, 32, 32, 32, 96, 32, 32, 32);
    c.fillStyle = P.fireOrange;
    c.fillRect(96 + 14, 32 + 12, 4, 6);
    c.fillStyle = P.goldYellow;
    c.fillRect(96 + 15, 32 + 10, 2, 4);
  },

  // 烘焙全部角色、敌人、武器与道具像素精灵
  bakeSprites: function() {
    const c = this.ctx;
    const P = this.PALETTE;

    const heroMap = {
      'B': P.black,
      'S': P.deepSlate,
      'G': P.stoneGray,
      'L': P.lightSlate,
      'W': P.pureWhite,
      'C': P.cyberCyan,
      'P': P.plasmaBlue,
      'Y': P.goldYellow,
      'R': P.bloodRed
    };

    // --- 1. 特工主角 (32x32 像素点阵) ---
    // 待机帧 (hero_idle_0)
    const heroIdleMat = [
      "        BBBBBBBB        ",
      "       BCCCCCCCCB       ",
      "      BCCCCCCCCCCB      ",
      "      BCWWCCCCWWCB      ",
      "      BCCCCWCCCCCB      ",
      "       BCCCCCCCCB       ",
      "       BBBBBBBBBB       ",
      "      BPPSSSSSSPPB      ",
      "     BPPSSLLLLSSPPB     ",
      "     BPSSLLLLLLSSPB     ",
      "     BPSSLLLLLLSSPB     ",
      "     BPPSSLLLLSSPPB     ",
      "      BPPSSSSSSPPB      ",
      "       BGGGGGGGBB       ",
      "       BSSB  BSSB       ",
      "       BSSB  BSSB       ",
      "       BSSB  BSSB       ",
      "       BBBB  BBBB       "
    ];
    this.drawPixelMatrix(c, 0 + 8, 0 + 6, heroIdleMat, heroMap, 1);

    // 行走帧 1 (hero_walk_0 - 迈出左腿)
    const heroWalk1Mat = [
      "        BBBBBBBB        ",
      "       BCCCCCCCCB       ",
      "      BCCCCCCCCCCB      ",
      "      BCWWCCCCWWCB      ",
      "       BCCCCCCCCB       ",
      "       BBBBBBBBBB       ",
      "      BPPSSSSSSPPB      ",
      "     BPPSSLLLLSSPPB     ",
      "     BPSSLLLLLLSSPB     ",
      "      BPPSSSSSSPPB      ",
      "       BGGGGGGGBB       ",
      "      BSSSSB  BB        ",
      "      BSSSSB BSSB       ",
      "       BBBB  BSSB       ",
      "             BBBB       "
    ];
    this.drawPixelMatrix(c, 32 + 8, 0 + 6, heroWalk1Mat, heroMap, 1);

    // 行走帧 2 (hero_walk_1 - 迈出右腿)
    const heroWalk2Mat = [
      "        BBBBBBBB        ",
      "       BCCCCCCCCB       ",
      "      BCCCCCCCCCCB      ",
      "      BCWWCCCCWWCB      ",
      "       BCCCCCCCCB       ",
      "       BBBBBBBBBB       ",
      "      BPPSSSSSSPPB      ",
      "     BPPSSLLLLSSPPB     ",
      "     BPSSLLLLLLSSPB     ",
      "      BPPSSSSSSPPB      ",
      "       BGGGGGGGBB       ",
      "        BB  BSSSSB      ",
      "       BSSB BSSSSB      ",
      "       BSSB  BBBB       ",
      "       BBBB             "
    ];
    this.drawPixelMatrix(c, 64 + 8, 0 + 6, heroWalk2Mat, heroMap, 1);

    // 攻击挥砍/射击帧 (hero_attack_0)
    c.drawImage(this.canvas, 0, 0, 32, 32, 160, 0, 32, 32);
    c.fillStyle = P.cyberCyan;
    c.fillRect(160 + 24, 12, 7, 3); // 枪口能量闪光
    c.fillStyle = P.pureWhite;
    c.fillRect(160 + 26, 13, 5, 1);

    // 受击闪白红帧 (hero_hurt_0)
    const heroHurtMap = { ...heroMap, 'C': P.pureWhite, 'L': P.neonRed, 'S': P.bloodRed, 'P': P.neonRed };
    this.drawPixelMatrix(c, 192 + 8, 0 + 6, heroIdleMat, heroHurtMap, 1);

    // 倒地战死帧 (hero_die_0)
    c.save();
    c.translate(224 + 16, 24);
    c.rotate(Math.PI / 2);
    c.drawImage(this.canvas, 0, 0, 32, 32, -16, -16, 32, 32);
    c.restore();

    // --- 2. 爬虫小怪 (crawler 24x24) ---
    const spiderMap = { 'B': P.black, 'R': P.bloodRed, 'N': P.neonRed, 'S': P.stoneGray, 'P': P.toxicPurple };
    const crawlerMat = [
      "  B          B  ",
      "   B        B   ",
      "  BBNNNNNNNNBB  ",
      " BBNNNPRRPNNNBB ",
      "BBNNNRRRRRRNNNBB",
      " BBNNNPRRPNNNBB ",
      "  BBNNNNNNNNBB  ",
      "   B  BBBB  B   ",
      "  B          B  "
    ];
    this.drawPixelMatrix(c, 0 + 4, 32 + 6, crawlerMat, spiderMap, 1);
    this.drawPixelMatrix(c, 24 + 4, 32 + 5, crawlerMat, spiderMap, 1); // 动步态微抬
    // 爬虫受击
    const spiderHurtMap = { ...spiderMap, 'R': P.pureWhite, 'N': P.pureWhite, 'P': P.pureWhite };
    this.drawPixelMatrix(c, 48 + 4, 32 + 6, crawlerMat, spiderHurtMap, 1);

    // --- 3. 重甲骷髅狂暴者 (enforcer 32x32) ---
    const enfMap = { 'B': P.black, 'W': P.highlightWhite, 'S': P.deepSlate, 'G': P.goldYellow, 'R': P.bloodRed };
    const enforcerMat = [
      "      BBBBBB      ",
      "     BWWWWWWWB    ",
      "    BWWBRRWBWWB   ",
      "    BWWWWWWWWWB   ",
      "     BWBWBWBWB    ",
      "      BBBBBB      ",
      "     BSSSSSSB     ",
      "   BBSSSSSSSSBB   ",
      "  BGGSSSSSSSSGGB  ",
      "  BGGSSSSSSSSGGB  ",
      "   BBSSSSSSSSBB   ",
      "      BSSBSSB     ",
      "      BSSBSSB     ",
      "      BBBBBBB     "
    ];
    this.drawPixelMatrix(c, 0 + 8, 56 + 6, enforcerMat, enfMap, 1);
    this.drawPixelMatrix(c, 32 + 8, 56 + 5, enforcerMat, enfMap, 1);
    // 狂暴受击
    const enfHurtMap = { ...enfMap, 'W': P.pureWhite, 'S': P.neonRed, 'G': P.fireOrange };
    this.drawPixelMatrix(c, 96 + 8, 56 + 6, enforcerMat, enfHurtMap, 1);

    // --- 4. 浮空邪眼无人机 (drone 24x24) ---
    const eyeMap = { 'B': P.black, 'P': P.toxicPurple, 'D': P.darkPurple, 'C': P.cyberCyan, 'W': P.pureWhite, 'R': P.bloodRed };
    const droneMat = [
      "    BBBBBB    ",
      "   BDPPPPDDB  ",
      "  BDPPWWPPDDB ",
      " BDPPWCCWPPDDB",
      " BDPPWCRWPPDDB",
      " BDPPWCCWPPDDB",
      "  BDPPWWPPDDB ",
      "   BDPPPPDDB  ",
      "   B B  B B   ",
      "  B   B  B B  "
    ];
    this.drawPixelMatrix(c, 0 + 5, 88 + 5, droneMat, eyeMap, 1);
    this.drawPixelMatrix(c, 24 + 5, 88 + 7, droneMat, eyeMap, 1);
    const eyeHurtMap = { ...eyeMap, 'P': P.pureWhite, 'C': P.pureWhite, 'W': P.pureWhite };
    this.drawPixelMatrix(c, 48 + 5, 88 + 6, droneMat, eyeHurtMap, 1);

    // --- 5. 烈焰自爆魔 (bomber 28x28) ---
    const bombMap = { 'B': P.black, 'F': P.fireOrange, 'Y': P.goldYellow, 'R': P.bloodRed, 'S': P.deepSlate };
    const bomberMat = [
      "     BBBBBB     ",
      "   BBFFFFFFFFBB ",
      "  BFFYYYYYYYYFFB",
      " BFFYYRRRRRRFFFB",
      " BFFYYRRRRRRFFFB",
      "  BFFYYYYYYYYFFB",
      "   BBFFFFFFFFBB ",
      "     BSSB BSSB  ",
      "     BBB   BBB  "
    ];
    this.drawPixelMatrix(c, 0 + 6, 112 + 6, bomberMat, bombMap, 1);
    this.drawPixelMatrix(c, 28 + 6, 112 + 5, bomberMat, bombMap, 1);
    const bombIgniteMap = { ...bombMap, 'F': P.pureWhite, 'Y': P.pureWhite, 'R': P.pureWhite };
    this.drawPixelMatrix(c, 56 + 6, 112 + 6, bomberMat, bombIgniteMap, 1);

    // --- 6. 黄金宝箱 (chest 24x24) ---
    c.fillStyle = P.black;
    c.fillRect(0 + 2, 140 + 6, 20, 14);
    c.fillStyle = P.goldYellow;
    c.fillRect(0 + 3, 140 + 7, 18, 12);
    c.fillStyle = P.fireOrange;
    c.fillRect(0 + 5, 140 + 9, 14, 8);
    c.fillStyle = P.pureWhite;
    c.fillRect(0 + 11, 140 + 10, 2, 4); // 锁扣

    // 宝箱开启
    c.drawImage(this.canvas, 0, 140, 24, 24, 24, 140, 24, 24);
    c.fillStyle = P.cyberCyan;
    c.fillRect(24 + 5, 140 + 2, 14, 5); // 冲天光柱

    // --- 7. 经验宝石与补给水晶 (gems 16x16) ---
    // 蓝宝石 (gem_blue)
    c.fillStyle = P.cyberCyan;
    c.beginPath(); c.arc(8, 164 + 8, 5, 0, Math.PI * 2); c.fill();
    c.fillStyle = P.pureWhite;
    c.fillRect(6, 164 + 6, 2, 2);

    // 金宝石 (gem_gold)
    c.fillStyle = P.goldYellow;
    c.beginPath(); c.arc(16 + 8, 164 + 8, 6, 0, Math.PI * 2); c.fill();
    c.fillStyle = P.pureWhite;
    c.fillRect(16 + 6, 164 + 6, 2, 2);

    // 回血十字 (gem_heal)
    c.fillStyle = P.slimeGreen;
    c.fillRect(32 + 6, 164 + 3, 4, 10);
    c.fillRect(32 + 3, 164 + 6, 10, 4);

    // 磁吸徽章 (gem_mag)
    c.fillStyle = P.plasmaBlue;
    c.fillRect(48 + 3, 164 + 4, 10, 8);
    c.fillStyle = P.pureWhite;
    c.fillRect(48 + 5, 164 + 6, 6, 4);

    // --- 8. 歼灭巨兽 Boss (64x64) ---
    const bossMap = { 'B': P.black, 'S': P.deepSlate, 'L': P.stoneGray, 'W': P.pureWhite, 'R': P.bloodRed, 'O': P.fireOrange };
    const bossMat = [
      "        BBBBBBBBBBBB        ",
      "      BBLLLLSSSSLLLLBB      ",
      "     BLLLLRRSSSSRRLLLLB     ",
      "    BLLLLRWWSSSSWWTRLLLB    ",
      "    BLLLLRRSSSSRRLLLLLLB    ",
      "     BBLLLLSSSSLLLLBB       ",
      "       BBBBBBBBBBBB         ",
      "    BBSSSSOOOOOOOSSSSBB     ",
      "   BSSSOOOOOOOOOOOOOSSSB    ",
      "  BSSSOOORRRRRRROOOOSSSB    ",
      "  BSSSOOORRRRRRROOOOSSSB    ",
      "   BSSSOOOOOOOOOOOOOSSSB    ",
      "    BBSSSSOOOOOOOSSSSBB     ",
      "      BBSSBBBBBBSSBB        ",
      "      BSSB      BSSB        ",
      "      BSSB      BSSB        ",
      "      BBBB      BBBB        "
    ];
    this.drawPixelMatrix(c, 0 + 8, 180 + 8, bossMat, bossMap, 2);
    this.drawPixelMatrix(c, 64 + 8, 180 + 6, bossMat, bossMap, 2);
    const bossRageMap = { ...bossMap, 'S': P.bloodRed, 'L': P.neonRed, 'O': P.pureWhite };
    this.drawPixelMatrix(c, 128 + 8, 180 + 8, bossMat, bossRageMap, 2);
  },

  // 绘制精灵图方法
  drawSprite: function(destCtx, spriteKey, destX, destY, options = {}) {
    const s = this.SPRITES[spriteKey];
    if (!s) return;
    const [sx, sy, sw, sh] = s;
    const flipX = options.flipX || false;
    const scaleX = options.scaleX || 1.0;
    const scaleY = options.scaleY || 1.0;
    const angle = options.angle || 0;
    const alpha = options.alpha !== undefined ? options.alpha : 1.0;

    destCtx.save();
    destCtx.translate(destX, destY);
    if (alpha < 1.0) destCtx.globalAlpha = alpha;
    if (angle !== 0) destCtx.rotate(angle);
    if (scaleX !== 1.0 || scaleY !== 1.0 || flipX) {
      destCtx.scale(flipX ? -scaleX : scaleX, scaleY);
    }

    // 居中绘制
    destCtx.drawImage(this.canvas, sx, sy, sw, sh, -sw / 2, -sh / 2, sw, sh);
    destCtx.restore();
  },

  // 绘制地牢瓦片地图
  drawTile: function(destCtx, tileKey, destX, destY, tileSize = 32) {
    const t = this.TILES[tileKey];
    if (!t) return;
    const [sx, sy, sw, sh] = t;
    destCtx.drawImage(this.tileCanvas, sx, sy, sw, sh, destX, destY, tileSize, tileSize);
  }
};
"""
