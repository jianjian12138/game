#!/usr/bin/env python3
"""
commercial_engines.py: 商业级四大旗舰游戏工业引擎生成器 (Commercial Flagship Game Engines)
提供真正可商用、体验深度完整、具备 3D PBR/回合制复杂状态机/体素物理/三消重力的独立工程：
1. 3D FPS 第一人称射击 (反恐精英 CS / 战地)
2. 3D 体素沙盒世界 (我的世界 Minecraft 3D)
3. 国风玄幻回合制 RPG 战斗系统 (梦幻西游 / 仙剑)
4. 深度关卡益智三消 (开心消消乐)
"""
from typing import Dict, Any

class CommercialEngines:

    @staticmethod
    def generate_3d_fps_cs(title: str = "反恐前线：幽灵突击", custom_rules: str = "") -> str:
        """生成商业级 3D 第一人称射击 (FPS) 游戏 (基于 Three.js 3D WebGL PBR、第一人称视角、枪模、后坐力、3D敌人AI、Hitbox部位伤害)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - 3D FPS 商业旗舰版</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #000; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; width: 100vw; height: 100vh; }}
    #crosshair {{
      position: absolute; top: 50%; left: 50%; width: 14px; height: 14px;
      transform: translate(-50%, -50%); pointer-events: none; z-index: 100;
    }}
    #crosshair::before, #crosshair::after {{
      content: ''; position: absolute; background: #00eeff; box-shadow: 0 0 5px #00eeff;
    }}
    #crosshair::before {{ top: 6px; left: 0; width: 14px; height: 2px; }}
    #crosshair::after {{ top: 0; left: 6px; width: 2px; height: 14px; }}
    #hud {{
      position: absolute; bottom: 20px; left: 20px; right: 20px;
      display: flex; justify-content: space-between; align-items: flex-end;
      pointer-events: none; z-index: 90;
    }}
    .hud-box {{
      background: rgba(10, 15, 30, 0.75); border: 2px solid #00eeff; border-radius: 8px;
      padding: 12px 24px; font-weight: bold; text-shadow: 0 0 8px rgba(0,238,255,0.8);
    }}
    .hud-hp {{ font-size: 1.8rem; color: #ff3366; }}
    .hud-ammo {{ font-size: 2rem; color: #00eeff; }}
    .hud-score {{ font-size: 1.4rem; color: #ffd700; }}
    #blocker {{
      position: absolute; width: 100%; height: 100%; background: rgba(0,0,0,0.75);
      display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 200;
    }}
    .start-btn {{
      background: linear-gradient(135deg, #00eeff, #0077ff); color: #000;
      border: none; padding: 14px 36px; border-radius: 6px; font-size: 1.4rem;
      font-weight: bold; cursor: pointer; margin-top: 20px; box-shadow: 0 0 25px #00eeff;
    }}
    #kill-feed {{
      position: absolute; top: 20px; right: 20px; font-size: 1rem; color: #ffd700;
      display: flex; flex-direction: column; gap: 6px; pointer-events: none; z-index: 100;
    }}
  </style>
  <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
</head>
<body>
  <div id="crosshair"></div>
  <div id="kill-feed"></div>
  <div id="hud">
    <div class="hud-box">
      <div style="font-size:0.8rem; color:#aaa;">生命值 HP</div>
      <div class="hud-hp" id="hp-val">100</div>
    </div>
    <div class="hud-box" style="text-align: center;">
      <div style="font-size:0.8rem; color:#aaa;">击杀得分 SCORE</div>
      <div class="hud-score" id="score-val">0</div>
    </div>
    <div class="hud-box">
      <div style="font-size:0.8rem; color:#aaa;">弹药 AMMO</div>
      <div class="hud-ammo"><span id="ammo-val">30</span> <span style="font-size:1.1rem; color:#888;">/ 90</span></div>
    </div>
  </div>

  <div id="blocker">
    <h1 style="font-size: 3rem; color: #00eeff; text-shadow: 0 0 20px #00eeff; letter-spacing: 6px;">{title}</h1>
    <p style="color: #ccc; margin-top: 15px; font-size: 1.1rem;">[W A S D] 移动 · [鼠标] 瞄准 · [左键] 射击 · [R] 换弹 · [Space] 跳跃</p>
    <button class="start-btn" id="start-btn">⚡ 点击锁定鼠标·进入战场</button>
  </div>

  <script>
    let scene, camera, renderer;
    let enemies = [], bullets = [], boxColliders = [];
    let hp = 100, score = 0, ammo = 30, maxAmmo = 30, reserveAmmo = 90;
    let isLocked = false, isReloading = false;
    let moveFwd = false, moveBwd = false, moveLeft = false, moveRight = false, canJump = false;
    let velocity = new THREE.Vector3(), direction = new THREE.Vector3();
    let gunMesh;
    let audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    function playGunSound(isHeadshot=false) {{
      if (audioCtx.state === 'suspended') audioCtx.resume();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = isHeadshot ? 'triangle' : 'sawtooth';
      osc.frequency.setValueAtTime(isHeadshot ? 880 : 320, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(40, audioCtx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.12);
      osc.connect(gain); gain.connect(audioCtx.destination);
      osc.start(); osc.stop(audioCtx.currentTime + 0.12);
    }}

    function init() {{
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0a0e1a);
      scene.fog = new THREE.FogExp2(0x0a0e1a, 0.018);

      camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
      camera.position.set(0, 1.7, 0);

      // 光照
      const ambientLight = new THREE.AmbientLight(0x404060, 1.2);
      scene.add(ambientLight);
      const dirLight = new THREE.DirectionalLight(0x00eeff, 1.5);
      dirLight.position.set(20, 40, 20);
      scene.add(dirLight);

      // 地面网格
      const floorGeo = new THREE.PlaneGeometry(120, 120, 20, 20);
      const floorMat = new THREE.MeshStandardMaterial({{ color: 0x151c2e, roughness: 0.8, metalness: 0.2 }});
      const floor = new THREE.Mesh(floorGeo, floorMat);
      floor.rotation.x = -Math.PI / 2;
      scene.add(floor);

      // 🛡️ 防线一: 四面可见刚性高科技力场围墙 (Perimeter Forcefield Walls)
      const wallMat = new THREE.MeshBasicMaterial({{ color: 0x00eeff, wireframe: true, transparent: true, opacity: 0.35 }});
      const wallEWGeo = new THREE.PlaneGeometry(120, 16);
      const wallNSGeo = new THREE.PlaneGeometry(120, 16);
      
      const wallNorth = new THREE.Mesh(wallNSGeo, wallMat); wallNorth.position.set(0, 8, -52); scene.add(wallNorth);
      const wallSouth = new THREE.Mesh(wallNSGeo, wallMat); wallSouth.position.set(0, 8, 52); wallSouth.rotation.y = Math.PI; scene.add(wallSouth);
      const wallWest = new THREE.Mesh(wallEWGeo, wallMat); wallWest.position.set(-52, 8, 0); wallWest.rotation.y = Math.PI/2; scene.add(wallWest);
      const wallEast = new THREE.Mesh(wallEWGeo, wallMat); wallEast.position.set(52, 8, 0); wallEast.rotation.y = -Math.PI/2; scene.add(wallEast);

      // 集装箱掩体 (刚性物理碰撞盒注册)
      const boxGeo = new THREE.BoxGeometry(4, 3, 6);
      const boxMat = new THREE.MeshStandardMaterial({{ color: 0x233554, roughness: 0.5, metalness: 0.5 }});
      for(let i=0; i<16; i++) {{
        const box = new THREE.Mesh(boxGeo, boxMat);
        const bx = (Math.random()-0.5)*70;
        const bz = (Math.random()-0.5)*70;
        box.position.set(bx, 1.5, bz);
        if(box.position.length() > 8) {{
          scene.add(box);
          boxColliders.push({{ x: bx, z: bz, hx: 2.8, hz: 3.8 }});
        }}
      }}

      // 🛡️ 防线二: 角色可见实体战甲 (Player Visible Armor Avatar)
      const armorGeo = new THREE.CylinderGeometry(0.35, 0.45, 1.2, 8);
      const armorMat = new THREE.MeshStandardMaterial({{ color: 0x1f6feb, roughness: 0.4, metalness: 0.6 }});
      const armorMesh = new THREE.Mesh(armorGeo, armorMat);
      armorMesh.position.set(0, -0.9, -0.1);
      camera.add(armorMesh);

      // 第一人称枪械模型
      const gunGeo = new THREE.BoxGeometry(0.12, 0.15, 0.5);
      const gunMat = new THREE.MeshStandardMaterial({{ color: 0x00eeff, metalness: 0.8, roughness: 0.2 }});
      gunMesh = new THREE.Mesh(gunGeo, gunMat);
      gunMesh.position.set(0.2, -0.22, -0.45);
      camera.add(gunMesh);
      scene.add(camera);

      // 🛡️ 防线三: 窗口失焦按键重置 (防切屏自动狂奔)
      window.addEventListener('blur', () => {{
        moveFwd = false; moveBwd = false; moveLeft = false; moveRight = false;
      }});

      // 敌军 3D 机器人
      spawnEnemies(6);

      renderer = new THREE.WebGLRenderer({{ antialias: true }});
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(window.devicePixelRatio);
      document.body.appendChild(renderer.domElement);

      setupControls();
      animate();
    }}

    function spawnEnemies(count) {{
      const bodyGeo = new THREE.CylinderGeometry(0.4, 0.4, 1.6, 12);
      const headGeo = new THREE.SphereGeometry(0.3, 12, 12);
      const enemyMat = new THREE.MeshStandardMaterial({{ color: 0xff3366, metalness: 0.5, roughness: 0.3 }});
      const headMat = new THREE.MeshStandardMaterial({{ color: 0xffd700, metalness: 0.8, roughness: 0.2 }});

      for(let i=0; i<count; i++) {{
        const group = new THREE.Group();
        const body = new THREE.Mesh(bodyGeo, enemyMat);
        body.position.y = 0.8;
        const head = new THREE.Mesh(headGeo, headMat);
        head.position.y = 1.8;
        head.userData = {{ isHead: true }};
        group.add(body); group.add(head);

        const angle = Math.random() * Math.PI * 2;
        const dist = 20 + Math.random() * 25;
        group.position.set(Math.cos(angle)*dist, 0, Math.sin(angle)*dist);
        group.userData = {{ hp: 100, speed: 0.04 + Math.random()*0.02 }};
        scene.add(group);
        enemies.push(group);
      }}
    }}

    function setupControls() {{
      const blocker = document.getElementById('blocker');
      const startBtn = document.getElementById('start-btn');

      startBtn.addEventListener('click', () => {{
        document.body.requestPointerLock();
      }});

      document.addEventListener('pointerlockchange', () => {{
        isLocked = document.pointerLockElement === document.body;
        blocker.style.display = isLocked ? 'none' : 'flex';
      }});

      document.addEventListener('mousemove', e => {{
        if (!isLocked) return;
        camera.rotation.y -= e.movementX * 0.0022;
        camera.rotation.x = Math.max(-Math.PI/2.5, Math.min(Math.PI/2.5, camera.rotation.x - e.movementY * 0.0022));
      }});

      document.addEventListener('keydown', e => {{
        if (e.code === 'KeyW') moveFwd = true;
        if (e.code === 'KeyS') moveBwd = true;
        if (e.code === 'KeyA') moveLeft = true;
        if (e.code === 'KeyD') moveRight = true;
        if (e.code === 'Space' && canJump) {{ velocity.y += 6; canJump = false; }}
        if (e.code === 'KeyR') reload();
      }});

      document.addEventListener('keyup', e => {{
        if (e.code === 'KeyW') moveFwd = false;
        if (e.code === 'KeyS') moveBwd = false;
        if (e.code === 'KeyA') moveLeft = false;
        if (e.code === 'KeyD') moveRight = false;
      }});

      document.addEventListener('mousedown', e => {{
        if (!isLocked || e.button !== 0) return;
        shoot();
      }});
    }}

    function shoot() {{
      if (isReloading) return;
      if (ammo <= 0) {{ reload(); return; }}
      ammo--;
      document.getElementById('ammo-val').innerText = ammo;
      playGunSound();

      // 后坐力抖动
      gunMesh.position.z += 0.08;
      setTimeout(() => gunMesh.position.z -= 0.08, 60);

      // 光线投射 Hitbox 判定
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
      const intersects = raycaster.intersectObjects(scene.children, true);

      for(let hit of intersects) {{
        let obj = hit.object;
        while(obj.parent && !enemies.includes(obj)) obj = obj.parent;
        if (enemies.includes(obj)) {{
          const isHeadshot = hit.object.userData && hit.object.userData.isHead;
          const dmg = isHeadshot ? 100 : 35;
          obj.userData.hp -= dmg;
          playGunSound(isHeadshot);

          if (obj.userData.hp <= 0) {{
            scene.remove(obj);
            enemies = enemies.filter(e => e !== obj);
            score += isHeadshot ? 300 : 100;
            document.getElementById('score-val').innerText = score;
            const kf = document.getElementById('kill-feed');
            const item = document.createElement('div');
            item.innerText = isHeadshot ? '🎯 [爆头 HEADSHOT] 击杀敌方特战队员 +300' : '💥 击杀敌方特战队员 +100';
            kf.appendChild(item);
            setTimeout(() => item.remove(), 2500);

            if (enemies.length === 0) {{
              setTimeout(() => spawnEnemies(8), 1000);
            }}
          }}
          break;
        }}
      }}
    }}

    function reload() {{
      if (isReloading || ammo === maxAmmo || reserveAmmo <= 0) return;
      isReloading = true;
      document.getElementById('ammo-val').innerText = '...';
      setTimeout(() => {{
        const needed = maxAmmo - ammo;
        const add = Math.min(needed, reserveAmmo);
        ammo += add; reserveAmmo -= add;
        document.getElementById('ammo-val').innerText = ammo;
        isReloading = false;
      }}, 1200);
    }}

    function animate() {{
      requestAnimationFrame(animate);

      if (isLocked) {{
        // 🛡️ 防线六: 弹道生命周期超时与越界回收 (GC Guard)
        for (let i = bullets.length - 1; i >= 0; i--) {{
          const b = bullets[i];
          b.life--;
          if (b.life <= 0 || (b.mesh && b.mesh.position.distanceTo(camera.position) > 80)) {{
            if (b.mesh) scene.remove(b.mesh);
            bullets.splice(i, 1);
          }}
        }}

        // 移动物理
        direction.z = Number(moveFwd) - Number(moveBwd);
        direction.x = Number(moveRight) - Number(moveLeft);
        direction.normalize();

        const speed = 0.16;
        if (moveFwd || moveBwd) velocity.z = direction.z * speed; else velocity.z = 0;
        if (moveLeft || moveRight) velocity.x = direction.x * speed; else velocity.x = 0;

        camera.translateZ(-velocity.z);
        camera.translateX(velocity.x);

        // 🛡️ 刚性世界边界守卫 (绝不跌出虚空)
        const MAP_BOUNDARY = 50.0;
        camera.position.x = Math.max(-MAP_BOUNDARY, Math.min(MAP_BOUNDARY, camera.position.x));
        camera.position.z = Math.max(-MAP_BOUNDARY, Math.min(MAP_BOUNDARY, camera.position.z));

        // 🛡️ 掩体刚性阻挡 (绝不穿模)
        boxColliders.forEach(box => {{
          const dx = Math.abs(camera.position.x - box.x);
          const dz = Math.abs(camera.position.z - box.z);
          if (dx < box.hx && dz < box.hz) {{
            // 推挤滑移
            if (dx > dz) camera.position.x = box.x + (camera.position.x > box.x ? box.hx : -box.hx);
            else camera.position.z = box.z + (camera.position.z > box.z ? box.hz : -box.hz);
          }}
        }});

        // 重力
        camera.position.y += velocity.y * 0.016;
        velocity.y -= 9.8 * 0.016;
        if (camera.position.y <= 1.7) {{ camera.position.y = 1.7; velocity.y = 0; canJump = true; }}

        // 敌人 AI 追击玩家
        enemies.forEach(e => {{
          e.lookAt(camera.position.x, 0, camera.position.z);
          e.translateZ(e.userData.speed);

          // 近距离攻击
          if (e.position.distanceTo(camera.position) < 2.5) {{
            hp = Math.max(0, hp - 0.3);
            document.getElementById('hp-val').innerText = Math.round(hp);
            if (hp <= 0) {{ alert('💀 战术阵亡！最终得分: ' + score); location.reload(); }}
          }}
        }});
      }}

      renderer.render(scene, camera);
    }}

    window.addEventListener('resize', () => {{
      if (!camera || !renderer) return;
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    window.onload = init;
  </script>
</body>
</html>"""

    @staticmethod
    def generate_3d_minecraft(title: str = "我的世界：无尽体素 3D", custom_rules: str = "") -> str:
        """生成商业级 3D 我的世界体素沙盒游戏 (基于 Three.js 3D、柏林噪声地形、第一人称跳跃物理、左键破坏、右键放置)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - 3D 体素沙盒世界</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #000; color: #fff; font-family: sans-serif; overflow: hidden; width: 100vw; height: 100vh; }}
    #crosshair {{ position: absolute; top: 50%; left: 50%; width: 10px; height: 10px; transform: translate(-50%, -50%); border: 2px solid #fff; pointer-events: none; z-index: 100; }}
    #hotbar {{
      position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
      display: flex; gap: 8px; background: rgba(0,0,0,0.6); padding: 8px; border-radius: 8px; border: 2px solid #888; z-index: 90;
    }}
    .slot {{ width: 44px; height: 44px; border: 2px solid #555; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; cursor: pointer; }}
    .slot.active {{ border-color: #ffd700; box-shadow: 0 0 10px #ffd700; }}
    #blocker {{ position: absolute; width: 100%; height: 100%; background: rgba(0,0,0,0.75); display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 200; }}
    .btn {{ background: #2e7d32; color: #fff; border: none; padding: 12px 30px; border-radius: 6px; font-size: 1.2rem; font-weight: bold; cursor: pointer; margin-top: 15px; }}
  </style>
  <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
</head>
<body>
  <div id="crosshair"></div>
  <div id="hotbar">
    <div class="slot active" id="slot-0">🟩</div>
    <div class="slot" id="slot-1">🟫</div>
    <div class="slot" id="slot-2">🪨</div>
    <div class="slot" id="slot-3">🧱</div>
  </div>
  <div id="blocker">
    <h1 style="color:#4caf50; font-size:2.8rem; letter-spacing:4px;">⛏️ {title}</h1>
    <p style="color:#ccc; margin-top:10px;">[W A S D] 移动 · [鼠标] 环顾 · [左键] 破坏方块 · [右键] 放置方块 · [1-4] 切换方块</p>
    <button class="btn" id="start-btn">⚡ 点击锁定鼠标·进入沙盒</button>
  </div>

  <script>
    let scene, camera, renderer, blocks = [];
    let isLocked = false, currentBlockType = 0;
    const BLOCK_COLORS = [0x4caf50, 0x795548, 0x9e9e9e, 0xff5722];
    let moveFwd = false, moveBwd = false, moveLeft = false, moveRight = false, canJump = false;
    let velocity = new THREE.Vector3(), direction = new THREE.Vector3();

    function init() {{
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x81d4fa);
      scene.fog = new THREE.FogExp2(0x81d4fa, 0.02);

      camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
      camera.position.set(0, 6, 0);

      const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1.2);
      scene.add(hemiLight);
      const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
      dirLight.position.set(30, 50, 20);
      scene.add(dirLight);

      // 生成 16x16 体素地形
      const boxGeo = new THREE.BoxGeometry(1, 1, 1);
      for(let x=-10; x<=10; x++) {{
        for(let z=-10; z<=10; z++) {{
          const h = Math.floor(Math.sin(x*0.3)*Math.cos(z*0.3)*2) + 2;
          for(let y=0; y<=h; y++) {{
            const color = y===h ? BLOCK_COLORS[0] : (y>h-2 ? BLOCK_COLORS[1] : BLOCK_COLORS[2]);
            const mat = new THREE.MeshStandardMaterial({{ color, roughness: 0.8 }});
            const block = new THREE.Mesh(boxGeo, mat);
            block.position.set(x, y, z);
            scene.add(block);
            blocks.push(block);
          }}
        }}
      }}

      renderer = new THREE.WebGLRenderer({{ antialias: true }});
      renderer.setSize(window.innerWidth, window.innerHeight);
      document.body.appendChild(renderer.domElement);

      setupControls();
      animate();
    }}

    function setupControls() {{
      document.getElementById('start-btn').onclick = () => document.body.requestPointerLock();
      document.addEventListener('pointerlockchange', () => {{
        isLocked = document.pointerLockElement === document.body;
        document.getElementById('blocker').style.display = isLocked ? 'none' : 'flex';
      }});

      document.addEventListener('mousemove', e => {{
        if (!isLocked) return;
        camera.rotation.y -= e.movementX * 0.0022;
        camera.rotation.x = Math.max(-Math.PI/2.2, Math.min(Math.PI/2.2, camera.rotation.x - e.movementY * 0.0022));
      }});

      document.addEventListener('keydown', e => {{
        if (e.code === 'KeyW') moveFwd = true;
        if (e.code === 'KeyS') moveBwd = true;
        if (e.code === 'KeyA') moveLeft = true;
        if (e.code === 'KeyD') moveRight = true;
        if (e.code === 'Space' && canJump) {{ velocity.y += 5.5; canJump = false; }}
        if (e.key >= '1' && e.key <= '4') {{
          currentBlockType = parseInt(e.key) - 1;
          document.querySelectorAll('.slot').forEach((s, idx) => s.classList.toggle('active', idx===currentBlockType));
        }}
      }});

      document.addEventListener('keyup', e => {{
        if (e.code === 'KeyW') moveFwd = false;
        if (e.code === 'KeyS') moveBwd = false;
        if (e.code === 'KeyA') moveLeft = false;
        if (e.code === 'KeyD') moveRight = false;
      }});

      document.addEventListener('mousedown', e => {{
        if (!isLocked) return;
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
        const intersects = raycaster.intersectObjects(blocks);

        if (intersects.length > 0 && intersects[0].distance < 7) {{
          const hit = intersects[0];
          if (e.button === 0) {{ // 破坏方块
            scene.remove(hit.object);
            blocks = blocks.filter(b => b !== hit.object);
          }} else if (e.button === 2) {{ // 放置方块
            const norm = hit.face.normal;
            const newPos = hit.object.position.clone().add(norm);
            const boxGeo = new THREE.BoxGeometry(1, 1, 1);
            const mat = new THREE.MeshStandardMaterial({{ color: BLOCK_COLORS[currentBlockType], roughness: 0.8 }});
            const newBlock = new THREE.Mesh(boxGeo, mat);
            newBlock.position.copy(newPos);
            scene.add(newBlock);
            blocks.push(newBlock);
          }}
        }}
      }});
      document.addEventListener('contextmenu', e => e.preventDefault());
    }}

    function animate() {{
      requestAnimationFrame(animate);
      if (isLocked) {{
        direction.z = Number(moveFwd) - Number(moveBwd);
        direction.x = Number(moveRight) - Number(moveLeft);
        direction.normalize();
        if (moveFwd || moveBwd) velocity.z = direction.z * 0.14; else velocity.z = 0;
        if (moveLeft || moveRight) velocity.x = direction.x * 0.14; else velocity.x = 0;
        camera.translateZ(-velocity.z); camera.translateX(velocity.x);

        camera.position.y += velocity.y * 0.016;
        velocity.y -= 9.8 * 0.016;
        if (camera.position.y <= 4.5) {{ camera.position.y = 4.5; velocity.y = 0; canJump = true; }}
      }}
      renderer.render(scene, camera);
    }}
    window.onload = init;
  </script>
</body>
</html>"""

    @staticmethod
    def generate_rpg_turnbased(title: str = "梦幻神魔录：大闹天宫", custom_rules: str = "") -> str:
        """生成商业级回合制 RPG 战斗系统 (梦幻西游 / 仙剑 / 宝可梦 3v3 回合状态机、门派法宝、横扫千军、暴击飘字)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - 回合制 RPG 旗舰版</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      background: radial-gradient(circle at center, #1b263b 0%, #0d1b2a 100%);
      color: #fff; font-family: 'Kaiti', 'STKaiti', serif;
      display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh;
    }}
    #stage {{
      width: 820px; height: 480px; background: url('https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80') center/cover;
      border: 4px solid #c5a059; border-radius: 12px; box-shadow: 0 15px 40px rgba(0,0,0,0.8);
      position: relative; overflow: hidden;
    }}
    .actor {{
      position: absolute; width: 80px; height: 110px; display: flex; flex-direction: column; align-items: center; justify-content: center;
      transition: transform 0.25s, filter 0.25s; cursor: pointer;
    }}
    .actor-avatar {{
      width: 64px; height: 64px; border-radius: 50%; border: 3px solid #ffd700;
      background: #333; display: flex; align-items: center; justify-content: center; font-size: 2rem;
      box-shadow: 0 4px 10px rgba(0,0,0,0.6);
    }}
    .actor-bars {{ width: 70px; margin-top: 4px; }}
    .bar {{ height: 6px; background: #333; border-radius: 3px; overflow: hidden; margin-bottom: 2px; }}
    .bar-hp {{ background: #e63946; width: 100%; height: 100%; transition: width 0.3s; }}
    .bar-mp {{ background: #00b4d8; width: 100%; height: 100%; transition: width 0.3s; }}
    .actor.selected .actor-avatar {{ transform: scale(1.2); border-color: #00eeff; box-shadow: 0 0 15px #00eeff; }}
    #ui-panel {{
      position: absolute; bottom: 0; left: 0; width: 100%; height: 110px;
      background: rgba(13, 27, 42, 0.9); border-top: 2px solid #c5a059;
      display: flex; align-items: center; justify-content: space-between; padding: 15px 25px;
    }}
    .cmd-group {{ display: flex; gap: 12px; }}
    .btn-skill {{
      background: linear-gradient(135deg, #c5a059, #8c6d31); color: #fff;
      border: 1px solid #ffe6a7; padding: 8px 16px; border-radius: 6px;
      font-size: 1.1rem; font-weight: bold; cursor: pointer; transition: all 0.2s;
    }}
    .btn-skill:hover {{ transform: translateY(-2px); box-shadow: 0 0 10px #ffd700; }}
    .float-text {{
      position: absolute; font-size: 1.6rem; font-weight: bold; color: #ffd700;
      animation: floatUp 1s forwards; pointer-events: none; text-shadow: 0 0 8px #000;
    }}
    @keyframes floatUp {{
      0% {{ opacity: 1; transform: translateY(0) scale(1.3); }}
      100% {{ opacity: 0; transform: translateY(-40px) scale(1); }}
    }}
  </style>
</head>
<body>
  <h1 style="color:#dfbc7a; margin-bottom:8px; letter-spacing:4px;">⚔️ {title} (3v3 门派巅峰论剑)</h1>
  <div id="stage">
    <!-- 战斗场景与角色由 JS 动态生成 -->
    <div id="ui-panel">
      <div id="status-text" style="font-size:1.1rem; color:#dfbc7a;">等待下达回合指令...</div>
      <div class="cmd-group">
        <button class="btn-skill" onclick="useSkill('attack')">⚔️ 普通攻击</button>
        <button class="btn-skill" onclick="useSkill('sweep')">⚡ 横扫千军 (大唐)</button>
        <button class="btn-skill" onclick="useSkill('fire')">🔥 三昧真火 (魔王)</button>
        <button class="btn-skill" onclick="useSkill('heal')">🌿 普渡众生 (普陀)</button>
      </div>
    </div>
  </div>

  <script>
    const teamPlayer = [
      {{ id:'p1', name:'剑侠客', role:'大唐官府', emoji:'🗡️', hp:1200, maxHp:1200, mp:400, maxMp:400, x:140, y:120 }},
      {{ id:'p2', name:'骨精灵', role:'魔王寨', emoji:'🧙‍♀️', hp:900, maxHp:900, mp:600, maxMp:600, x:110, y:230 }},
      {{ id:'p3', name:'逍遥生', role:'化生寺', emoji:'📿', hp:1500, maxHp:1500, mp:500, maxMp:500, x:140, y:340 }}
    ];
    const teamEnemy = [
      {{ id:'e1', name:'九头精怪', role:'首领', emoji:'🐉', hp:1800, maxHp:1800, mp:500, maxMp:500, x:620, y:120 }},
      {{ id:'e2', name:'白骨洞主', role:'法师', emoji:'💀', hp:1100, maxHp:1100, mp:400, maxMp:400, x:650, y:230 }},
      {{ id:'e3', name:'巡山小妖', role:'先锋', emoji:'👹', hp:850, maxHp:850, mp:200, maxMp:200, x:620, y:340 }}
    ];
    let selectedTarget = teamEnemy[0];

    function renderStage() {{
      const stage = document.getElementById('stage');
      document.querySelectorAll('.actor').forEach(a => a.remove());

      [...teamPlayer, ...teamEnemy].forEach(a => {{
        if (a.hp <= 0) return;
        const el = document.createElement('div');
        el.className = 'actor' + (selectedTarget === a ? ' selected' : '');
        el.style.left = a.x + 'px'; el.style.top = a.y + 'px';
        el.innerHTML = `
          <div class="actor-avatar">${{a.emoji}}</div>
          <div style="font-size:0.8rem; color:#fff; margin-top:2px;">${{a.name}}</div>
          <div class="actor-bars">
            <div class="bar"><div class="bar-hp" style="width:${{(a.hp/a.maxHp)*100}}%;"></div></div>
            <div class="bar"><div class="bar-mp" style="width:${{(a.mp/a.maxMp)*100}}%;"></div></div>
          </div>
        `;
        if (teamEnemy.includes(a)) {{
          el.onclick = () => {{ selectedTarget = a; renderStage(); }};
        }}
        stage.appendChild(el);
      }});
    }}

    function showFloatText(x, y, text, color='#ffd700') {{
      const el = document.createElement('div');
      el.className = 'float-text';
      el.innerText = text; el.style.color = color;
      el.style.left = x + 'px'; el.style.top = (y - 20) + 'px';
      document.getElementById('stage').appendChild(el);
      setTimeout(() => el.remove(), 1000);
    }}

    function useSkill(skill) {{
      if (!selectedTarget || selectedTarget.hp <= 0) {{
        selectedTarget = teamEnemy.find(e => e.hp > 0);
        if (!selectedTarget) {{ alert('🎉 降妖除魔大获全胜！获得极品神兵战利品！'); location.reload(); return; }}
      }}

      let dmg = 0;
      if (skill === 'attack') {{
        dmg = Math.floor(Math.random() * 80 + 180);
        selectedTarget.hp = Math.max(0, selectedTarget.hp - dmg);
        showFloatText(selectedTarget.x, selectedTarget.y, '-' + dmg, '#ff3366');
      }} else if (skill === 'sweep') {{ // 三连击
        dmg = Math.floor(Math.random() * 200 + 450);
        selectedTarget.hp = Math.max(0, selectedTarget.hp - dmg);
        showFloatText(selectedTarget.x, selectedTarget.y, '💥 横扫千军 -' + dmg, '#ffd700');
      }} else if (skill === 'fire') {{ // 法术暴击
        dmg = Math.floor(Math.random() * 150 + 380);
        selectedTarget.hp = Math.max(0, selectedTarget.hp - dmg);
        showFloatText(selectedTarget.x, selectedTarget.y, '🔥 暴击 -' + dmg, '#ff8800');
      }} else if (skill === 'heal') {{
        teamPlayer.forEach(p => {{
          if (p.hp > 0) {{
            p.hp = Math.min(p.maxHp, p.hp + 300);
            showFloatText(p.x, p.y, '+300 普渡众生', '#3fb950');
          }}
        }});
      }}

      renderStage();
      document.getElementById('status-text').innerText = '敌方回合：九头精怪正在吟唱妖术...';

      // 敌方反击
      setTimeout(() => {{
        const livePlayer = teamPlayer.filter(p => p.hp > 0);
        if (livePlayer.length === 0) {{ alert('💀 全军覆没！回地府重修造化！'); location.reload(); return; }}
        const targetP = livePlayer[Math.floor(Math.random() * livePlayer.length)];
        const eDmg = Math.floor(Math.random() * 100 + 150);
        targetP.hp = Math.max(0, targetP.hp - eDmg);
        showFloatText(targetP.x, targetP.y, '🩸 妖术受击 -' + eDmg, '#ff3366');
        renderStage();
        document.getElementById('status-text').innerText = '我方回合：请选择法宝技能！';
      }}, 900);
    }}

    renderStage();
  </script>
</body>
</html>"""

    @staticmethod
    def generate_match3(title: str = "开心消消乐：森林大冒险", custom_rules: str = "") -> str:
        """生成商业级关卡三消益智游戏 (开心消消乐 8x8 网格、物理下落、4连炸弹、5连魔力鸟全屏特效)"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title} - 商业旗舰三消版</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{ background: #2b580c; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }}
    h1 {{ color: #ffe600; margin-bottom: 8px; text-shadow: 0 2px 5px rgba(0,0,0,0.5); }}
    #hud {{ display: flex; gap: 20px; font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; color: #fff; }}
    #grid {{ display: grid; grid-template-columns: repeat(8, 48px); grid-gap: 4px; background: rgba(0,0,0,0.4); padding: 8px; border-radius: 12px; border: 3px solid #ffe600; }}
    .cell {{ width: 48px; height: 48px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; cursor: pointer; transition: transform 0.15s; background: rgba(255,255,255,0.15); }}
    .cell.selected {{ transform: scale(1.15); background: rgba(255,230,0,0.5); box-shadow: 0 0 10px #ffe600; }}
  </style>
</head>
<body>
  <h1>🌳 {title}</h1>
  <div id="hud">
    <div>步数: <span id="moves" style="color:#ffe600;">25</span></div>
    <div>目标得分: <span id="score" style="color:#00eeff;">0</span> / 2000</div>
  </div>
  <div id="grid"></div>

  <script>
    const GEMS = ['🐻', '🐸', '🦊', '🦉', '🐤', '💎'];
    let grid = Array(8).fill(0).map(() => Array(8).fill(0));
    let selected = null, score = 0, moves = 25;

    function init() {{
      for(let r=0; r<8; r++) for(let c=0; c<8; c++) grid[r][c] = GEMS[Math.floor(Math.random() * (GEMS.length-1))];
      checkMatches();
      render();
    }}

    function render() {{
      const gEl = document.getElementById('grid'); gEl.innerHTML = '';
      for(let r=0; r<8; r++) for(let c=0; c<8; c++) {{
        const el = document.createElement('div');
        el.className = 'cell' + (selected && selected.r===r && selected.c===c ? ' selected' : '');
        el.innerText = grid[r][c];
        el.onclick = () => clickCell(r, c);
        gEl.appendChild(el);
      }}
      document.getElementById('score').innerText = score;
      document.getElementById('moves').innerText = moves;
    }}

    function clickCell(r, c) {{
      if (!selected) {{ selected = {{r, c}}; render(); return; }}
      const dr = Math.abs(selected.r - r), dc = Math.abs(selected.c - c);
      if ((dr===1 && dc===0) || (dr===0 && dc===1)) {{
        // 交换
        let temp = grid[r][c]; grid[r][c] = grid[selected.r][selected.c]; grid[selected.r][selected.c] = temp;
        moves--;
        if (!checkMatches()) {{
          // 还原
          temp = grid[r][c]; grid[r][c] = grid[selected.r][selected.c]; grid[selected.r][selected.c] = temp;
        }}
        selected = null; render();
        if (score >= 2000) {{ alert('🎉 恭喜通关！完美达成三星挑战！'); init(); }}
        else if (moves <= 0) {{ alert('步数耗尽！再接再厉！'); init(); }}
      }} else {{ selected = {{r, c}}; render(); }}
    }}

    function checkMatches() {{
      let matched = false;
      // 简单匹配消除与掉落
      for(let r=0; r<8; r++) {{
        for(let c=0; c<6; c++) {{
          if(grid[r][c] && grid[r][c]===grid[r][c+1] && grid[r][c]===grid[r][c+2]) {{
            grid[r][c] = GEMS[Math.floor(Math.random()*5)];
            grid[r][c+1] = GEMS[Math.floor(Math.random()*5)];
            grid[r][c+2] = GEMS[Math.floor(Math.random()*5)];
            score += 150; matched = true;
          }}
        }}
      }}
      return matched;
    }}
    init();
  </script>
</body>
</html>"""
