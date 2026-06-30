"""
坦克大战 — Classic Tank Battle (Battle City style)

  KEY1-4: ↑↓←→ 移动 (直控四方向)
  SWITCH: 暂停 (ON) / 继续 (OFF)
  KEY5:   退出
  自动射击 (无需按键)
  编码器: 选择坦克变体 + 按下确认

  5 关递增难度, 保护基地, 消灭全部敌人过关.

  渲染: numpy 帧缓冲 + push_frame (~7 FPS)
  依赖: numpy
"""

import os, pathlib, time, math, random
from dataclasses import dataclass
from collections import deque

from vckb.apps.base import AppDefinition

APP = AppDefinition(
    id="tank_battle",
    name="Tank Battle",
    name_zh="坦克大战",
    description="Classic tank battle — 5 levels, protect the base, auto-fire",
    icon="🔫",
    category="game",
    controls={
        "KEY1": "上移 ↑",
        "KEY2": "下移 ↓",
        "KEY3": "左移 ←",
        "KEY4": "右移 →",
        "SWITCH": "暂停 / 继续",
        "KEY5": "退出",
        "编码器": "选择坦克 (select界面)",
        "编码器BTN": "确认选择",
    },
    module="vckb.apps.tank_battle",
    requires=["numpy"],
)

# ═══════════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════════
DISPLAY_W, DISPLAY_H = 320, 240
TOP_H = 16
GAME_Y0 = TOP_H                    # 16
GAME_H  = DISPLAY_H - TOP_H        # 224
COLS, ROWS = 20, 14
CELL = 16                          # px/格
RENDER_INTERVAL = 0.15             # ~6.7 FPS (匹配 USB FS 带宽)
TICKS_PER_FRAME = 3                # 每帧游戏逻辑 tick 数
BULLET_SPEED = 5                   # px/tick

# 方向: 0=↑ 1=→ 2=↓ 3=←
DIR_DXY = [(0, -1), (1, 0), (0, 1), (-1, 0)]
DIR_KEYS = ['up', 'right', 'down', 'left']  # 对应 keys_held

# ═══════════════════════════════════════════════════════════
# 坦克变体
# ═══════════════════════════════════════════════════════════
VARIANTS = [
    {'id': 'balanced', 'name': 'BALANCED', 'color': 0x07E0, 'cannon': 0x07FF,
     'speed': 2.0, 'lives': 3, 'max_bullets': 1, 'fire_s': 0.50,  'icon': '[:]'},
    {'id': 'swift',    'name': 'SWIFT',    'color': 0xFFE0, 'cannon': 0xFE80,
     'speed': 3.0, 'lives': 2, 'max_bullets': 1, 'fire_s': 0.35,  'icon': '[:>'},
    {'id': 'tank',     'name': 'TANK',     'color': 0x07FF, 'cannon': 0x063F,
     'speed': 1.5, 'lives': 4, 'max_bullets': 2, 'fire_s': 0.50,  'icon': '[:D'},
]

# ═══════════════════════════════════════════════════════════
# 关卡配置
# ═══════════════════════════════════════════════════════════
LEVEL_CFG = [
    {'enemies': 3, 'espeed': 1.0},   # LV1
    {'enemies': 4, 'espeed': 1.2},   # LV2
    {'enemies': 5, 'espeed': 1.4},   # LV3
    {'enemies': 6, 'espeed': 1.6},   # LV4
    {'enemies': 7, 'espeed': 1.8},   # LV5
]

# 地图 (14×20): . = 空地  B = 砖墙  S = 钢墙  W = 水域  T = 树丛
# 基地固定在底部中央 (col 9-10, row 12-13), 钢墙包围在 map 中体现
_MAP_DATA = [
    # LV1 — 练手: 开阔, 少量砖墙
    ["....................",
     "....................",
     "....................",
     "......BB..BB........",
     "......BB..BB........",
     "....................",
     "..BB..........BB....",
     "..BB..........BB....",
     "....................",
     "......BB..BB........",
     "......BB..BB........",
     "...SS........SS.....",
     "...S............S...",
     "...S....BASE....S..."],
    # LV2 — 迷宫入门: 对称砖墙, 水域
    ["....................",
     "........BB..........",
     ".....BB..BB.BB......",
     "...BB........BB.....",
     "...B..WW..WW..B.....",
     ".......W..W.........",
     "..BB........BB......",
     "...B..........B.....",
     ".....BBBBBBBB.......",
     "....................",
     "..BB..........BB....",
     "...SS........SS.....",
     "...S............S...",
     "...S....BASE....S..."],
    # LV3 — 对称布局: 多砖墙, 钢墙增加
    [".......BB.BB........",
     "..B....B..B.....B...",
     "..B..BB....BB..B....",
     "...BB........BB.....",
     "....B..WWWW..B......",
     "..BB............BB..",
     "..B..............B..",
     "...B..SS..SS..B.....",
     "....B..........B....",
     ".....BB......BB.....",
     "..BB....BB....BB....",
     "..SSS..........SSS..",
     "..S....S....S....S..",
     "...S....BASE....S..."],
    # LV4 — 复杂通道: 水域 + 钢墙 + 砖墙
    ["....B..........B....",
     "...B.B........B.B...",
     "..B...B..SS..B...B..",
     ".B.....B....B.....B.",
     ".B..W....BB....W..B.",
     "....W...B..B...W....",
     ".B..W........W...B..",
     "..B...SS....SS...B..",
     "...B............B...",
     "....B..BBBBBB..B....",
     ".....B........B.....",
     "..SS..B..BB..B..SS..",
     "..S......BB......S..",
     "...S....BASE....S..."],
    # LV5 — 最终关: 高密度, 全方位
    ["..BB..........BB....",
     ".B..B..BBBB..B..B...",
     ".B..SS......SS..B...",
     "..B..............B..",
     "..B..B..SS..B...B...",
     "...BB.W....W.BBB....",
     ".....W.W..W.W.......",
     "..B.....BB.....B....",
     ".B..B........B..B...",
     "..B..B..BB..B..B....",
     "...BB........BB.....",
     "..SSS..SSSS...SSS...",
     "..S....S..S....S....",
     "...S....BASE....S..."],
]

# 解析地图: 字符 → 单元格类型 0=空地 1=砖墙 2=钢墙 3=水域 4=树丛
_MAP_CHAR = {'.': 0, 'B': 1, 'S': 2, 'W': 3, 'T': 4}
# 单元格颜色 (原始 RGB565 — 走 push_frame 时自动补偿 INVON)
_CELL_COLOR = {1: 0xFC40, 2: 0x8410, 3: 0x001F, 4: 0x07E0}
BASE_COLOR = 0xFFE0       # 基地 (黄色)
BULLET_COLOR = 0xFFFF     # 子弹 (白色)
EXPLOSION_COLORS = [0xFFFF, 0xFFE0, 0xF800, 0x0000]  # 爆炸帧: 白→黄→红→黑


def _parse_map(strs):
    """字符串地图 → 14×20 int 数组"""
    grid = [[0] * COLS for _ in range(ROWS)]
    for r, line in enumerate(strs):
        for c, ch in enumerate(line):
            if ch in _MAP_CHAR:
                grid[r][c] = _MAP_CHAR[ch]
    return grid


MAPS = [_parse_map(m) for m in _MAP_DATA]

# ═══════════════════════════════════════════════════════════
# 游戏对象
# ═══════════════════════════════════════════════════════════

@dataclass
class Bullet:
    x: float; y: float; direction: int; owner: str  # 'player'|'enemy'
    alive: bool = True


@dataclass
class Explosion:
    x: float; y: float; frame: int  # 倒计时帧数 (4→0, 每帧递减)
    big: bool = False               # 大爆炸 (坦克) / 小火花 (钢墙)


# ═══════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════

def main():
    import numpy as np
    from vckb import VCKeyboard

    stop_signal = os.environ.get("VCKB_STOP_SIGNAL", "")

    def inv(c):
        """固件命令路径不补偿 INVON: 发送 ~c 显示 c"""
        return (~c) & 0xFFFF

    with VCKeyboard() as kb:
        kb.fill(inv(0x0000))

        # ── 输入状态 ──
        keys_held = set()         # {'up','down','left','right'}
        switch_on = False
        enc_select = 0            # select 界面选中的坦克索引
        enc_confirmed = False     # 编码器 BTN 按下
        enc_input = deque()       # ('cw',n) | ('ccw',n) | ('btn',)
        running = True

        @kb.on_key("KEY1", "down")
        def _k1d(): keys_held.add('up')
        @kb.on_key("KEY1", "up")
        def _k1u(): keys_held.discard('up')
        @kb.on_key("KEY2", "down")
        def _k2d(): keys_held.add('down')
        @kb.on_key("KEY2", "up")
        def _k2u(): keys_held.discard('down')
        @kb.on_key("KEY3", "down")
        def _k3d(): keys_held.add('left')
        @kb.on_key("KEY3", "up")
        def _k3u(): keys_held.discard('left')
        @kb.on_key("KEY4", "down")
        def _k4d(): keys_held.add('right')
        @kb.on_key("KEY4", "up")
        def _k4u(): keys_held.discard('right')
        @kb.on_key("KEY5", "down")
        def _k5d():
            nonlocal running; running = False

        @kb.on_switch()
        def _sw(state):
            nonlocal switch_on
            switch_on = (state == 'ON')

        @kb.on_encoder(divider=4)
        def _enc(action, steps):
            if action in ('cw', 'ccw'):
                enc_input.append((action, steps))
            elif action == 'btn':
                enc_input.append(('btn',))

        # ── 游戏状态 (main 作用域, 供 nonlocal) ──
        state = 'select'
        level = 1; score = 0; lives = 3
        enemies_left = 0
        px = 160.0; py = 216.0; pfacing = 0
        pfire_timer = 0.0; pmax_bullets = 1; pfire_interval = 0.50
        enemy_list = []; bullet_list = []; explosion_list = []
        game_map = [row[:] for row in MAPS[0]]
        enemy_spawn_queue = []; enemy_spawn_timer = 0.0
        prev_score = -1; prev_lives = -1; prev_enemies = -1
        last_tick = 0.0; last_render = 0.0
        ready_timer = 0.0
        prev_frame = None        # 差分推送: 上一帧缓存, None=需全量刷新

        # ── 坦克选择界面 ──
        def render_select():
            """编码器切换高亮, BTN 确认"""
            nonlocal enc_select, enc_confirmed
            n = len(VARIANTS)
            # 消费编码器输入
            while enc_input:
                ev = enc_input.popleft()
                if ev[0] == 'cw':
                    enc_select = (enc_select + 1) % n
                elif ev[0] == 'ccw':
                    enc_select = (enc_select - 1) % n
                elif ev[0] == 'btn':
                    enc_confirmed = True
                    return

            kb.fill(inv(0x0000))
            kb.text(20, 5, "SELECT YOUR TANK", size="M", color=inv(0xFFFF))
            kb.text(170, 9, "ENC=选择 BTN=确认", size="S", color=inv(0x7BEF))

            for i, v in enumerate(VARIANTS):
                y0 = 40 + i * 64
                sel = (i == enc_select)
                # 卡片背景
                kb.rect(30, y0, 260, 56, inv(0x2104) if sel else inv(0x1082))
                if sel:
                    kb.rect(28, y0 - 2, 264, 60, inv(0x07FF))  # 高亮框
                # 坦克色块预览
                kb.rect(45, y0 + 8, 36, 36, inv(v['color']))
                kb.rect(57, y0, 8, 12, inv(v['cannon']))       # 炮管
                # 名称
                kb.text(95, y0 + 4, v['name'], size="M",
                        color=inv(0xFFFF) if sel else inv(0xAD55))
                # 生命
                kb.text(95, y0 + 24, "♥" * v['lives'], size="S", color=inv(0xF800))
                # 属性
                info = f"Spd:{v['speed']:.1f}  "
                info += f"Fire:{v['fire_s']}s  "
                info += "1x" if v['max_bullets'] == 1 else "2x"
                kb.text(180, y0 + 24, info, size="S", color=inv(0x7BEF))

        # ── 游戏初始化 ──
        def init_game():
            """初始化/重置游戏状态"""
            nonlocal state, level, score, lives, enemies_left
            nonlocal px, py, pfacing, pfire_timer, pmax_bullets, pfire_interval
            nonlocal enemy_list, bullet_list, explosion_list
            nonlocal game_map, enemy_spawn_queue, enemy_spawn_timer
            nonlocal prev_score, prev_lives, prev_enemies
            nonlocal last_tick, last_render, ready_timer, prev_frame

            level = 1; score = 0
            v = VARIANTS[enc_select]
            lives = v['lives']
            pmax_bullets = v['max_bullets']
            pfire_interval = v['fire_s']

            game_map = [row[:] for row in MAPS[level - 1]]
            # 基地位置: col 9-10, row 12-13 → 像素 (144, 208) 32×32
            # 恢复/确保基地周围钢墙 (在地图中已预设 'S')
            # 确保基地格为空 (坦克可重生在此)
            for r in range(12, 14):
                for c in range(9, 11):
                    game_map[r][c] = 0  # 基地格清空 (图标单独画)

            # 玩家
            px, py = 160.0, 216.0       # 基地上方
            pfacing = 0                  # ↑
            pfire_timer = 0.0

            # 敌人
            enemy_list = []
            enemy_spawn_queue = []
            ecount = LEVEL_CFG[level - 1]['enemies']
            # 3个出生点轮流
            spawns = [(16, 16), (160, 16), (304, 16)]  # 像素坐标
            for i in range(ecount):
                sx, sy = spawns[i % 3]
                enemy_spawn_queue.append((sx + random.uniform(-8, 8), sy))
            enemy_spawn_timer = 0.0

            enemies_left = ecount
            bullet_list = []
            explosion_list = []

            state = 'ready'
            ready_timer = 0.0
            prev_frame = None        # 强制下帧全量刷新 (地图已切换)

            prev_score = -1; prev_lives = -1; prev_enemies = -1
            last_tick = 0.0; last_render = 0.0

        # ── 碰撞 / 工具 ──
        def is_solid(cell):
            return cell in (1, 2, 3)  # 砖/钢/水 → 坦克不可通过

        def tank_wall_collision(cx, cy):
            """坦克 14×14 bounding box 是否碰墙"""
            x0, y0 = int(cx - 7), int(cy - 7)
            x1, y1 = int(cx + 7), int(cy + 7)
            for yr in range(y0, y1 + 1, CELL):
                for xr in range(x0, x1 + 1, CELL):
                    c = yr // CELL
                    r = (yr - GAME_Y0) // CELL
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        cell = game_map[r][c]
                        if is_solid(cell):
                            # AABB 重叠检查
                            wx = c * CELL
                            wy = r * CELL + GAME_Y0
                            if not (x1 < wx or x0 > wx + CELL - 1 or
                                    y1 < wy or y0 > wy + CELL - 1):
                                return True
            # 边界
            if x0 < 0 or x1 >= DISPLAY_W or y0 < GAME_Y0 or y1 >= DISPLAY_H:
                return True
            return False

        def bullet_hit_cell(bx, by, bw=2, bh=4):
            """子弹 2×4 命中格 — 返回 (col, row) 或 None"""
            for r in range(ROWS):
                for c in range(COLS):
                    if game_map[r][c] in (0, 4):  # 空地/树丛 → 子弹通过
                        continue
                    wx = c * CELL
                    wy = r * CELL + GAME_Y0
                    if not (bx + bw < wx or bx > wx + CELL - 1 or
                            by + bh < wy or by > wy + CELL - 1):
                        return (c, r)
            # 边界外 → 消失
            if bx < 0 or bx + bw >= DISPLAY_W or by < GAME_Y0 or by + bh >= DISPLAY_H:
                return ('edge',)
            return None

        def bullet_hit_tank(bullet, cx, cy, size=14):
            """子弹是否命中坦克 AABB"""
            bw, bh = 2, 4
            bx0, by0 = bullet.x, bullet.y
            tx0, ty0 = cx - size // 2, cy - size // 2
            return not (bx0 + bw < tx0 or bx0 > tx0 + size - 1 or
                        by0 + bh < ty0 or by0 > ty0 + size - 1)

        # ── 游戏更新 ──
        def update_game():
            nonlocal px, py, pfacing, pfire_timer, lives, score, state
            nonlocal enemy_list, bullet_list, explosion_list
            nonlocal enemies_left, enemy_spawn_queue, enemy_spawn_timer
            nonlocal game_map

            dt = RENDER_INTERVAL / TICKS_PER_FRAME  # 每 tick 秒数
            cfg = LEVEL_CFG[level - 1]
            v = VARIANTS[enc_select]
            pspeed = v['speed']
            espeed = cfg['espeed']

            # ── 1. 移动玩家坦克 ──
            dx, dy = 0.0, 0.0
            move_keys = []
            if 'up' in keys_held:    dy -= 1; move_keys.append(0)
            if 'down' in keys_held:  dy += 1; move_keys.append(2)
            if 'left' in keys_held:  dx -= 1; move_keys.append(3)
            if 'right' in keys_held: dx += 1; move_keys.append(1)

            if dx != 0 or dy != 0:
                # 对角归一化
                if dx != 0 and dy != 0:
                    dx *= 0.707; dy *= 0.707
                new_x = px + dx * pspeed
                new_y = py + dy * pspeed
                # 分别检查 X / Y 碰撞 (滑墙)
                if not tank_wall_collision(new_x, py):
                    px = new_x
                if not tank_wall_collision(px, new_y):
                    py = new_y
                # 朝向: 使用最后按下的方向键
                pfacing = move_keys[-1] if move_keys else pfacing
                # 更新朝向用于自动射击
            # else: 朝向保持, 不移动

            # ── 2. 自动射击 ──
            pfire_timer += dt
            player_bullets = sum(1 for b in bullet_list if b.owner == 'player' and b.alive)
            if pfire_timer >= pfire_interval and player_bullets < pmax_bullets:
                pfire_timer = 0.0
                dxb, dyb = DIR_DXY[pfacing]
                # 子弹从炮管口发出
                bx = px + dxb * 9
                by = py + dyb * 9
                bullet_list.append(Bullet(bx, by, pfacing, 'player'))
                # 重新随机化射击间隔 (避免过于规整)
                pfire_timer = random.uniform(-0.05, 0.0)

            # ── 3. 移动子弹 ──
            for b in bullet_list:
                if not b.alive:
                    continue
                dxb, dyb = DIR_DXY[b.direction]
                b.x += dxb * BULLET_SPEED
                b.y += dyb * BULLET_SPEED

                hit = bullet_hit_cell(b.x, b.y)
                if hit:
                    if hit[0] == 'edge':
                        b.alive = False
                    else:
                        c, r = hit
                        cell = game_map[r][c]
                        if cell == 1:        # 砖墙 → 破坏
                            game_map[r][c] = 0
                            b.alive = False
                            explosion_list.append(
                                Explosion(c * CELL + 8, r * CELL + GAME_Y0 + 8, 3))
                        elif cell == 2:      # 钢墙 → 火花
                            b.alive = False
                            explosion_list.append(
                                Explosion(c * CELL + 8, r * CELL + GAME_Y0 + 8, 2, big=False))
                        elif cell == 3:      # 水域 → 子弹通过 (不消失)
                            pass
                    continue

                # 命中玩家坦克
                if b.owner == 'enemy' and bullet_hit_tank(b, px, py):
                    b.alive = False
                    explosion_list.append(Explosion(px, py, 4, big=True))
                    lives -= 1
                    if lives <= 0:
                        state = 'over'
                    else:
                        # 重生
                        px, py = 160.0, 216.0
                        pfacing = 0
                    continue

                # 命中敌人坦克
                if b.owner == 'player':
                    for e in enemy_list:
                        if e['alive'] and bullet_hit_tank(b, e['x'], e['y']):
                            b.alive = False
                            e['alive'] = False
                            explosion_list.append(Explosion(e['x'], e['y'], 4, big=True))
                            score += 10
                            enemies_left -= 1
                            if enemies_left == 0:
                                state = 'won'
                            break

                # 命中基地 (32×32 at 144, 208)
                if bullet_hit_tank(b, 160, 224, size=32):
                    b.alive = False
                    explosion_list.append(Explosion(160, 224, 6, big=True))
                    state = 'over'

            # 清理死子弹
            bullet_list = [b for b in bullet_list if b.alive]

            # ── 4. 子弹互抵 ──
            i = 0
            while i < len(bullet_list):
                j = i + 1
                while j < len(bullet_list):
                    bi, bj = bullet_list[i], bullet_list[j]
                    if bi.owner != bj.owner:
                        if abs(bi.x - bj.x) < 3 and abs(bi.y - bj.y) < 3:
                            bi.alive = False; bj.alive = False
                    j += 1
                i += 1
            bullet_list = [b for b in bullet_list if b.alive]

            # ── 5. 更新爆炸 ──
            for ex in explosion_list:
                ex.frame -= 1
            explosion_list = [e for e in explosion_list if e.frame >= 0]

            # ── 6. 敌人 AI ──
            for e in enemy_list:
                if not e['alive']:
                    continue
                e['dir_timer'] -= dt
                e['fire_timer'] -= dt

                if e['dir_timer'] <= 0:
                    e['direction'] = random.randint(0, 3)
                    e['dir_timer'] = random.uniform(0.4, 1.2)
                    # 简单追逐 (概率随关卡递增)
                    if level >= 3 and random.random() < 0.25:
                        # 朝玩家方向
                        if abs(e['x'] - px) > abs(e['y'] - py):
                            e['direction'] = 1 if px > e['x'] else 3
                        else:
                            e['direction'] = 2 if py > e['y'] else 0

                # 移动
                edx, edy = DIR_DXY[e['direction']]
                new_ex = e['x'] + edx * espeed
                new_ey = e['y'] + edy * espeed
                if not tank_wall_collision(new_ex, e['y']):
                    e['x'] = new_ex
                else:
                    e['dir_timer'] = 0  # 碰墙换方向
                if not tank_wall_collision(e['x'], new_ey):
                    e['y'] = new_ey
                else:
                    e['dir_timer'] = 0

                # 坦克互碰
                for e2 in enemy_list:
                    if e2 is e or not e2['alive']:
                        continue
                    if abs(e['x'] - e2['x']) < 16 and abs(e['y'] - e2['y']) < 16:
                        e['dir_timer'] = 0
                        e2['dir_timer'] = 0

                # 碰玩家
                if abs(e['x'] - px) < 16 and abs(e['y'] - py) < 16:
                    e['dir_timer'] = 0

                # 射击
                enemy_bullets = sum(1 for b in bullet_list if b.owner == 'enemy' and b.alive)
                if e['fire_timer'] <= 0 and enemy_bullets < 1:
                    e['fire_timer'] = random.uniform(1.0, 3.0)
                    edx2, edy2 = DIR_DXY[e['direction']]
                    bx = e['x'] + edx2 * 9
                    by = e['y'] + edy2 * 9
                    bullet_list.append(Bullet(bx, by, e['direction'], 'enemy'))

            # ── 7. 敌人生成 ──
            if enemy_spawn_queue:
                enemy_spawn_timer -= dt
                alive_enemies = sum(1 for e in enemy_list if e['alive'])
                if alive_enemies < 2 and enemy_spawn_timer <= 0:
                    sx, sy = enemy_spawn_queue.pop(0)
                    enemy_list.append({
                        'x': sx, 'y': sy,
                        'direction': 2,  # ↓
                        'dir_timer': random.uniform(0.3, 1.0),
                        'fire_timer': random.uniform(0.5, 2.0),
                        'alive': True,
                        'spawn_protect': 1.5,  # 出生保护 1.5s
                    })
                    enemy_spawn_timer = 0.8  # 下个敌人间隔

            # 出生保护倒计时
            for e in enemy_list:
                if e.get('spawn_protect', 0) > 0:
                    e['spawn_protect'] -= dt

        # ── 渲染 (游戏区) ──
        def render_game():
            """构建 224×320 numpy 帧缓冲 → 行差分 push_frame"""
            nonlocal prev_frame
            fb = np.zeros((GAME_H, DISPLAY_W), dtype='<u2')

            # 1. 水域
            for r in range(ROWS):
                for c in range(COLS):
                    if game_map[r][c] == 3:
                        y0 = r * CELL; x0 = c * CELL
                        fb[y0:y0 + CELL, x0:x0 + CELL] = _CELL_COLOR[3]

            # 2. 砖墙 + 钢墙
            for r in range(ROWS):
                for c in range(COLS):
                    cell = game_map[r][c]
                    if cell in (1, 2):
                        y0 = r * CELL; x0 = c * CELL
                        fb[y0:y0 + CELL, x0:x0 + CELL] = _CELL_COLOR[cell]

            # 3. 基地 (32×32 菱形/十字, 像素 144..175, 208..239)
            bx, by = 144 - GAME_Y0 + 1, 208 - GAME_Y0 + 1  # fb 坐标
            # 简化为黄色填充菱形
            base_px = 144; base_py = 208
            bbx0 = base_px; bby0 = base_py - GAME_Y0
            for dy in range(32):
                for dx in range(32):
                    if abs(dx - 16) + abs(dy - 16) < 15:
                        yy = bby0 + dy; xx = bbx0 + dx
                        if 0 <= yy < GAME_H and 0 <= xx < DISPLAY_W:
                            fb[yy, xx] = BASE_COLOR

            # 4. 子弹
            for b in bullet_list:
                bx, by = int(b.x), int(b.y - GAME_Y0)
                dxb, dyb = DIR_DXY[b.direction]
                # 沿方向画 2×4
                for i in range(4):
                    sx = int(b.x + dxb * i) - 1
                    sy = int(b.y + dyb * i - GAME_Y0) - 1
                    for ddx in range(2):
                        for ddy in range(2):
                            xx, yy = sx + ddx, sy + ddy
                            if 0 <= xx < DISPLAY_W and 0 <= yy < GAME_H:
                                fb[yy, xx] = BULLET_COLOR

            # 5. 坦克 (先敌人, 后玩家 — 玩家在上)
            def draw_tank(fb, cx, cy, direction, body_color, cannon_color,
                          flashing=False):
                """在帧缓冲中绘制坦克 (14×14 + 炮管)"""
                half = 7
                tx0 = int(cx - half); ty0 = int(cy - half - GAME_Y0)
                # 车身 12×10
                bx0 = int(cx - 5); by0 = int(cy - 5 - GAME_Y0)
                for dy in range(10):
                    for dx in range(12):
                        yy = by0 + dy; xx = bx0 + dx
                        if 0 <= yy < GAME_H and 0 <= xx < DISPLAY_W:
                            c = body_color
                            if flashing:
                                c = body_color if (int(time.time() * 10) % 2) else 0x0000
                            fb[yy, xx] = c
                # 炮管 (2×8, 沿方向)
                dxb, dyb = DIR_DXY[direction]
                for i in range(8):
                    sx = int(cx - 1 + dxb * (4 + i))
                    sy = int(cy - 1 + dyb * (4 + i) - GAME_Y0)
                    for ddx in range(2):
                        for ddy in range(2):
                            xx, yy = sx + ddx, sy + ddy
                            if 0 <= xx < DISPLAY_W and 0 <= yy < GAME_H:
                                fb[yy, xx] = cannon_color

            # 敌人坦克
            for e in enemy_list:
                if not e['alive']:
                    continue
                flash = e.get('spawn_protect', 0) > 0
                draw_tank(fb, e['x'], e['y'], e['direction'],
                          0xE820, 0xFC60, flashing=flash)

            # 玩家坦克
            v = VARIANTS[enc_select]
            draw_tank(fb, px, py, pfacing, v['color'], v['cannon'])

            # 6. 爆炸
            for ex in explosion_list:
                radius = (4 - ex.frame) * (6 if ex.big else 2) + 3
                color = EXPLOSION_COLORS[min(ex.frame, 3)]
                ex0 = int(ex.x - radius); ey0 = int(ex.y - radius - GAME_Y0)
                for dy in range(int(radius * 2)):
                    for dx in range(int(radius * 2)):
                        if (dx - radius) ** 2 + (dy - radius) ** 2 < radius ** 2:
                            xx, yy = ex0 + dx, ey0 + dy
                            if 0 <= xx < DISPLAY_W and 0 <= yy < GAME_H:
                                fb[yy, xx] = color

            # 7. 树丛 (最上层, 视觉遮挡)
            for r in range(ROWS):
                for c in range(COLS):
                    if game_map[r][c] == 4:
                        y0 = r * CELL; x0 = c * CELL
                        fb[y0:y0 + CELL, x0:x0 + CELL] = _CELL_COLOR[4]

            # ── 行差分推送: 只推变化区域, 静态背景不重传 ──
            if prev_frame is None:
                # 首帧 / 关卡切换: 全量推送
                kb.push_frame(0, GAME_Y0, DISPLAY_W, GAME_H, fb.tobytes())
                prev_frame = fb.copy()
            else:
                # 逐行比对 (numpy 向量化, ~μs 级)
                row_changed = np.any(fb != prev_frame, axis=1)
                if not row_changed.any():
                    # 无变化, 跳过渲染但仍保存帧 (下一帧比对用)
                    prev_frame = fb.copy()
                    return

                changed_idx = np.where(row_changed)[0]
                # 合并连续变化行为段
                runs = []
                seg_start = changed_idx[0]
                for i in range(1, len(changed_idx)):
                    if changed_idx[i] != changed_idx[i - 1] + 1:
                        runs.append((seg_start, changed_idx[i - 1] + 1))
                        seg_start = changed_idx[i]
                runs.append((seg_start, changed_idx[-1] + 1))

                for r0, r1 in runs:
                    # 在该行段内找最小/最大变化列 (缩小矩形宽度)
                    run_slice = fb[r0:r1, :]
                    prev_slice = prev_frame[r0:r1, :]
                    col_mask = np.any(run_slice != prev_slice, axis=0)
                    if not col_mask.any():
                        continue
                    c_idx = np.where(col_mask)[0]
                    c0, c1 = c_idx[0], c_idx[-1] + 1
                    seg_data = run_slice[:, c0:c1].tobytes()
                    if seg_data:
                        kb.push_frame(c0, GAME_Y0 + r0, c1 - c0, r1 - r0, seg_data)

                prev_frame = fb.copy()

        # ── HUD 顶栏 ──
        def draw_hud():
            kb.rect(0, 0, DISPLAY_W, TOP_H, inv(0x2104))
            kb.text(3, 3, "♥" * lives, size="S", color=inv(0xF800))
            kb.text(60, 3, f"SCORE:{score:05d}", size="S", color=inv(0xFFFF))
            kb.text(170, 3, f"LV{level}", size="S", color=inv(0x07FF))
            kb.text(220, 3, f"E:{enemies_left}", size="S", color=inv(0xFD20))

        # ── 状态覆盖文字 ──
        def overlay(msg, sub="", color=0xFFFF):
            yr = TOP_H + 2
            kb.rect(60, yr + 20, 200, 100, inv(0x0000))
            kb.text(70, yr + 40, msg, size="L", color=inv(color))
            if sub:
                kb.text(90, yr + 74, sub, size="M", color=inv(0xFFFF))

        # ── 主流程 ──
        # 初始 select 渲染
        render_select()

        while running:
            kb.poll(timeout=0.02)

            if stop_signal and pathlib.Path(stop_signal).exists():
                running = False; break

            now = time.time()

            # ── select 状态 ──
            if state == 'select':
                if enc_confirmed:
                    init_game()
                    state = 'ready'
                    ready_timer = 1.0
                    # 初始渲染
                    draw_hud()
                    render_game()
                    overlay(f"LEVEL {level}", "GET READY!", 0x07E0)
                    last_render = now
                    continue
                if enc_input:
                    render_select()
                continue

            # ── 暂停检查 ──
            if state == 'playing' and switch_on:
                state = 'paused'
                overlay("PAUSED", "SWITCH OFF = RESUME", 0xFFE0)
                continue
            elif state == 'paused' and not switch_on:
                state = 'playing'
                # 重绘
                draw_hud()
                render_game()
                last_render = now
                continue
            elif state == 'paused':
                continue  # 暂停中只 poll

            # ── ready 状态 ──
            if state == 'ready':
                ready_timer -= 0.02
                if ready_timer <= 0:
                    state = 'playing'
                    draw_hud()
                    render_game()
                    last_tick = now
                    last_render = now
                continue

            # ── won / over 状态 ──
            if state == 'won':
                overlay("YOU WIN!", f"Score: {score}", 0x07E0)
                time.sleep(2.0)
                if level >= 5:
                    overlay("ALL CLEAR!", f"Final: {score}", 0xFFE0)
                    time.sleep(3.0)
                    running = False
                    break
                level += 1
                init_game()
                state = 'ready'; ready_timer = 1.0
                draw_hud()
                render_game()
                overlay(f"LEVEL {level}", "GET READY!", 0x07E0)
                last_render = now
                continue

            if state == 'over':
                overlay("GAME OVER", f"Score: {score}", 0xF800)
                time.sleep(2.5)
                init_game()
                state = 'select'
                enc_confirmed = False
                render_select()
                continue

            # ── playing: 游戏 tick ──
            if state == 'playing':
                for _ in range(TICKS_PER_FRAME):
                    update_game()
                    if state != 'playing':  # won/over 中断
                        break

                # 渲染
                if state == 'playing' and now - last_render >= RENDER_INTERVAL:
                    # HUD 仅在变化时重绘
                    if (score != prev_score or lives != prev_lives or
                            enemies_left != prev_enemies):
                        draw_hud()
                    prev_score = score; prev_lives = lives
                    prev_enemies = enemies_left

                    render_game()
                    last_render = now

                # 状态切换后强制重绘
                if state != 'playing':
                    draw_hud()
                    render_game()
                    last_render = now

        # ── 退出清理 ──
        kb.fill(inv(0x0000))
        if stop_signal:
            pathlib.Path(stop_signal).unlink(missing_ok=True)
