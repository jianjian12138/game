#!/usr/bin/env python3
"""
sprite_vector_synthesizer.py: 程序化角色与怪物矢量绘制中枢 (Sprite Vector Synthesizer)
彻底根除用单一 ctx.arc() 画纯色圆圈糊弄人的恶劣行为！
为 Agent 注入工业级 Q 版卡通人物分层装配绘制管线：
包含：足底阴影、动态披风、精细铠甲、生动五官大眼睛、手持专属武器、以及带有晶石巨拳的熔岩领主 Boss！
"""

class SpriteVectorSynthesizer:

    @staticmethod
    def get_vector_render_js() -> str:
        """返回高精度分层矢量角色绘制引擎 JavaScript 源码"""
        return """
// =================================================================
// 🎨 程序化角色与怪物多层矢量绘制引擎 (Sprite Vector Synthesizer)
// 彻底消灭单色小圆点！呈现具备五官、披风、武器与生动动画的商业级角色！
// =================================================================

const SpritePainter = (function() {

  // 1. 绘制足底柔和阴影
  function drawShadow(ctx, x, y, radius) {
    ctx.save();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
    ctx.beginPath();
    ctx.ellipse(x, y + radius * 0.75, radius * 0.85, radius * 0.32, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // 2. 绘制生动卡通大眼睛 (带水汪汪高光与眨眼)
  function drawChibiEyes(ctx, x, y, size, isBlinking) {
    ctx.save();
    if (isBlinking) {
      // 眯眼弯月笑
      ctx.strokeStyle = '#1a1a1a';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(x - size * 0.45, y, size * 0.3, 0.2, Math.PI - 0.2);
      ctx.arc(x + size * 0.45, y, size * 0.3, 0.2, Math.PI - 0.2);
      ctx.stroke();
    } else {
      // 黑色大瞳孔
      ctx.fillStyle = '#1a1a1a';
      ctx.beginPath();
      ctx.ellipse(x - size * 0.45, y, size * 0.32, size * 0.45, 0, 0, Math.PI * 2);
      ctx.ellipse(x + size * 0.45, y, size * 0.32, size * 0.45, 0, 0, Math.PI * 2);
      ctx.fill();

      // 白色反光高光点
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(x - size * 0.45 - 2, y - 2, size * 0.16, 0, Math.PI * 2);
      ctx.arc(x + size * 0.45 - 2, y - 2, size * 0.16, 0, Math.PI * 2);
      ctx.fill();

      // 腮红点缀
      ctx.fillStyle = 'rgba(255, 100, 120, 0.4)';
      ctx.beginPath();
      ctx.arc(x - size * 0.75, y + size * 0.3, size * 0.2, 0, Math.PI * 2);
      ctx.arc(x + size * 0.75, y + size * 0.3, size * 0.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  return {
    // -------------------------------------------------------------
    // A. 绘制玩家出战英雄 (根据职业定制披风、铠甲与手持武器)
    // -------------------------------------------------------------
    drawHero: function(ctx, x, y, charId, facingAngle, tick) {
      ctx.save();
      ctx.translate(x, y);

      const breath = Math.sin(tick * 0.08) * 1.8; // 呼吸起伏
      const walkTilt = Math.sin(tick * 0.15) * 0.06; // 走动微倾斜
      ctx.rotate(walkTilt);

      // 1. 阴影
      drawShadow(ctx, 0, 0, 18);

      // 2. 动态披风 (狂战角斗士 / 游侠)
      if (charId === 'char_warrior' || charId === 'char_ranger') {
        ctx.save();
        const capeColor = charId === 'char_warrior' ? '#c1121f' : '#2a9d8f';
        ctx.fillStyle = capeColor;
        ctx.beginPath();
        const capeWave = Math.sin(tick * 0.12) * 5;
        ctx.moveTo(-12, -2);
        ctx.quadraticCurveTo(-18 + capeWave, 18, -10 + capeWave, 24);
        ctx.lineTo(10 + capeWave, 24);
        ctx.quadraticCurveTo(18 + capeWave, 18, 12, -2);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }

      // 3. 身体躯干护甲
      ctx.save();
      const armorColor = charId === 'char_warrior' ? '#780000' : (charId === 'char_ranger' ? '#264653' : '#3a0ca3');
      ctx.fillStyle = armorColor;
      ctx.strokeStyle = '#ffd700';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(-10, -2 + breath * 0.5, 20, 18, 6);
      ctx.fill();
      ctx.stroke();
      ctx.restore();

      // 4. 头部与脸庞
      ctx.save();
      ctx.fillStyle = '#ffdfba'; // 白皙Q版肤色
      ctx.beginPath();
      ctx.arc(0, -10 + breath, 13, 0, Math.PI * 2);
      ctx.fill();

      // 发型 / 头盔 / 头带
      if (charId === 'char_warrior') {
        // 齐天大圣 / 泰坦战神金冠与束发
        ctx.fillStyle = '#4a2810';
        ctx.beginPath();
        ctx.arc(0, -14 + breath, 13, Math.PI, Math.PI * 2);
        ctx.fill();
        // 金箍金带
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(0, -11 + breath, 13, Math.PI * 1.15, Math.PI * 1.85);
        ctx.stroke();
      } else if (charId === 'char_ranger') {
        // 游侠绿头巾与刘海
        ctx.fillStyle = '#1d3557';
        ctx.beginPath();
        ctx.arc(0, -13 + breath, 14, Math.PI * 0.9, Math.PI * 2.1);
        ctx.fill();
      } else {
        // 奥术师紫星兜帽
        ctx.fillStyle = '#7209b7';
        ctx.beginPath();
        ctx.arc(0, -12 + breath, 15, Math.PI * 0.8, Math.PI * 2.2);
        ctx.lineTo(0, -28 + breath);
        ctx.closePath();
        ctx.fill();
      }

      // 眨眼动画
      const isBlinking = (tick % 90) > 85;
      drawChibiEyes(ctx, 0, -10 + breath, 7, isBlinking);
      ctx.restore();

      // 5. 手持专属武器 (根据朝向旋转)
      ctx.save();
      if (charId === 'char_warrior') {
        // 黄金战斧
        ctx.translate(14, -4 + breath);
        ctx.rotate(Math.sin(tick * 0.15) * 0.25);
        ctx.fillStyle = '#8b5a2b';
        ctx.fillRect(-2, -18, 4, 28); // 斧柄
        ctx.fillStyle = '#ffd700';
        ctx.strokeStyle = '#ff9900';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(2, -16);
        ctx.lineTo(16, -24);
        ctx.lineTo(12, -4);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      } else if (charId === 'char_ranger') {
        // 疾风双持银刃
        ctx.translate(12, -2 + breath);
        ctx.fillStyle = '#00eeff';
        ctx.beginPath();
        ctx.moveTo(0, 0); ctx.lineTo(14, -6); ctx.lineTo(10, 4); ctx.closePath();
        ctx.fill();
      } else {
        // 奥术雷电法杖
        ctx.translate(14, -6 + breath);
        ctx.fillStyle = '#4a2810';
        ctx.fillRect(-2, -20, 4, 32);
        // 法杖顶端发光宝珠
        ctx.fillStyle = '#00f5d4';
        ctx.shadowColor = '#00f5d4'; ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(0, -22, 6.5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();

      ctx.restore();
    },

    // -------------------------------------------------------------
    // B. 绘制生动怪物生物 (拒绝绿点！画出甲壳毒虫、自爆蝠与巨型Boss)
    // -------------------------------------------------------------
    drawMonster: function(ctx, e, tick) {
      ctx.save();
      ctx.translate(e.x, e.y);

      // 1. 怪物阴影
      drawShadow(ctx, 0, 0, e.radius * 0.9);

      if (e.isBoss) {
        // 🌟 巨型熔岩岩石 Boss (高度还原用户截图 1 的晶石领主！)
        const breath = Math.sin(tick * 0.08) * 3;
        
        // 熔岩核心身躯
        ctx.fillStyle = '#ff7b00';
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 3.5;
        ctx.beginPath();
        ctx.roundRect(-30, -28 + breath, 60, 52, 14);
        ctx.fill();
        ctx.stroke();

        // 晶石肩甲 (左右突出冰蓝/金黄水晶)
        ctx.fillStyle = '#00eeff';
        ctx.beginPath();
        ctx.moveTo(-32, -20 + breath); ctx.lineTo(-46, -38 + breath); ctx.lineTo(-24, -34 + breath); ctx.closePath();
        ctx.fill();
        ctx.beginPath();
        ctx.moveTo(32, -20 + breath); ctx.lineTo(46, -38 + breath); ctx.lineTo(24, -34 + breath); ctx.closePath();
        ctx.fill();

        // Boss 威严冠冕与怒目
        ctx.fillStyle = '#ffaa00';
        ctx.beginPath();
        ctx.moveTo(-16, -28 + breath); ctx.lineTo(0, -42 + breath); ctx.lineTo(16, -28 + breath); ctx.closePath();
        ctx.fill();

        // 赤红怒目
        ctx.fillStyle = '#ff0000';
        ctx.shadowColor = '#ff0000'; ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.ellipse(-10, -14 + breath, 5, 8, 0.2, 0, Math.PI * 2);
        ctx.ellipse(10, -14 + breath, 5, 8, -0.2, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // 两只浮空巨拳 (带脉冲)
        const fistBob = Math.cos(tick * 0.1) * 4;
        ctx.fillStyle = '#ff9e00';
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 2;
        // 左拳
        ctx.beginPath(); ctx.roundRect(-48, 8 + fistBob, 20, 22, 6); ctx.fill(); ctx.stroke();
        // 右拳
        ctx.beginPath(); ctx.roundRect(28, 8 - fistBob, 20, 22, 6); ctx.fill(); ctx.stroke();

      } else if (e.radius > 12) {
        // 狂暴自爆蛛 (红色甲壳与四肢)
        const legWiggle = Math.sin(tick * 0.2) * 4;
        ctx.strokeStyle = '#a30000';
        ctx.lineWidth = 2.5;
        // 蜘蛛腿
        ctx.beginPath();
        ctx.moveTo(-10, 0); ctx.lineTo(-18, -8 + legWiggle);
        ctx.moveTo(-10, 6); ctx.lineTo(-18, 12 - legWiggle);
        ctx.moveTo(10, 0); ctx.lineTo(18, -8 - legWiggle);
        ctx.moveTo(10, 6); ctx.lineTo(18, 12 + legWiggle);
        ctx.stroke();

        // 猩红甲壳与核心复眼
        ctx.fillStyle = '#d90429';
        ctx.beginPath();
        ctx.arc(0, 0, 12, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffd700';
        ctx.beginPath();
        ctx.arc(-4, -2, 2.5, 0, Math.PI * 2);
        ctx.arc(4, -2, 2.5, 0, Math.PI * 2);
        ctx.fill();

      } else {
        // 异星绿色幼虫 (软萌爬虫造型)
        const wiggle = Math.sin(tick * 0.2) * 3;
        ctx.fillStyle = '#70e000';
        ctx.beginPath();
        ctx.arc(0, 0, 10, 0, Math.PI * 2);
        ctx.fill();

        // 两根小触角
        ctx.strokeStyle = '#38b000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(-4, -8); ctx.lineTo(-8 + wiggle, -15);
        ctx.moveTo(4, -8); ctx.lineTo(8 + wiggle, -15);
        ctx.stroke();

        // 萌萌黑圆眼
        ctx.fillStyle = '#004b23';
        ctx.beginPath();
        ctx.arc(-3, -2, 2, 0, Math.PI * 2);
        ctx.arc(3, -2, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // 血条 (统一工业风格)
      if (e.hp < e.maxHp) {
        const pct = Math.max(0, e.hp / e.maxHp);
        const barW = e.isBoss ? 70 : 26;
        ctx.fillStyle = 'rgba(0,0,0,0.7)';
        ctx.fillRect(-barW/2, -e.radius - 12, barW, 5);
        ctx.fillStyle = e.isBoss ? '#ff0055' : '#70e000';
        ctx.fillRect(-barW/2, -e.radius - 12, barW * pct, 5);
      }

      ctx.restore();
    }
  };
})();
"""
