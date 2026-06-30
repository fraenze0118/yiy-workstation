"""
打砖块 — Classic Breakout

  编码器 CW/CCW → 移动挡板
  KEY1 → 发射球 / 重新开始
  KEY2 → 暂停 / 继续
  KEY5 → 退出

  5 关难度递增: 球速 3→5, 挡板 48→32px
  5 行砖块: 红→橙→黄→绿→蓝 (50→10 分)
"""

import os, pathlib, time, math

from vckb.apps.base import AppDefinition

APP = AppDefinition(
    id="breakout",
    name="Breakout",
    name_zh="打砖块",
    description="Classic brick breaker — 5 levels, encoder control",
    icon="🧱",
    category="game",
    controls={
        "KEY3": "挡板左移",
        "KEY4": "挡板右移",
        "KEY1": "发射球 / 重新开始",
        "KEY2": "暂停 / 继续",
        "KEY5": "退出",
    },
    module="vckb.apps.breakout",
    requires=[],
)

# ── 常量 ──
TOP_H = 16
BRICK_ROWS = 5
BRICK_COLS = 8
BRICK_W = 38
BRICK_H = 10
BRICK_GAP = 1
BRICK_X0 = 1  # 左起始
BRICK_Y0 = TOP_H + 2
PADDLE_H = 6
PADDLE_Y = 226
BALL_R = 3

# 每行颜色 & 分值
ROW_COLORS = [0xF800, 0xFD20, 0xFFE0, 0x07E0, 0x001F]  # R,O,Y,G,B
ROW_SCORES = [50, 40, 30, 20, 10]


def ball_color():
    return 0xFFFF  # white


def paddle_color():
    return 0x07FF  # cyan


def bg_color():
    return 0x0000  # black


def main():
    from vckb import VCKeyboard

    stop_signal = os.environ.get("VCKB_STOP_SIGNAL", "")

    with VCKeyboard() as kb:
        # ── 游戏状态 ──
        level = 1
        score = 0
        lives = 3

        # 动态参数 (随 level 变化)
        def level_params():
            speeds = [5, 6, 7, 8, 8]
            widths = [48, 44, 40, 36, 32]
            idx = min(level - 1, 4)
            return speeds[idx], widths[idx]

        ball_speed, paddle_w = level_params()

        # 砖块
        bricks = [[True] * BRICK_COLS for _ in range(BRICK_ROWS)]
        bricks_remaining = BRICK_ROWS * BRICK_COLS

        # 挡板
        paddle_x = 160 - paddle_w // 2

        # 球
        ball_x, ball_y = 160.0, 210.0
        ball_dx, ball_dy = 0.5, -1.0  # 归一化方向

        # 归一化方向向量
        def norm_dir(dx, dy):
            mag = math.sqrt(dx * dx + dy * dy)
            return dx / mag, dy / mag

        _, ball_dy_sign_init = norm_dir(ball_dx, ball_dy)
        ball_dx, ball_dy = norm_dir(ball_dx, ball_dy)

        # 状态机
        state = "ready"  # ready | playing | paused | dead | won | over
        running = True
        prev_paddle_x = paddle_x

        def reset_ball():
            nonlocal ball_x, ball_y, ball_dx, ball_dy
            ball_x = paddle_x + paddle_w // 2
            ball_y = PADDLE_Y - BALL_R - 2
            ball_dx, ball_dy = norm_dir(0.5, -1.0)

        def reset_level():
            nonlocal bricks, bricks_remaining, state
            for r in range(BRICK_ROWS):
                for c in range(BRICK_COLS):
                    bricks[r][c] = True
            bricks_remaining = BRICK_ROWS * BRICK_COLS
            reset_ball()
            state = "ready"

        def next_level():
            nonlocal level, ball_speed, paddle_w
            level += 1
            ball_speed, paddle_w = level_params()
            reset_level()

        def brick_rect(col, row):
            x = BRICK_X0 + col * (BRICK_W + BRICK_GAP)
            y = BRICK_Y0 + row * (BRICK_H + BRICK_GAP)
            return x, y, BRICK_W, BRICK_H

        def ball_rect():
            return int(ball_x - BALL_R), int(ball_y - BALL_R), BALL_R * 2, BALL_R * 2

        # ── 碰撞检测 ──

        def circle_rect_collision(cx, cy, cr, rx, ry, rw, rh):
            """圆 vs 矩形碰撞"""
            closest_x = max(rx, min(cx, rx + rw))
            closest_y = max(ry, min(cy, ry + rh))
            dist = math.sqrt((cx - closest_x) ** 2 + (cy - closest_y) ** 2)
            return dist <= cr

        def handle_collisions():
            nonlocal ball_dx, ball_dy, ball_x, ball_y, score, bricks_remaining, lives, state

            bx, by = ball_x, ball_y
            new_dx, new_dy = ball_dx, ball_dy

            # 墙碰撞
            if bx - BALL_R <= 0:
                new_dx = abs(ball_dx)
                ball_x = BALL_R  # nudge out
            elif bx + BALL_R >= 320:
                new_dx = -abs(ball_dx)
                ball_x = 320 - BALL_R
            if by - BALL_R <= TOP_H:
                new_dy = abs(ball_dy)
                ball_y = TOP_H + BALL_R

            # 底墙 → 掉球
            if by + BALL_R >= 240:
                nonlocal lives
                lives -= 1
                if lives <= 0:
                    state = "over"
                else:
                    state = "dead"
                    reset_ball()
                return

            # Paddle 碰撞
            if circle_rect_collision(bx, by, BALL_R,
                                     paddle_x, PADDLE_Y, paddle_w, PADDLE_H):
                new_dy = -abs(ball_dy)
                # 根据撞击位置调整角度
                hit = (bx - (paddle_x + paddle_w / 2)) / (paddle_w / 2)
                hit = max(-1.0, min(1.0, hit))
                new_dx, new_dy = norm_dir(hit * 1.2, new_dy)
                # nudge ball above paddle
                ball_y = PADDLE_Y - BALL_R - 1

            # 砖块碰撞
            hit_brick = False
            for row in range(BRICK_ROWS):
                for col in range(BRICK_COLS):
                    if not bricks[row][col]:
                        continue
                    rx, ry, rw, rh = brick_rect(col, row)
                    if circle_rect_collision(bx, by, BALL_R, rx, ry, rw, rh):
                        bricks[row][col] = False
                        bricks_remaining -= 1
                        score += ROW_SCORES[row]
                        new_dy = -new_dy  # 反弹
                        hit_brick = True
                        # 只消除一个砖块 (break inner loop)
                        break
                if hit_brick:
                    break

            if hit_brick and bricks_remaining == 0:
                state = "won"

            ball_dx, ball_dy = new_dx, new_dy

        # ── 绘制 ──

        BKG = bg_color()

        def draw_static():
            """一次性绘制不动的元素: 背景 + 砖块"""
            kb.fill(BKG)
            for row in range(BRICK_ROWS):
                for col in range(BRICK_COLS):
                    if bricks[row][col]:
                        rx, ry, rw, rh = brick_rect(col, row)
                        kb.rect(rx, ry, rw, rh, ROW_COLORS[row])

        def draw_top_bar():
            """重绘顶栏文字 (轻量)"""
            kb.rect(0, 0, 320, TOP_H, 0x2104)
            kb.text(3, 3, f"SCORE:{score:05d}", size="S", color=0xFFFF)
            h = " ".join(["♥"] * lives)
            kb.text(120, 3, h, size="S", color=0xF800)
            kb.text(200, 3, f"LV{level}", size="S", color=0x07FF)

        def erase_old_ball(bx, by, bw, bh):
            kb.rect(bx, by, bw, bh, BKG)

        def draw_ball():
            bx, by, bw, bh = ball_rect()
            kb.rect(bx, by, bw, bh, ball_color())
            return bx, by, bw, bh

        def erase_old_paddle(px):
            kb.rect(px, PADDLE_Y, paddle_w, PADDLE_H, BKG)

        def draw_paddle():
            kb.rect(paddle_x, PADDLE_Y, paddle_w, PADDLE_H, paddle_color())

        def erase_brick(col, row):
            rx, ry, rw, rh = brick_rect(col, row)
            kb.rect(rx, ry, rw, rh, BKG)

        def show_overlay(msg, sub="", color=0xFFFF):
            """画状态覆盖文字"""
            yr = TOP_H + 2
            kb.rect(60, yr + 20, 200, 100, BKG)
            kb.text(65, yr + 35, msg, size="L", color=color)
            if sub:
                kb.text(90, yr + 70, sub, size="M", color=0xFFFF)

        # ── 输入 ──

        @kb.on_key("KEY3", "down")
        def on_key3():
            nonlocal paddle_x
            old = paddle_x
            paddle_x = max(0, paddle_x - 8)
            if paddle_x != old:
                erase_old_paddle(old)
                draw_paddle()
                if state == "ready":
                    reset_ball()

        @kb.on_key("KEY4", "down")
        def on_key4():
            nonlocal paddle_x
            old = paddle_x
            paddle_x = min(320 - paddle_w, paddle_x + 8)
            if paddle_x != old:
                erase_old_paddle(old)
                draw_paddle()
                if state == "ready":
                    reset_ball()

        @kb.on_key("KEY1", "down")
        def on_key1():
            nonlocal state, level, score, lives
            if state == "ready":
                state = "playing"
            elif state == "won":
                next_level()
            elif state in ("over", "dead"):
                level = 1
                score = 0
                lives = 3
                nonlocal ball_speed, paddle_w
                ball_speed, paddle_w = level_params()
                reset_level()
                state = "ready"

        @kb.on_key("KEY2", "down")
        def on_key2():
            nonlocal state
            if state == "playing":
                state = "paused"
            elif state == "paused":
                state = "playing"

        @kb.on_key("KEY5", "down")
        def on_exit():
            nonlocal running
            running = False

        # ── 游戏循环 ──

        tick = 1.0 / 60  # 60fps target, ~16ms
        old_ball = ball_rect()
        prev_score = score
        prev_lives = lives
        prev_state = state

        # 初始全屏绘制
        draw_static()
        draw_top_bar()
        draw_paddle()
        old_ball = draw_ball()

        while running:
            kb.poll(timeout=0.005)
            t0 = time.time()

            if stop_signal and pathlib.Path(stop_signal).exists():
                running = False
                break

            # ── 更新 ──
            if state == "playing":
                prev_ball = ball_rect()
                old_paddle = paddle_x
                old_bricks = bricks_remaining

                ball_x += ball_dx * ball_speed
                ball_y += ball_dy * ball_speed
                handle_collisions()

                # 增量绘制: 擦旧 → 画新
                # 球
                erase_old_ball(*prev_ball)
                # 挡板
                if paddle_x != old_paddle:
                    erase_old_paddle(old_paddle)
                    draw_paddle()
                # 被消除的砖块
                if bricks_remaining < old_bricks:
                    for row in range(BRICK_ROWS):
                        for col in range(BRICK_COLS):
                            if old_bricks - bricks_remaining <= 0:
                                break
                            # mark: just detect which brick disappeared
                    # simpler: redraw static (bricks) when one is destroyed
                    draw_static()
                    # re-draw paddle and ball on top
                    draw_paddle()

                # 画新球
                old_ball = draw_ball()

                # 顶栏变化时重绘
                if score != prev_score or lives != prev_lives:
                    draw_top_bar()
                    prev_score = score
                    prev_lives = lives

            elif state != prev_state:
                # 状态切换时全量重绘
                draw_static()
                draw_top_bar()
                draw_paddle()
                old_ball = draw_ball()

                if state == "ready":
                    show_overlay("BREAKOUT", "KEY1 = START", 0x07E0)
                elif state == "paused":
                    show_overlay("PAUSED", "KEY2 = RESUME", 0xFFE0)
                elif state == "won":
                    show_overlay("YOU WIN!", f"Score: {score}", 0x07E0)
                elif state == "over":
                    show_overlay("GAME OVER", f"Score: {score}", 0xF800)
                elif state == "dead":
                    show_overlay("MISS!", f"Lives: {lives}", 0xF800)

                prev_state = state

            # ── 帧率控制 ──
            elapsed = time.time() - t0
            if elapsed < tick:
                time.sleep(tick - elapsed)

        kb.fill(bg_color())
        if stop_signal:
            pathlib.Path(stop_signal).unlink(missing_ok=True)
