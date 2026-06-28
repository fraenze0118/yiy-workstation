"""
帧缓冲 + 差分推送

在 PC 端维护一个与设备屏幕等大的逻辑帧缓冲。
调用 begin_frame / end_frame 自动计算变化区域, 仅推送差异。
"""

from .device import VCKeyboard

DISPLAY_W = 320
DISPLAY_H = 240

class FrameBuffer:
    """320×240 RGB565 帧缓冲, 差分推送"""

    def __init__(self, kb: VCKeyboard):
        self.kb = kb
        self._front = bytearray(DISPLAY_W * DISPLAY_H * 2)  # 当前帧
        self._back  = bytearray(DISPLAY_W * DISPLAY_H * 2)  # 上一帧
        self._dirty = False

    def clear(self, color: int = 0x0000):
        """清空帧缓冲为指定颜色"""
        lo = color & 0xFF
        hi = (color >> 8) & 0xFF
        for i in range(0, len(self._front), 2):
            self._front[i]   = lo
            self._front[i+1] = hi
        self._dirty = True

    def _set_pixel(self, x: int, y: int, color: int):
        if x < 0 or x >= DISPLAY_W or y < 0 or y >= DISPLAY_H:
            return
        off = (y * DISPLAY_W + x) * 2
        self._front[off]   = color & 0xFF
        self._front[off+1] = (color >> 8) & 0xFF
        self._dirty = True

    def rect(self, x: int, y: int, w: int, h: int, color: int):
        """在帧缓冲中绘制填充矩形"""
        lo = color & 0xFF
        hi = (color >> 8) & 0xFF
        for row in range(y, min(y + h, DISPLAY_H)):
            off = (row * DISPLAY_W + x) * 2
            for col in range(w):
                if x + col >= DISPLAY_W: break
                self._front[off]   = lo
                self._front[off+1] = hi
                off += 2
        self._dirty = True

    def blit(self, x: int, y: int, w: int, h: int, rgb565: bytes):
        """将 RGB565 数据写入帧缓冲"""
        src_off = 0
        for row in range(y, min(y + h, DISPLAY_H)):
            dst_off = (row * DISPLAY_W + x) * 2
            row_bytes = min(w * 2, (DISPLAY_W - x) * 2)
            self._front[dst_off : dst_off + row_bytes] = rgb565[src_off : src_off + row_bytes]
            src_off += w * 2
        self._dirty = True

    def flush(self):
        """
        计算差分区域并推送到设备
        仅推送与上一帧不同的矩形
        """
        if not self._dirty:
            return

        # 逐行扫描, 找变化的连续区域
        row = 0
        while row < DISPLAY_H:
            off = row * DISPLAY_W * 2
            line_changed = (self._front[off : off + DISPLAY_W * 2]
                            != self._back[off : off + DISPLAY_W * 2])

            if not line_changed:
                row += 1
                continue

            # 找到变化区域的起始和结束行
            start_row = row
            while row < DISPLAY_H:
                off = row * DISPLAY_W * 2
                if self._front[off : off + DISPLAY_W * 2] == self._back[off : off + DISPLAY_W * 2]:
                    break
                row += 1
            end_row = row

            # 在这个区域内找变化的列范围
            start_col = DISPLAY_W
            end_col = 0
            for r in range(start_row, end_row):
                ro = r * DISPLAY_W * 2
                for c in range(DISPLAY_W):
                    co = ro + c * 2
                    if self._front[co] != self._back[co] or self._front[co+1] != self._back[co+1]:
                        if c < start_col: start_col = c
                        if c > end_col: end_col = c

            w = end_col - start_col + 1
            h = end_row - start_row

            # 提取该区域 RGB565 数据
            data = bytearray(w * h * 2)
            di = 0
            for r in range(start_row, end_row):
                so = (r * DISPLAY_W + start_col) * 2
                data[di : di + w * 2] = self._front[so : so + w * 2]
                di += w * 2

            # 推送到设备
            self.kb.push_frame(start_col, start_row, w, h, bytes(data))

            row = end_row

        # 保存当前帧作为上一帧
        self._back[:] = self._front
        self._dirty = False

    def full_push(self):
        """全屏推送 (不分差分)"""
        self.kb.push_frame(0, 0, DISPLAY_W, DISPLAY_H, bytes(self._front))
        self._back[:] = self._front
        self._dirty = False
