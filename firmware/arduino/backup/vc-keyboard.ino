/*
 * VC-Keyboard 外设手动测试固件
 * MCU: ESP32-S3-WROOM-1-N16R8
 *
 * 依赖库 (Arduino Library Manager):
 *   - Adafruit GFX Library
 *   - Adafruit ST7789 Library
 *
 * 通过串口菜单手动测试:
 *   1. 按键 (KEY1~5) + 拨动开关 (SW)
 *   2. 旋转编码器 (A/B/Button)
 *   3. MEMS PDM 麦克风 (I2S)
 *   4. TFT LCD 显示屏 (ST7789, SPI)
 *   5. VBUS 电压检测
 *   6. 综合监控模式
 *
 * 串口: 115200 baud
 */

#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <ESP_I2S.h>

// ============================================================
// 引脚定义
// ============================================================

// --- 按键 (6个, 低电平触发) ---
const uint8_t KEY_PINS[]   = {3, 4, 5, 6, 7};
const char*  KEY_NAMES[]   = {"KEY1 (GPIO3)", "KEY2 (GPIO4)", "KEY3 (GPIO5)",
                              "KEY4 (GPIO6)", "KEY5 (GPIO7)"};
const uint8_t KEY_COUNT    = 5;
const uint8_t SW_PIN       = 17;  // 拨动开关 ST-0-102-A01-T000-LF

// --- 旋转编码器 (PEC11L-4210F) ---
const uint8_t ENC_A_PIN    = 45;
const uint8_t ENC_B_PIN    = 46;
const uint8_t ENC_BTN_PIN  = 42;

// --- MEMS PDM 麦克风 (GSA4030H10-F26-8P) ---
const uint8_t MIC_CLK_PIN  = 14;
const uint8_t MIC_DATA_PIN = 15;

// --- TFT LCD (HS280S010B, ST7789, 240x320, SPI) ---
const uint8_t TFT_CS_PIN   = 10;
const uint8_t TFT_DC_PIN   = 8;
const uint8_t TFT_RST_PIN  = 9;
const uint8_t TFT_MOSI_PIN = 11;
const uint8_t TFT_SCK_PIN  = 12;

// --- VBUS 电压检测 (分压 1/2) ---
const uint8_t VBUS_DET_PIN = 16;

// ============================================================
// 外设对象
// ============================================================

// ST7789 显示屏 (硬件 SPI)
Adafruit_ST7789 tft(TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);

// ============================================================
// 旋转编码器状态 (volatile = ISR 安全)
// ============================================================
volatile int32_t enc_counter  = 0;
volatile bool    enc_btn_flag  = false;

// I2S 麦克风 (使用新版 ESP_I2S API)
#define I2S_SAMPLE_RATE   44100    // 44.1kHz → PDM CLK = 2.822MHz (GSA4030H10: 1.0~4.0MHz)
I2SClass mic_i2s;
static bool mic_initialized = false;

// ============================================================
// ISR 前向声明 (Arduino 编译必需)
// ============================================================
void IRAM_ATTR enc_isr();
void IRAM_ATTR enc_btn_isr();

// ============================================================
// 初始化
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(500);

  print_banner();
  init_all_peripherals();
  print_menu();
}

void print_banner() {
  Serial.println();
  Serial.println(F("+------------------------------------------+"));
  Serial.println(F("|  VC-Keyboard  Peripheral Test Firmware    |"));
  Serial.println(F("|  MCU: ESP32-S3-WROOM-1-N16R8             |"));
  Serial.println(F("+------------------------------------------+"));
  Serial.println();
}

void init_all_peripherals() {
  Serial.println(F("Initializing peripherals..."));
  Serial.println();

  // --- 按键引脚 ---
  for (int i = 0; i < KEY_COUNT; i++) {
    pinMode(KEY_PINS[i], INPUT_PULLUP);
  }
  pinMode(SW_PIN, INPUT_PULLUP);
  Serial.println(F("  [OK] Keys (GPIO 3/4/5/6/7) + SW (GPIO17) -> INPUT_PULLUP"));

  // --- 旋转编码器 ---
  pinMode(ENC_A_PIN, INPUT_PULLUP);
  pinMode(ENC_B_PIN, INPUT_PULLUP);
  pinMode(ENC_BTN_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_A_PIN), enc_isr, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_BTN_PIN), enc_btn_isr, FALLING);
  Serial.println(F("  [OK] Rotary Encoder (A=GPIO45, B=GPIO46, BTN=GPIO42) -> INT"));

  // --- VBUS 检测 ---
  analogReadResolution(12);               // ESP32-S3 ADC: 12-bit
  analogSetAttenuation(ADC_11db);         // 满量程 ~3.3V
  pinMode(VBUS_DET_PIN, INPUT);
  Serial.println(F("  [OK] VBUS detect (GPIO16) -> ADC"));

  // --- I2S PDM 麦克风 ---
  if (init_mic_i2s()) {
    Serial.println(F("  [OK] MEMS PDM Mic (CLK=GPIO14, DATA=GPIO15) -> I2S"));
  } else {
    Serial.println(F("  [FAIL] MEMS PDM Mic init failed"));
  }

  // --- TFT LCD ---
  init_lcd();
  Serial.println();

  // 在屏幕上显示启动信息
  draw_test_pattern();
}

// ============================================================
// I2S PDM 麦克风初始化 (ESP_I2S API, ESP32-S3 PDM 正确支持)
// ============================================================
bool init_mic_i2s() {
  mic_i2s.setPinsPdmRx(MIC_CLK_PIN, MIC_DATA_PIN);
  bool ok = mic_i2s.begin(I2S_MODE_PDM_RX, I2S_SAMPLE_RATE,
                          I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  if (ok) {
    mic_initialized = true;
    delay(50);
  }
  return ok;
}

// ============================================================
// TFT LCD 初始化
// ============================================================
void init_lcd() {
  pinMode(TFT_CS_PIN, OUTPUT);
  digitalWrite(TFT_CS_PIN, HIGH);

  tft.init(240, 320, SPI_MODE2);        // ST7789 通常使用 SPI_MODE2 或 SPI_MODE3
  tft.setRotation(0);                    // 竖屏
  tft.fillScreen(ST77XX_BLACK);
  Serial.println(F("  [OK] TFT LCD (ST7789, 240x320, HW SPI) -> initialized"));
}

// ============================================================
// LCD 测试画面
// ============================================================
void draw_test_pattern() {
  tft.fillScreen(ST77XX_BLACK);

  // 标题栏
  tft.fillRect(0, 0, 240, 30, ST77XX_BLUE);
  tft.setCursor(10, 8);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.print("VC-Keyboard");

  // 色块测试
  uint16_t colors[] = {ST77XX_RED, ST77XX_GREEN, ST77XX_BLUE,
                       ST77XX_YELLOW, ST77XX_CYAN, ST77XX_MAGENTA};
  int bar_h = 35;
  for (int i = 0; i < 6; i++) {
    tft.fillRect(0, 40 + i * bar_h, 240, bar_h - 2, colors[i]);
  }

  // 底部信息
  tft.setTextSize(1);
  tft.setTextColor(ST77XX_WHITE);
  tft.setCursor(5, 260);
  tft.print("TFT: ST7789 240x320");
  tft.setCursor(5, 275);
  tft.print("SPI: CS10 DC8 RST9");
  tft.setCursor(5, 290);
  tft.print("MOSI11 SCK12");
  tft.setCursor(5, 305);
  tft.print("Test FW Ready.");
  tft.setTextSize(1);
}

// ============================================================
// 旋转编码器 ISR
// ============================================================
// 用两个静态变量跟踪编码器 A/B 相上一状态
// 必须放在 ISR 可达的作用域

static volatile uint8_t isr_enc_last_a = HIGH;

void IRAM_ATTR enc_isr() {
  uint8_t a = digitalRead(ENC_A_PIN);
  uint8_t b = digitalRead(ENC_B_PIN);

  // 只在 A 相变化时处理
  if (a != isr_enc_last_a) {
    isr_enc_last_a = a;
    if (a == LOW) {              // A 相下降沿
      if (b == LOW) {
        enc_counter--;           // 逆时针
      } else {
        enc_counter++;           // 顺时针
      }
    }
  }
}

void IRAM_ATTR enc_btn_isr() {
  enc_btn_flag = true;
}

// 7. 麦克风 GPIO 硬件检测 (不需要示波器)
void test_mic_gpio() {
  Serial.println();
  Serial.println(F(">>> Mic GPIO Hardware Check"));
  Serial.println(F("    Use a multimeter to check voltages on mic pins."));
  Serial.println();

  // 1. 释放 I2S, 恢复 GPIO 控制
  if (mic_initialized) {
    mic_i2s.end();
    mic_initialized = false;
  }

  // 2. CLK 引脚 (GPIO14) 手动翻转 —— 用万用表测电压
  Serial.println(F("  [TEST 1] Toggling CLK pin (GPIO14) at ~1kHz..."));
  Serial.println(F("    → Measure GPIO14 with multimeter DC voltage."));
  Serial.println(F("    → Expected: ~1.65V (half of 3.3V, 50% duty square wave)"));
  Serial.println(F("    → If 0V or 3.3V steady: GPIO14 may be shorted or not connected."));
  Serial.println();

  pinMode(MIC_CLK_PIN, OUTPUT);
  for (int i = 0; i < 5; i++) {
    // Toggle GPIO14 rapidly for a few seconds
    unsigned long start = millis();
    while (millis() - start < 2000) {
      digitalWrite(MIC_CLK_PIN, HIGH);
      delayMicroseconds(500);
      digitalWrite(MIC_CLK_PIN, LOW);
      delayMicroseconds(500);
    }
    Serial.print(F("    Toggling... "));
    Serial.println(i + 1);
  }
  digitalWrite(MIC_CLK_PIN, LOW);
  Serial.println(F("  [DONE] Check multimeter reading on GPIO14."));
  Serial.println();

  // 3. DATA 引脚 (GPIO15) 读取 —— 检查是否浮空
  Serial.println(F("  [TEST 2] Reading DATA pin (GPIO15) state..."));
  Serial.println(F("    → Mic DATA is an output. Check if it's floating or driven."));
  Serial.println();

  // 无上拉/下拉，直接读
  pinMode(MIC_DATA_PIN, INPUT);
  int raw_none = 0, raw_high = 0;
  for (int i = 0; i < 100; i++) {
    if (digitalRead(MIC_DATA_PIN) == HIGH) raw_high++;
    delay(1);
  }
  Serial.print(F("    DATA pin (no pull): HIGH="));
  Serial.print(raw_high);
  Serial.print(F("/100  LOW="));
  Serial.print(100 - raw_high);
  Serial.println(raw_high > 80 ? F("  → looks pulled HIGH")
               : raw_high < 20 ? F("  → looks pulled LOW")
               : F("  → looks FLOATING or toggling"));

  // 内部上拉
  pinMode(MIC_DATA_PIN, INPUT_PULLUP);
  int pull_high = 0;
  for (int i = 0; i < 100; i++) {
    if (digitalRead(MIC_DATA_PIN) == HIGH) pull_high++;
    delay(1);
  }
  Serial.print(F("    DATA pin (INPUT_PULLUP): HIGH="));
  Serial.print(pull_high);
  Serial.print(F("/100"));
  Serial.println(pull_high > 90 ? F("  → can be pulled HIGH (not shorted to GND)")
               : F("  → CANNOT be pulled HIGH → possible short to GND!"));

  // 内部下拉
  pinMode(MIC_DATA_PIN, INPUT_PULLDOWN);
  int pull_low = 0;
  for (int i = 0; i < 100; i++) {
    if (digitalRead(MIC_DATA_PIN) == LOW) pull_low++;
    delay(1);
  }
  Serial.print(F("    DATA pin (INPUT_PULLDOWN): LOW="));
  Serial.print(pull_low);
  Serial.print(F("/100"));
  Serial.println(pull_low > 90 ? F("  → can be pulled LOW (not shorted to VDD)")
               : F("  → CANNOT be pulled LOW → possible short to VDD!"));

  Serial.println();
  Serial.println(F("  [INFO] GPIO test complete."));
  Serial.println(F("  [INFO] I2S driver was stopped. Re-enter mic test to re-init."));
  Serial.println();
  print_menu();
}

// ============================================================
// 菜单
// ============================================================
void print_menu() {
  Serial.println(F("+------------------------------------------+"));
  Serial.println(F("|  Select test (type number + Enter):      |"));
  Serial.println(F("|------------------------------------------|"));
  Serial.println(F("|  1  Key scan (KEY1~5 + SW)               |"));
  Serial.println(F("|  2  Rotary Encoder (A/B/Button)          |"));
  Serial.println(F("|  3  MEMS PDM Mic (I2S level meter)       |"));
  Serial.println(F("|  4  TFT LCD (color/draw test)            |"));
  Serial.println(F("|  5  VBUS voltage detect                  |"));
  Serial.println(F("|  6  All-in-one monitor                   |"));
  Serial.println(F("|  7  Mic GPIO check (CLK toggle, DATA read)|"));
  Serial.println(F("|  h  Reprint this menu                    |"));
  Serial.println(F("+------------------------------------------+"));
}

// ============================================================
// 1. 按键扫描测试
// ============================================================
void test_keys() {
  while (Serial.available()) Serial.read();  // 清空残留串口数据

  Serial.println();
  Serial.println(F(">>> Key Scan Test (press 'q' to quit)"));
  Serial.println(F("    Press/release any key to see changes."));
  Serial.println();

  bool prev_keys[5] = {HIGH, HIGH, HIGH, HIGH, HIGH};
  bool prev_sw      = HIGH;

  while (1) {
    if (check_quit()) return;

    for (int i = 0; i < KEY_COUNT; i++) {
      bool cur = digitalRead(KEY_PINS[i]);
      if (cur != prev_keys[i]) {
        delay(30);  // 去抖
        cur = digitalRead(KEY_PINS[i]);
        if (cur != prev_keys[i]) {
          prev_keys[i] = cur;
          Serial.print(F("  ["));
          Serial.print(cur == LOW ? "PRESSED " : "RELEASED");
          Serial.print(F("] "));
          Serial.println(KEY_NAMES[i]);
        }
      }
    }

    bool cur = digitalRead(SW_PIN);
    if (cur != prev_sw) {
      delay(30);
      cur = digitalRead(SW_PIN);
      if (cur != prev_sw) {
        prev_sw = cur;
        Serial.print(F("  [SWITCH] GPIO17 -> "));
        Serial.println(cur == LOW ? "ON" : "OFF");
      }
    }
    delay(5);
  }
}

// ============================================================
// 2. 旋转编码器测试
// ============================================================
void test_encoder() {
  while (Serial.available()) Serial.read();  // 清空残留串口数据

  Serial.println();
  Serial.println(F(">>> Rotary Encoder Test (press 'q' to quit, 'r' to reset)"));
  Serial.println(F("    CW=+  CCW=-  Press=button"));
  Serial.println();

  int32_t last_counter = 0;

  while (1) {
    if (check_quit()) return;

    // 处理重置命令
    if (Serial.available()) {
      char c = Serial.read();
      if (c == 'r' || c == 'R') {
        noInterrupts();
        enc_counter = 0;
        interrupts();
        last_counter = 0;
        Serial.println(F("  [RESET] Counter = 0"));
      }
    }

    // 读取计数值
    int32_t cur;
    noInterrupts();
    cur = enc_counter;
    interrupts();

    if (cur != last_counter) {
      int32_t delta = cur - last_counter;
      last_counter = cur;
      Serial.print(F("  Encoder: "));
      Serial.print(cur);
      Serial.print(F("  ("));
      if (delta > 0) Serial.print('+');
      Serial.print(delta);
      Serial.println(F(")"));
    }

    // 按键
    bool btn;
    noInterrupts();
    btn = enc_btn_flag;
    if (btn) enc_btn_flag = false;
    interrupts();

    if (btn) {
      delay(30);
      if (digitalRead(ENC_BTN_PIN) == LOW) {
        Serial.println(F("  [BTN] Encoder button pressed (GPIO42)"));
      }
    }
    delay(1);
  }
}

// ============================================================
// 3. MEMS PDM 麦克风测试
// ============================================================
void test_mic() {
  while (Serial.available()) Serial.read();

  Serial.println();
  Serial.println(F(">>> MEMS PDM Mic Test"));
  Serial.print(F("    Rate: ")); Serial.print(I2S_SAMPLE_RATE);
  Serial.print(F(" Hz  |  PDM CLK: ")); Serial.print(I2S_SAMPLE_RATE * 64);
  Serial.println(F(" Hz"));
  Serial.println(F("    r=reinit  d=raw dump  q=quit"));
  Serial.println();

  if (!mic_initialized) {
    Serial.println(F("  [WARN] Re-initializing mic..."));
    if (!init_mic_i2s()) {
      Serial.println(F("  [FAIL] Cannot initialize mic."));
      print_menu();
      return;
    }
  }

  int16_t* buf = (int16_t*)malloc(256 * sizeof(int16_t));
  if (!buf) {
    Serial.println(F("  [ERROR] malloc failed"));
    print_menu();
    return;
  }

  unsigned long last_print = 0;
  bool dump_mode = false;

  while (1) {
    while (Serial.available()) {
      char c = Serial.read();
      if (c == 'q' || c == 'Q') {
        free(buf);
        Serial.println(F("  <quit>"));
        Serial.println();
        print_menu();
        return;
      } else if (c == 'r' || c == 'R') {
        mic_i2s.end();
        mic_initialized = false;
        bool ok = init_mic_i2s();
        Serial.print(F("  [INFO] Re-init: "));
        Serial.println(ok ? "OK" : "FAIL");
        last_print = 0;
      } else if (c == 'd' || c == 'D') {
        dump_mode = !dump_mode;
        Serial.print(F("  [INFO] Raw dump: "));
        Serial.println(dump_mode ? "ON" : "OFF");
        last_print = 0;
      }
    }

    // 读取 256 个采样 (ESP_I2S::read 阻塞直到有数据)
    int n = 256;
    for (int i = 0; i < n; i++) {
      buf[i] = (int16_t)mic_i2s.read();
    }

    if (dump_mode) {
      Serial.print(F("  [RAW] "));
      int dump_n = (n > 16) ? 16 : n;
      for (int i = 0; i < dump_n; i++) {
        Serial.print(F("0x"));
        Serial.print((uint16_t)buf[i], HEX);
        Serial.print(' ');
      }
      if (n > 16) Serial.print(F("..."));
      Serial.println();
      delay(200);
      continue;
    }

    int32_t sum = 0;
    int16_t peak = 0;
    int zero_count = 0;
    for (int i = 0; i < n; i++) {
      int16_t s = abs(buf[i]);
      sum += s;
      if (s > peak) peak = s;
      if (buf[i] == 0) zero_count++;
    }
    int16_t avg = sum / n;

    if (millis() - last_print >= 300) {
      last_print = millis();
      // bar: 0~30000 (silence ~40, speech ~8000, blowing ~29000)
      int bar = map(avg, 0, 30000, 0, 40);
      if (bar < 0) bar = 0;
      if (bar > 40) bar = 40;

      Serial.print(F("  ["));
      for (int i = 0; i < bar; i++)  Serial.print('=');
      for (int i = bar; i < 40; i++) Serial.print(' ');
      Serial.print(F("] avg="));
      Serial.print(avg);
      Serial.print(F(" peak="));
      Serial.print(peak);
      Serial.print(F(" n="));
      Serial.print(n);
      Serial.print(F(" z="));
      Serial.print(zero_count * 100 / n);
      Serial.println(F("%"));
    }
  }
}

// ============================================================
// 4. TFT LCD 测试
// ============================================================
void test_lcd() {
  Serial.println();
  Serial.println(F(">>> TFT LCD Test (press 'q' to quit)"));
  Serial.println();

  // --- 子测试 1: 纯色填充 ---
  Serial.println(F("  1/5 Fill screen tests..."));
  const uint16_t fill_colors[] = {ST77XX_RED, ST77XX_GREEN, ST77XX_BLUE,
                                  ST77XX_WHITE, ST77XX_BLACK};
  const char* fill_names[] = {"RED", "GREEN", "BLUE", "WHITE", "BLACK"};
  for (int i = 0; i < 5; i++) {
    if (Serial_peek_quit()) { draw_test_pattern(); print_menu(); return; }
    tft.fillScreen(fill_colors[i]);
    Serial.print(F("    Fill "));
    Serial.println(fill_names[i]);
    delay(500);
  }

  // --- 子测试 2: 几何图形 ---
  Serial.println(F("  2/5 Geometry test..."));
  if (Serial_peek_quit()) { draw_test_pattern(); print_menu(); return; }
  tft.fillScreen(ST77XX_BLACK);
  // 矩形
  tft.drawRect(10, 10, 100, 60, ST77XX_RED);
  tft.fillRect(120, 10, 100, 60, ST77XX_GREEN);
  // 圆
  tft.drawCircle(50, 130, 30, ST77XX_BLUE);
  tft.fillCircle(180, 130, 30, ST77XX_YELLOW);
  // 三角形
  tft.drawTriangle(10, 190, 60, 150, 110, 190, ST77XX_CYAN);
  tft.fillTriangle(130, 190, 180, 150, 230, 190, ST77XX_MAGENTA);
  // 圆角矩形
  tft.fillRoundRect(40, 210, 160, 50, 8, ST77XX_ORANGE);
  delay(2000);

  // --- 子测试 3: 文本 ---
  Serial.println(F("  3/5 Text test..."));
  if (Serial_peek_quit()) { draw_test_pattern(); print_menu(); return; }
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.setCursor(5, 5);    tft.print("Size1: ABC abc 123");
  tft.setTextSize(2);
  tft.setCursor(5, 25);   tft.print("Size2: ABC abc");
  tft.setTextSize(3);
  tft.setCursor(5, 55);   tft.print("Size3: ABC");
  tft.setTextSize(4);
  tft.setCursor(5, 95);   tft.print("Size4: A");
  tft.setTextColor(ST77XX_RED);
  tft.setTextSize(2);
  tft.setCursor(10, 140); tft.print("RED");
  tft.setTextColor(ST77XX_GREEN);
  tft.setCursor(80, 140); tft.print("GREEN");
  tft.setTextColor(ST77XX_BLUE);
  tft.setCursor(160, 140); tft.print("BLUE");
  delay(2000);

  // --- 子测试 4: 渐变条 ---
  Serial.println(F("  4/5 Gradient bars..."));
  if (Serial_peek_quit()) { draw_test_pattern(); print_menu(); return; }
  tft.fillScreen(ST77XX_BLACK);
  for (int y = 0; y < 320; y++) {
    uint8_t r = map(y, 0, 319, 0, 31);
    uint8_t g = map(y, 0, 319, 0, 63);
    uint8_t b = map(y, 0, 319, 0, 31);
    uint16_t c = tft.color565(r, g, b);
    tft.drawFastHLine(0, y, 240, c);
  }
  delay(2000);

  // --- 子测试 5: 像素网格 ---
  Serial.println(F("  5/5 Pixel grid..."));
  if (Serial_peek_quit()) { draw_test_pattern(); print_menu(); return; }
  tft.fillScreen(ST77XX_BLACK);
  for (int x = 0; x < 240; x += 8) {
    tft.drawFastVLine(x, 0, 320, ST77XX_ORANGE);
  }
  for (int y = 0; y < 320; y += 8) {
    tft.drawFastHLine(0, y, 240, ST77XX_ORANGE);
  }
  delay(2000);

  // 恢复
  draw_test_pattern();
  Serial.println(F("  LCD test complete."));
  Serial.println();
  print_menu();
}

// ============================================================
// 5. VBUS 电压检测测试
// ============================================================
void test_vbus() {
  while (Serial.available()) Serial.read();  // 清空残留串口数据

  Serial.println();
  Serial.println(F(">>> VBUS Voltage Detect Test (press 'q' to quit)"));
  Serial.println(F("    VBUS -> 10k -> GPIO16 -> 10k -> GND  (divider = 1/2)"));
  Serial.println();

  while (1) {
    if (check_quit()) return;

    int   raw   = analogRead(VBUS_DET_PIN);
    float vgpio = (raw / 4095.0f) * 3.3f;
    float vbus  = vgpio * 2.0f;
    bool  dig   = digitalRead(VBUS_DET_PIN);

    Serial.print(F("  ADC="));
    Serial.print(raw);
    Serial.print(F("/4095  GPIO="));
    Serial.print(vgpio, 2);
    Serial.print(F("V  VBUS~="));
    Serial.print(vbus, 2);
    Serial.print(F("V  DIGITAL="));
    Serial.print(dig ? "HIGH" : "LOW");

    if (vbus > 4.5f)       Serial.print(F("  [CONNECTED]"));
    else if (vbus < 0.5f)  Serial.print(F("  [DISCONNECTED]"));
    else                    Serial.print(F("  [WARN: abnormal voltage]"));

    Serial.println();
    delay(500);
  }
}

// ============================================================
// 6. 综合监控模式
// ============================================================
void monitor_all() {
  while (Serial.available()) Serial.read();  // 清空残留串口数据

  Serial.println();
  Serial.println(F(">>> All-in-One Monitor (press 'q' to quit)"));
  Serial.println();

  bool prev_keys[5]  = {HIGH, HIGH, HIGH, HIGH, HIGH};
  bool prev_sw       = HIGH;
  unsigned long last_summary = 0;

  while (1) {
    if (check_quit()) return;

    // --- 按键 ---
    for (int i = 0; i < KEY_COUNT; i++) {
      bool cur = digitalRead(KEY_PINS[i]);
      if (cur != prev_keys[i]) {
        delay(30);
        cur = digitalRead(KEY_PINS[i]);
        if (cur != prev_keys[i]) {
          prev_keys[i] = cur;
          Serial.print(F("  [KEY] "));
          Serial.print(KEY_NAMES[i]);
          Serial.println(cur == LOW ? F(" PRESSED") : F(" RELEASED"));
        }
      }
    }

    bool cur = digitalRead(SW_PIN);
    if (cur != prev_sw) {
      delay(30);
      cur = digitalRead(SW_PIN);
      if (cur != prev_sw) {
        prev_sw = cur;
        Serial.print(F("  [SW]  GPIO17 = "));
        Serial.println(cur == LOW ? "ON" : "OFF");
      }
    }

    // --- 编码器 ---
    static int32_t last_enc = 0;
    int32_t cur_enc;
    noInterrupts();
    cur_enc = enc_counter;
    interrupts();
    if (cur_enc != last_enc) {
      int32_t delta = cur_enc - last_enc;
      last_enc = cur_enc;
      Serial.print(F("  [ENC] pos="));
      Serial.print(cur_enc);
      Serial.print(F(" ("));
      if (delta > 0) Serial.print('+');
      Serial.print(delta);
      Serial.println(F(")"));
    }

    bool btn;
    noInterrupts();
    btn = enc_btn_flag;
    if (btn) enc_btn_flag = false;
    interrupts();
    if (btn) {
      delay(30);
      if (digitalRead(ENC_BTN_PIN) == LOW) {
        Serial.println(F("  [ENC_BTN] GPIO42 PRESSED"));
      }
    }

    // --- 定期摘要 (每 2 秒) ---
    if (millis() - last_summary >= 2000) {
      last_summary = millis();

      float vbus = (analogRead(VBUS_DET_PIN) / 4095.0f) * 3.3f * 2.0f;

      int16_t mic_peak = 0;
      for (int i = 0; i < 64; i++) {
        int16_t s = abs((int16_t)mic_i2s.read());
        if (s > mic_peak) mic_peak = s;
      }

      Serial.print(F("  [SUMMARY] VBUS="));
      Serial.print(vbus, 1);
      Serial.print(F("V  MIC_peak="));
      Serial.print(mic_peak);
      Serial.print(F("  Keys=["));
      bool any = false;
      for (int i = 0; i < KEY_COUNT; i++) {
        if (digitalRead(KEY_PINS[i]) == LOW) {
          if (any) Serial.print(',');
          Serial.print(KEY_NAMES[i]);
          any = true;
        }
      }
      if (!any) Serial.print(F("none"));
      Serial.print(F("]  SW="));
      Serial.print(digitalRead(SW_PIN) == LOW ? "ON" : "OFF");
      Serial.print(F("  ENC="));
      noInterrupts();
      Serial.print(enc_counter);
      interrupts();
      Serial.println();
    }

    delay(2);
  }
}

// ============================================================
// 工具函数
// ============================================================

// 检查串口是否有 'q' 输入, 有则打印退出消息并返回 true
// 注意: 只读取单个非 'q' 字符, 不批量消费 (避免干扰其他按键处理)
bool check_quit() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'q' || c == 'Q') {
      Serial.println(F("  <quit>"));
      Serial.println();
      print_menu();
      return true;
    }
    // 非 'q' 字符被丢弃 (换行符、残留控制字符等)
  }
  return false;
}

// 仅检查不消费 (用于循环内部的快速检查)
bool Serial_peek_quit() {
  if (Serial.available()) {
    return (Serial.peek() == 'q' || Serial.peek() == 'Q');
  }
  return false;
}

// ============================================================
// 主循环
// ============================================================
void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r' || c == ' ') return;

    switch (c) {
      case '1': test_keys();     break;
      case '2': test_encoder();  break;
      case '3': test_mic();      break;
      case '4': test_lcd();      break;
      case '5': test_vbus();     break;
      case '6': monitor_all();   break;
      case '7': test_mic_gpio(); break;
      case 'h':
      case 'H': print_menu();    break;
      default:
        Serial.print(F("  Unknown option: "));
        Serial.println(c);
        print_menu();
        break;
    }
  }
}
