"""
语音电平表 + 频谱可视化

  实时显示麦克风音频的频谱柱状图 (64 频段) + 波形图 + 峰值电平。

  依赖: numpy (FFT)
  操作: KEY5 = 退出
"""

import os, pathlib, struct, time
from collections import deque

from vckb.apps.base import AppDefinition

APP = AppDefinition(
    id="voice_meter",
    name="Voice Meter",
    name_zh="语音电平表",
    description="Real-time audio spectrum & waveform visualization",
    icon="🎤",
    category="tool",
    controls={"KEY5": "退出"},
    module="vckb.apps.voice_meter",
    requires=["numpy"],
)

# ── 布局常量 ──
TOP_H = 18       # 顶栏高度
SPEC_H = 180     # 频谱区高度
WAVE_H = 36      # 波形区高度
N_BARS = 64      # 频柱数量
BAR_W = 320 // N_BARS  # 每柱宽度 = 5
FFT_SIZE = 1024  # FFT 点数

# 频谱区 Y 范围
SPEC_Y0 = TOP_H
SPEC_Y1 = SPEC_Y0 + SPEC_H  # 198

# 波形区 Y 范围
WAVE_Y0 = SPEC_Y1 + 2   # 200 (分隔线后)
WAVE_MID = WAVE_Y0 + WAVE_H // 2  # 218


def main():
    import numpy as np
    from vckb import VCKeyboard, BLACK, WHITE

    stop_signal = os.environ.get("VCKB_STOP_SIGNAL", "")

    with VCKeyboard() as kb:
        kb.fill(BLACK)

        # ── 音频缓冲 ──
        fft_buf = deque(maxlen=FFT_SIZE)  # FFT 累积
        wave_buf = deque(maxlen=320)       # 波形显示

        # ── 状态 ──
        bar_heights = np.zeros(N_BARS, dtype=np.float32)  # 平滑后的柱高
        peak_db = -60.0
        speaking = False
        frame_count = 0
        frames_per_update = 2  # 每 2 包音频刷新一次

        # ── FFT 预计算 ──
        hann = np.hanning(FFT_SIZE)

        # 频率 bin → 64 频段映射 (log 尺度)
        # rfft 输出 bins: 0..FFT_SIZE//2 对应 0..22050 Hz
        freqs = np.fft.rfftfreq(FFT_SIZE, 1 / 44100)
        # 低频截止 50Hz, 高频截止 20kHz
        lo_idx = np.searchsorted(freqs, 50)
        hi_idx = np.searchsorted(freqs, 20000)
        log_freqs = np.logspace(np.log10(50), np.log10(20000), N_BARS + 1)
        band_map = []  # [(start_bin, end_bin), ...] per bar
        for i in range(N_BARS):
            b0 = np.searchsorted(freqs, log_freqs[i])
            b1 = np.searchsorted(freqs, log_freqs[i + 1])
            b0 = max(b0, lo_idx)
            b1 = min(b1, hi_idx)
            band_map.append((b0, max(b0 + 1, b1)))

        # ── 绘图 ──

        def color_for_height(h_ratio):
            """柱高比 (0~1) → RGB565 颜色 (绿→黄→红)"""
            if h_ratio < 0.33:
                t = h_ratio / 0.33
                r = int(t * 255) & 0xF8
                g = 255 & 0xFC
                b = 0
            elif h_ratio < 0.66:
                t = (h_ratio - 0.33) / 0.33
                r = 255 & 0xF8
                g = 255 & 0xFC
                b = 0
            else:
                t = (h_ratio - 0.66) / 0.34
                r = 255 & 0xF8
                g = int((1 - t) * 255) & 0xFC
                b = 0
            return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

        def draw_top_bar():
            kb.rect(0, 0, 320, TOP_H, 0x2104)
            kb.text(3, 3, f"Voice Meter", size="S", color=WHITE)
            db_text = f"PEAK:{peak_db:+.0f}dB" if peak_db > -60 else "PEAK:---"
            kb.text(120, 3, db_text, size="S", color=0x07FF if speaking else 0x8410)
            if speaking:
                kb.rect(240, 4, 10, 10, 0x07E0)
                kb.text(253, 3, "SPK", size="S", color=0x07E0)
            else:
                kb.rect(240, 4, 10, 10, 0x4208)
                kb.text(253, 3, "---", size="S", color=0x8410)

        def draw_spectrum(magnitudes):
            """画 64 根频谱柱 (差分更新: 只重画变化超过 1px 的柱)"""
            for i in range(N_BARS):
                # 柱高 = magnitude 映射到 0~SPEC_H
                mag = magnitudes[i]
                # dB 尺度: 线性 magnitude → dB
                if mag > 1e-6:
                    db = 20 * np.log10(mag)
                    # 映射: -40dB → 0px, 0dB → SPEC_H px
                    new_h = max(0, min(SPEC_H, (db + 40) / 40 * SPEC_H))
                else:
                    new_h = 0

                # 指数平滑
                bar_heights[i] = bar_heights[i] * 0.55 + new_h * 0.45
                h = int(bar_heights[i])

                if h > 0:
                    ratio = h / SPEC_H
                    color = color_for_height(ratio)
                    x = i * BAR_W
                    y = SPEC_Y1 - h
                    kb.rect(x, y, BAR_W, h, color)

                # 画基准线 (底部一条横线)
                x = i * BAR_W
                kb.hline(x, SPEC_Y1 - 1, BAR_W, 0x3186)

        def draw_waveform():
            """画底部波形折线"""
            # 背景清空
            kb.rect(0, WAVE_Y0, 320, WAVE_H, BLACK)
            # 中心基线
            kb.hline(0, WAVE_MID, 320, 0x2104)

            if len(wave_buf) < 2:
                return

            samples = list(wave_buf)
            n = len(samples)
            # 垂直范围: -32768..32767 → WAVE_Y0..WAVE_Y0+WAVE_H
            half_h = WAVE_H // 2 - 2

            for i in range(min(n, 319)):
                x = i
                # 当前采样
                v = samples[i] / 32768.0
                y = int(WAVE_MID - v * half_h)
                y = max(WAVE_Y0 + 1, min(WAVE_Y0 + WAVE_H - 2, y))
                kb.vline(x, min(y, WAVE_MID), abs(y - WAVE_MID) + 1, 0x07E0)

        # ── 音频处理 ──

        @kb.on_audio()
        def on_audio(pcm):
            nonlocal frame_count, peak_db, speaking

            # 解包 PCM16 采样
            n_samples = len(pcm) // 2
            samples = struct.unpack(f"<{n_samples}h", pcm)

            # RMS → dB
            arr = np.array(samples, dtype=np.float32)
            rms = np.sqrt(np.mean(arr ** 2))
            if rms > 0:
                db = 20 * np.log10(rms / 32768.0)
            else:
                db = -60.0
            peak_db = max(peak_db - 0.3, db)  # 峰值缓降

            # 语音活动检测: RMS > -30dB (可调)
            speaking = db > -30

            # 累积 FFT buffer
            fft_buf.extend(arr)
            wave_buf.extend(arr)

            frame_count += 1
            if frame_count < frames_per_update:
                return
            frame_count = 0

            # ── FFT ──
            if len(fft_buf) >= FFT_SIZE:
                fft_data = np.array(list(fft_buf)[-FFT_SIZE:], dtype=np.float32)
                windowed = fft_data * hann
                spectrum = np.abs(np.fft.rfft(windowed))
                # 归一化
                spectrum /= FFT_SIZE

                # 合并到 64 频段
                mags = np.zeros(N_BARS, dtype=np.float32)
                for i, (b0, b1) in enumerate(band_map):
                    if b1 > b0:
                        mags[i] = np.max(spectrum[b0:b1])

                draw_spectrum(mags)

            # ── 波形 ──
            draw_waveform()

            # ── 顶栏 ──
            draw_top_bar()

        # ── 初始绘制 ──
        draw_top_bar()

        # ── 开启麦克风 ──
        kb.mic_start()

        # ── 主循环 ──
        running = True

        @kb.on_key("KEY5", "down")
        def on_exit():
            nonlocal running
            running = False

        while running:
            kb.poll(timeout=0.05)
            if stop_signal and pathlib.Path(stop_signal).exists():
                running = False
                break

        kb.mic_stop()
        kb.clear()
        if stop_signal:
            pathlib.Path(stop_signal).unlink(missing_ok=True)
