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
// 启动画面
// ============================================================

// ST7789 INVON: 硬件层面取反所有颜色 → 代码中预先取反, 双重取反=原始色
#define INV(c) ((uint16_t)(~(c)))

void show_splash_screen() {
  // ── 背景: 深色科技风 ──
  tft.fillScreen(INV(0x0004));   // deep navy-black

  // 几何色块: 顶部 & 底部 accent bars
  tft.fillRect(0, 0, 320, 3, INV(0x07FF));         // top edge — bright cyan
  tft.fillRect(0, 237, 320, 3, INV(0x07FF));       // bottom edge

  // 扫描线纹理: 每 6px 一条半透明线
  for (int y = 10; y < 230; y += 6) {
    tft.drawFastHLine(20, y, 280, INV(0x020C));
  }

  // ── 双层边框 ──
  tft.drawRect(10, 10, 300, 220, INV(0x0318));     // outer: dim cyan
  tft.drawRect(13, 13, 294, 214, INV(0x063F));     // inner: brighter

  // ── 四角括号 ──
  const int CX = 22, CY = 22, CL = 24, CG = 2;
  const uint16_t CA = INV(0x07FF);  // accent cyan
  // TL
  tft.drawFastHLine(CX, CY, CL, CA);           tft.drawFastVLine(CX, CY, CL, CA);
  tft.drawFastHLine(CX, CY + CG, CL - 4, CA);  tft.drawFastVLine(CX + CG, CY, CL - 4, CA);
  // TR
  tft.drawFastHLine(298 - CL, CY, CL, CA);     tft.drawFastVLine(298, CY, CL, CA);
  tft.drawFastHLine(302 - CL + 4, CY + CG, CL - 4, CA); tft.drawFastVLine(298 - CG, CY, CL - 4, CA);
  // BL
  tft.drawFastHLine(CX, 218, CL, CA);          tft.drawFastVLine(CX, 218 - CL, CL, CA);
  tft.drawFastHLine(CX, 218 - CG, CL - 4, CA); tft.drawFastVLine(CX + CG, 218 - CL + 4, CL - 4, CA);
  // BR
  tft.drawFastHLine(298 - CL, 218, CL, CA);    tft.drawFastVLine(298, 218 - CL, CL, CA);
  tft.drawFastHLine(302 - CL + 4, 218 - CG, CL - 4, CA); tft.drawFastVLine(298 - CG, 218 - CL + 4, CL - 4, CA);

  // ── 装饰小菱形 (四角内侧) ──
  const int DX = 50, DY = 48;
  // TL diamond
  tft.drawPixel(DX, DY, INV(0x07FF));
  tft.drawFastHLine(DX - 3, DY, 7, INV(0x063F));
  tft.drawFastVLine(DX, DY - 3, 7, INV(0x063F));
  // TR diamond
  tft.drawPixel(320 - DX, DY, INV(0x07FF));
  tft.drawFastHLine(320 - DX - 3, DY, 7, INV(0x063F));
  tft.drawFastVLine(320 - DX, DY - 3, 7, INV(0x063F));
  // BL diamond
  tft.drawPixel(DX, 240 - DY, INV(0x07FF));
  tft.drawFastHLine(DX - 3, 240 - DY, 7, INV(0x063F));
  tft.drawFastVLine(DX, 240 - DY - 3, 7, INV(0x063F));
  // BR diamond
  tft.drawPixel(320 - DX, 240 - DY, INV(0x07FF));
  tft.drawFastHLine(320 - DX - 3, 240 - DY, 7, INV(0x063F));
  tft.drawFastVLine(320 - DX, 240 - DY - 3, 7, INV(0x063F));

  // ── 标题区顶部装饰线 ──
  tft.drawFastHLine(60, 76, 200, INV(0x041F));
  tft.drawFastHLine(70, 78, 180, INV(0x063F));

  // ── 主标题 ──
  tft.setTextSize(3);
  tft.setTextColor(INV(0x07FF));   // cyan
  tft.setCursor(32, 84);
  tft.print("Yiy-Workstation");

  // ── 标题区底部装饰线 ──
  tft.drawFastHLine(70, 114, 180, INV(0x063F));
  tft.drawFastHLine(60, 116, 200, INV(0x041F));

  // ── 副标题 ──
  tft.setTextSize(2);
  tft.setTextColor(INV(0x053C));   // medium cyan-blue
  tft.setCursor(62, 130);
  tft.print("Designed by YYC");

  // ── 分隔线 ──
  tft.drawFastHLine(90, 162, 140, INV(0x039F));
  // 分隔线中间圆点
  tft.fillCircle(160, 162, 3, INV(0x07FF));
  tft.fillCircle(160, 162, 1, INV(0xFFFF));

  // ── 底部信息栏 ──
  tft.setTextSize(1);

  // 版本
  tft.setCursor(46, 178);
  tft.setTextColor(INV(0x063F));
  tft.print("v1.0");

  // 竖分隔
  tft.drawFastVLine(76, 176, 14, INV(0x0318));

  // MIC 状态
  tft.setCursor(84, 178);
  tft.setTextColor(mic_initialized ? INV(0x07E0) : INV(0xF800));  // green : red
  tft.print(mic_initialized ? "MIC" : "MIC");

  // 竖分隔
  tft.drawFastVLine(134, 176, 14, INV(0x0318));

  // MCU
  tft.setCursor(142, 178);
  tft.setTextColor(INV(0x063F));
  tft.print("ESP32-S3");

  // 竖分隔
  tft.drawFastVLine(204, 176, 14, INV(0x0318));

  // 状态 dot
  tft.fillCircle(216, 182, 3, mic_initialized ? INV(0x07E0) : INV(0xF800));

  tft.setCursor(224, 178);
  tft.setTextColor(INV(0x063F));
  tft.print(mic_initialized ? "OK" : "FAIL");

  // ── 底部两侧小十字 ──
  // left cross
  tft.drawFastHLine(44, 210, 8, INV(0x0318));
  tft.drawFastVLine(48, 206, 8, INV(0x0318));
  // right cross
  tft.drawFastHLine(268, 210, 8, INV(0x0318));
  tft.drawFastVLine(272, 206, 8, INV(0x0318));
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
  show_splash_screen();

  Serial.println(F("RDY"));
}

void init_display() {
  pinMode(TFT_CS_PIN, OUTPUT);
  digitalWrite(TFT_CS_PIN, HIGH);
  tft.init(240, 320, SPI_MODE2);
  tft.setRotation(1);   // 横屏: 320×240
  tft.setSPISpeed(80000000);  // 80MHz, 默认 32MHz; 提速整屏绘制 (走线不稳则降回 40MHz)
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

void process_serial() {
  while (Serial.available()) {
    byte b = Serial.read();

    // 文本命令: 以 \n 结尾 (B 位图命令的数据由 execute_command 内部直接读取,
    // 不经过这里; 因此位图数据中的 0xAA/0x0A 等字节不会干扰文本解析)
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
// 命令执行
// ============================================================

void execute_command(const char* cmd) {

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
  // PC 侧按行分块推送 (单块 < 4KB RX 缓冲), 每块等本分支应答:
  //   成功 → "OK", 行读取超时(字节丢失) → "B:ERR" 并排空残留字节.
  // 小块 (≤4KB, 分块推送的常态): 整块读入 + 一次 drawRGBBitmap block write,
  //   省去逐行 startWrite/setAddrWindow/endWrite 的 h 倍开销, 显著提速.
  // 大块 (>4KB, 仅遗留/直推路径): 退化为逐行流式, 避免大 malloc + 长阻塞 SPI.
  if (cmd[0] == 'B' && cmd[1] == ',') {
    int x, y, w, h;
    if (sscanf(cmd + 2, "%d,%d,%d,%d", &x, &y, &w, &h) == 4) {
      if (w > 0 && h > 0 && w <= 320 && h <= 240) {
        size_t need = (size_t)w * h * 2;
        if (need <= 4096) {
          // ── 整块路径 (快) ──
          uint8_t* buf = (uint8_t*)malloc(need);
          if (buf) {
            size_t rd = 0;
            uint32_t deadline = millis() + 5000;
            while (rd < need && millis() < deadline) {
              if (Serial.available()) buf[rd++] = Serial.read();
              else delay(0);
            }
            if (rd == need) {
              tft.drawRGBBitmap(x, y, (uint16_t*)buf, w, h);
              Serial.println(F("OK"));
            } else {
              while (Serial.available()) { Serial.read(); delay(0); }
              Serial.print(F("B:ERR:rd="));
              Serial.println((int)rd);
            }
            free(buf);
          }
        } else {
          // ── 逐行路径 (遗留大块, 不常走) ──
          uint8_t* line = (uint8_t*)malloc(w * 2);
          if (line) {
            int row = 0; bool ok = true;
            for (row = 0; row < h; row++) {
              size_t rd = 0;
              uint32_t deadline = millis() + 5000;
              while (rd < (size_t)(w * 2) && millis() < deadline) {
                if (Serial.available()) line[rd++] = Serial.read();
                else delay(0);
              }
              if (rd == (size_t)(w * 2)) {
                tft.drawRGBBitmap(x, y + row, (uint16_t*)line, w, 1);
              } else { ok = false; break; }
            }
            free(line);
            if (ok) Serial.println(F("OK"));
            else {
              while (Serial.available()) { Serial.read(); delay(0); }
              Serial.print(F("B:ERR:row="));
              Serial.println(row);
            }
          }
        }
      }
    }
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
