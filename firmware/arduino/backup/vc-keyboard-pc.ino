/*
 * VC-Keyboard 通用 PC 外设固件
 * MCU: ESP32-S3-WROOM-1-N16R8
 *
 * USB CDC Serial 连接 PC，接收绘制命令/二进制帧，
 * 上报按键/编码器/麦克风事件。
 *
 * 依赖库 (Arduino Library Manager):
 *   - Adafruit GFX Library
 *   - Adafruit ST7789 Library
 *
 * 协议详见 doc/DESIGN.md
 *
 * 串口: USB CDC (Hardware CDC and JTAG 模式)
 */

#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <ESP_I2S.h>

// ============================================================
// 引脚定义
// ============================================================

// 按键 (5 个, 低电平触发)
const uint8_t KEY_PINS[]  = { 3, 7, 6, 5, 4 };
const char*  KEY_NAMES[]  = { "KEY1", "KEY2", "KEY3", "KEY4", "KEY5" };
const int    KEY_COUNT     = 5;
const uint8_t SW_PIN       = 17;

// 旋转编码器
const uint8_t ENC_A_PIN    = 45;
const uint8_t ENC_B_PIN    = 46;
const uint8_t ENC_BTN_PIN  = 42;

// MEMS PDM 麦克风
const uint8_t MIC_CLK_PIN  = 14;
const uint8_t MIC_DATA_PIN = 15;

// TFT LCD (ST7789, SPI)
const uint8_t TFT_CS_PIN   = 10;
const uint8_t TFT_DC_PIN   = 8;
const uint8_t TFT_RST_PIN  = 9;
const uint8_t TFT_MOSI_PIN = 11;   // 硬件 SPI, 仅备注
const uint8_t TFT_SCK_PIN  = 12;

// ============================================================
// 外设对象
// ============================================================

Adafruit_ST7789 tft(TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);
I2SClass         mic_i2s;

// ============================================================
// 常量
// ============================================================

#define PROTOCOL_VERSION  "VCK:v1.0:ESP32-S3"
#define MIC_SAMPLE_RATE   44100
#define CMD_BUF_SIZE      512
#define MIC_BUF_SAMPLES   320     // 每包音频采样数 (~7.3ms @44.1k)

// ============================================================
// 状态变量
// ============================================================

// 串口命令缓冲
static char    cmd_buf[CMD_BUF_SIZE];
static int     cmd_len = 0;

// 二进制帧状态 (握手协议)
static enum { BF_IDLE, BF_HEADER, BF_LINE } bf_state = BF_IDLE;
static uint8_t  bf_hdr[10];
static int      bf_hdr_pos = 0;
static int      bf_payload_len = 0;
static int      bf_line = 0, bf_line_bytes = 0;
static uint8_t* bf_line_buf = NULL;
static int      frame_x = 0, frame_y = 0, frame_w = 0, frame_h = 0;

// 麦克风
static bool    mic_streaming = false;
static bool    mic_initialized = false;

// 输入上报开关
static bool    report_keys    = true;
static bool    report_encoder = true;
static bool    report_switch  = true;

// 编码器 ISR 状态
volatile int32_t enc_counter  = 0;
volatile bool    enc_btn_flag = false;

// 按键去抖
static bool      prev_keys[5]    = { HIGH, HIGH, HIGH, HIGH, HIGH };
static bool      prev_sw         = HIGH;
static int32_t   last_enc_count  = 0;

// ============================================================
// ISR
// ============================================================

// 正交编码器: A 相边沿触发 ISR, 同时读取 B 相电平判断方向
// 边沿 + B 电平 → 直接判断, 无需状态机, 天然抗抖动, CW/CCW 完全对称
//
//   A 上升沿 (0→1):  B=0 → CW+1    B=1 → CCW-1
//   A 下降沿 (1→0):  B=1 → CW+1    B=0 → CCW-1

static volatile uint8_t enc_last_a = 0;

void IRAM_ATTR enc_isr() {
  uint32_t in = REG_READ(GPIO_IN1_REG);
  uint8_t a = (in >> (ENC_A_PIN - 32)) & 1;
  uint8_t b = (in >> (ENC_B_PIN - 32)) & 1;

  if (a == enc_last_a) return;  // 假触发 (边沿已过去)
  enc_last_a = a;

  if (a == 1) {                 // 上升沿
    enc_counter += (b == 0) ? 1 : -1;
  } else {                      // 下降沿
    enc_counter += (b == 1) ? 1 : -1;
  }
}

void IRAM_ATTR enc_btn_isr() {
  enc_btn_flag = true;
}

// ============================================================
// 初始化
// ============================================================

void setup() {
  Serial.setRxBufferSize(4096);  // 加大 RX 缓冲, 防止显示命令溢出
  Serial.begin(115200);          // USB CDC, 波特率忽略, 实际 ~6Mbps
  delay(500);

  init_display();
  init_keys();
  init_encoder();
  init_mic();

  // 显示启动画面
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_GREEN);
  tft.setTextSize(2);
  tft.setCursor(40, 100);
  tft.print("VC-Keyboard");
  tft.setTextSize(1);
  tft.setTextColor(ST77XX_WHITE);
  tft.setCursor(50, 130);
  tft.print(mic_initialized ? "MIC OK" : "MIC FAIL");

  Serial.println(F("RDY"));
}

void init_display() {
  pinMode(TFT_CS_PIN, OUTPUT);
  digitalWrite(TFT_CS_PIN, HIGH);
  tft.init(240, 320, SPI_MODE2);
  tft.setRotation(1);   // 横屏: 320×240
  tft.fillScreen(ST77XX_BLACK);
}

void init_keys() {
  for (int i = 0; i < KEY_COUNT; i++) {
    pinMode(KEY_PINS[i], INPUT_PULLUP);
  }
  pinMode(SW_PIN, INPUT_PULLUP);
}

void init_encoder() {
  pinMode(ENC_A_PIN, INPUT_PULLUP);
  pinMode(ENC_B_PIN, INPUT_PULLUP);
  pinMode(ENC_BTN_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_A_PIN), enc_isr, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_BTN_PIN), enc_btn_isr, FALLING);
}

void init_mic() {
  mic_i2s.setPinsPdmRx(MIC_CLK_PIN, MIC_DATA_PIN);
  mic_initialized = mic_i2s.begin(I2S_MODE_PDM_RX, MIC_SAMPLE_RATE,
                                   I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  if (mic_initialized) delay(50);
}

// ============================================================
// 主循环
// ============================================================

void loop() {
  process_serial();
  scan_inputs();
  stream_audio();
}

// ============================================================
// 串口处理
// ============================================================

// 一字节预读缓存: 解决 USB CDC 分包导致的 0xAA 0xBB 分离问题
static bool have_pending = false;
static byte pending_byte = 0;

void process_serial() {
  while (Serial.available()) {
    byte b;
    if (have_pending) {
      b = pending_byte;
      have_pending = false;
    } else {
      b = Serial.read();
    }

    // 正在接收二进制帧 (优先级最高)
    if (bf_state != BF_IDLE) {
      handle_frame_byte(b);
      continue;
    }

    // 检测二进制帧头 \xAA\xBB
    if (b == 0xAA) {
      // 尝试读下一个字节
      byte b2;
      if (have_pending) {
        b2 = pending_byte;
        have_pending = false;
      } else if (Serial.available()) {
        b2 = Serial.read();
      } else {
        // \xAA 可能是帧头, 也可能只是文本里的一个字节
        // 先缓存, 等下一个字节到了再判断
        pending_byte = 0xAA;
        have_pending = true;
        continue;
      }

      if (b2 == 0xBB) {
        start_binary_frame();
        continue;
      }
      // 不是帧头, 两个都当文本
      append_text(0xAA);
      append_text(b2);
      continue;
    }

    // 文本命令: 以 \n 结尾
    if (b == '\n' || b == '\r') {
      if (cmd_len > 0) {
        cmd_buf[cmd_len] = '\0';
        execute_command(cmd_buf);
        cmd_len = 0;
      }
      continue;
    }

    append_text(b);
  }
}

static void append_text(byte b) {
  if (cmd_len < CMD_BUF_SIZE - 1) {
    cmd_buf[cmd_len++] = (char)b;
  } else {
    cmd_len = 0;
  }
}

// ============================================================
// 二进制帧接收 (按行接收, 支持任意尺寸)
//
// 帧格式 (little-endian):
//   \xAA\xBB magic
//   uint16_t payload_len   (8 + w*h*2)
//   uint16_t x, y, w, h
//   uint8_t  RGB565[w*h*2]
// ============================================================

void start_binary_frame() {
  bf_state = BF_HEADER;
  bf_hdr_pos = 0;
}

void handle_frame_byte(byte b) {
  if (bf_state == BF_HEADER) {
    bf_hdr[bf_hdr_pos++] = b;

    if (bf_hdr_pos >= 10) {
      // 解析 header
      bf_payload_len = (bf_hdr[0]) | (bf_hdr[1] << 8);
      frame_x = (bf_hdr[2]) | (bf_hdr[3] << 8);
      frame_y = (bf_hdr[4]) | (bf_hdr[5] << 8);
      frame_w = (bf_hdr[6]) | (bf_hdr[7] << 8);
      frame_h = (bf_hdr[8]) | (bf_hdr[9] << 8);

      int expected = 8 + frame_w * frame_h * 2;
      if (bf_payload_len != expected || frame_w <= 0 || frame_h <= 0
          || frame_w > 320 || frame_h > 240) {
        Serial.print(F("BF:ERR plen="));
        Serial.print(bf_payload_len);
        Serial.print(F(" exp="));
        Serial.println(expected);
        bf_state = BF_IDLE;
        bf_hdr_pos = 0;
        return;
      }
      Serial.print(F("BF:"));
      Serial.print(frame_w);
      Serial.print('x');
      Serial.print(frame_h);
      Serial.print('@');
      Serial.print(frame_x);
      Serial.print(',');
      Serial.println(frame_y);

      // 分配行缓冲
      bf_line_buf = (uint8_t*)malloc(frame_w * 2);
      if (!bf_line_buf) {
        bf_state = BF_IDLE;
        bf_hdr_pos = 0;
        return;
      }

      bf_line = 0;
      bf_line_bytes = 0;
      bf_state = BF_LINE;
    }
    return;
  }

  // BF_LINE: 逐行接收
  if (bf_state == BF_LINE) {
    bf_line_buf[bf_line_bytes++] = b;

    if (bf_line_bytes >= frame_w * 2) {
      // 一行收完, 贴到屏幕
      tft.drawRGBBitmap(frame_x, frame_y + bf_line,
                        (uint16_t*)bf_line_buf, frame_w, 1);
      bf_line++;
      bf_line_bytes = 0;

      if (bf_line >= frame_h) {
        // 帧完成
        free(bf_line_buf);
        bf_line_buf = NULL;
        bf_state = BF_IDLE;
        bf_hdr_pos = 0;
      }
    }
  }
}

// ============================================================
// 命令执行
// ============================================================

void execute_command(const char* cmd) {
  // DEBUG: 打印所有 B 开头命令
  if (cmd[0] == 'B') {
    Serial.print(F("EXEC:")); Serial.println(cmd);
  }

  // ── 系统 ──
  if (strcmp(cmd, "*IDN?") == 0) {
    Serial.println(F(PROTOCOL_VERSION));
    return;
  }
  if (strcmp(cmd, "PING") == 0) {
    Serial.println(F("PONG"));
    return;
  }
  if (strcmp(cmd, "*RST") == 0) {
    Serial.println(F("RST"));
    delay(100);
    ESP.restart();
    return;
  }

  // ── 全屏填充 ──
  if (cmd[0] == 'F' && cmd[1] == ',') {
    uint16_t color;
    if (sscanf(cmd + 2, "%hx", &color) == 1) {
      tft.fillScreen(color);
    }
    return;
  }

  // ── 填充矩形 R,x,y,w,h,color ──
  if (cmd[0] == 'R' && cmd[1] == ',') {
    int x, y, w, h;
    uint16_t color;
    if (sscanf(cmd + 2, "%d,%d,%d,%d,%hx", &x, &y, &w, &h, &color) == 5) {
      tft.fillRect(x, y, w, h, color);
    }
    return;
  }

  // ── 水平线 H,x,y,w,color ──
  if (cmd[0] == 'H' && cmd[1] == ',') {
    int x, y, w;
    uint16_t color;
    if (sscanf(cmd + 2, "%d,%d,%d,%hx", &x, &y, &w, &color) == 4) {
      tft.drawFastHLine(x, y, w, color);
    }
    return;
  }

  // ── 垂直线 V,x,y,h,color ──
  if (cmd[0] == 'V' && cmd[1] == ',') {
    int x, y, h;
    uint16_t color;
    if (sscanf(cmd + 2, "%d,%d,%d,%hx", &x, &y, &h, &color) == 4) {
      tft.drawFastVLine(x, y, h, color);
    }
    return;
  }

  // ── 文本 T,x,y,size,color,text ──
  // size: S=1 M=2 L=3 XL=4
  if (cmd[0] == 'T' && cmd[1] == ',') {
    int x, y, tx, th;
    char sz;
    uint16_t color;
    // 格式: T,x,y,S,FFFF,text
    char text[CMD_BUF_SIZE];
    int n = sscanf(cmd + 2, "%d,%d,%c,%hx,%[^\n]", &x, &y, &sz, &color, text);
    if (n >= 4) {
      uint8_t size = 1;
      if      (sz == 'S') size = 1;
      else if (sz == 'M') size = 2;
      else if (sz == 'L') size = 3;
      else if (sz == 'X' || sz == '4') size = 4;

      tft.setTextSize(size);
      tft.setTextColor(color);
      tft.setCursor(x, y);
      if (n == 5) tft.print(text);
    }
    return;
  }

  // ── 二进制位图 B,x,y,w,h+原始 RGB565 ──
  if (cmd[0] == 'B' && cmd[1] == ',') {
    int x, y, w, h;
    Serial.print(F("B_CMD:")); Serial.println(cmd);  // 确认收到命令
    if (sscanf(cmd + 2, "%d,%d,%d,%d", &x, &y, &w, &h) == 4) {
      int total = w * h * 2;
      Serial.print(F("B_PARSE:")); Serial.print(w); Serial.print('x'); Serial.println(h);
      if (total > 0 && total <= 153600 && w <= 320 && h <= 240) {
        uint8_t* buf = (uint8_t*)malloc(total);
        if (buf) {
          size_t rd = 0;
          uint32_t deadline = millis() + 5000;
          while (rd < (size_t)total && millis() < deadline) {
            if (Serial.available()) {
              buf[rd++] = Serial.read();
            }
          }
          Serial.print(F("B_DONE rd=")); Serial.print(rd); Serial.print('/'); Serial.println(total);
          if (rd == (size_t)total) {
            tft.drawRGBBitmap(x, y, (uint16_t*)buf, w, h);
          }
          free(buf);
        } else { Serial.println(F("B_MALLOC_FAIL")); }
      } else { Serial.println(F("B_SIZE_ERR")); }
    } else { Serial.println(F("B_PARSE_FAIL")); }
    return;
  }

  // ── 显示控制 ──
  if (strncmp(cmd, "SCR:R:", 6) == 0) {
    int angle = atoi(cmd + 6);
    tft.setRotation(angle);
    return;
  }

  // ── 麦克风 ──
  if (strcmp(cmd, "MIC:ON") == 0) {
    mic_streaming = mic_initialized;
    Serial.println(mic_streaming ? F("MIC:ON") : F("MIC:FAIL"));
    return;
  }
  if (strcmp(cmd, "MIC:OFF") == 0) {
    mic_streaming = false;
    Serial.println(F("MIC:OFF"));
    return;
  }

  // ── 输入上报 ──
  if (strcmp(cmd, "RPT:ALL:on") == 0) {
    report_keys = report_encoder = report_switch = true;
    return;
  }
  if (strcmp(cmd, "RPT:ALL:off") == 0) {
    report_keys = report_encoder = report_switch = false;
    return;
  }
  if (strcmp(cmd, "RPT:KEY:on") == 0)  { report_keys = true;    return; }
  if (strcmp(cmd, "RPT:KEY:off") == 0) { report_keys = false;   return; }
  if (strcmp(cmd, "RPT:ENC:on") == 0)  { report_encoder = true;  return; }
  if (strcmp(cmd, "RPT:ENC:off") == 0) { report_encoder = false; return; }
  if (strcmp(cmd, "RPT:SW:on") == 0)   { report_switch = true;   return; }
  if (strcmp(cmd, "RPT:SW:off") == 0)  { report_switch = false;  return; }

  // ── 未知命令 ──
  Serial.print(F("ERR:unknown:"));
  Serial.println(cmd);
}

// ============================================================
// 输入扫描
// ============================================================

void scan_inputs() {
  // ── 按键 ──
  for (int i = 0; i < KEY_COUNT; i++) {
    bool cur = digitalRead(KEY_PINS[i]);
    if (cur != prev_keys[i]) {
      delay(30);  // 去抖
      cur = digitalRead(KEY_PINS[i]);
      if (cur != prev_keys[i]) {
        prev_keys[i] = cur;
        if (report_keys) {
          Serial.print(F("K:"));
          Serial.print(cur == LOW ? 'D' : 'U');
          Serial.print(':');
          Serial.println(KEY_NAMES[i]);
        }
      }
    }
  }

  // ── 拨动开关 ──
  bool cur_sw = digitalRead(SW_PIN);
  if (cur_sw != prev_sw) {
    delay(30);
    cur_sw = digitalRead(SW_PIN);
    if (cur_sw != prev_sw) {
      prev_sw = cur_sw;
      if (report_switch) {
        Serial.println(cur_sw == LOW ? F("SW:ON") : F("SW:OFF"));
      }
    }
  }

  // ── 编码器 ──
  int32_t cur_enc;
  noInterrupts();
  cur_enc = enc_counter;
  interrupts();

  if (cur_enc != last_enc_count && report_encoder) {
    int32_t delta = cur_enc - last_enc_count;
    last_enc_count = cur_enc;
    Serial.print(F("E:"));
    Serial.print(delta > 0 ? "CW:" : "CCW:");
    Serial.println(abs(delta));
  }

  // 编码器按键
  bool btn_flag;
  noInterrupts();
  btn_flag = enc_btn_flag;
  if (btn_flag) enc_btn_flag = false;
  interrupts();

  if (btn_flag && report_encoder) {
    delay(30);
    if (digitalRead(ENC_BTN_PIN) == LOW) {
      Serial.println(F("E:BTN"));
    }
  }

  delay(2);
}

// ============================================================
// 麦克风音频流
// ============================================================

void stream_audio() {
  if (!mic_streaming || !mic_initialized) return;

  static int16_t mic_buf[MIC_BUF_SAMPLES];
  static int     mic_idx = 0;

  // 非阻塞尝试: 读取一个采样, 没有数据则返回
  // (ESP_I2S::read 阻塞, 但 44.1kHz 下每个采样 ~22.7μs, 可以接受)
  for (int i = 0; i < MIC_BUF_SAMPLES; i++) {
    mic_buf[i] = (int16_t)mic_i2s.read();
  }

  // 发送二进制音频包: \xCC\xDD len(2B LE) PCM16_data
  uint16_t data_len = MIC_BUF_SAMPLES * sizeof(int16_t);
  uint16_t total_len = data_len;

  Serial.write(0xCC);
  Serial.write(0xDD);
  Serial.write((uint8_t)(total_len & 0xFF));
  Serial.write((uint8_t)((total_len >> 8) & 0xFF));
  Serial.write((uint8_t*)mic_buf, data_len);
}
