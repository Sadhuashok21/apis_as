from django.core.management.base import BaseCommand
from skiltrix.hardware_models import HardwareBoard


class Command(BaseCommand):
    help = "Seeds standard Arduino, ESP32, and ARM Cortex development boards"

    def handle(self, *args, **options):
        boards = [
            {
                "board_id": "arduino_uno",
                "name": "Arduino Uno R3",
                "family": "arduino",
                "mcu": "ATmega328P",
                "clock_speed_mhz": 16,
                "flash_size_mb": 0.032,
                "ram_kb": 2.0,
                "operating_voltage": 5.0,
                "gpio_count": 14,
                "has_wifi": False,
                "has_ble": False,
                "platformio_env": "uno",
                "arduino_fqbn": "arduino:avr:uno",
                "schematic_symbol": "MCU_Module:Arduino_Uno_R3",
                "pinout_data": {
                    "digital_pins": ["D0 (RX)", "D1 (TX)", "D2", "D3 (PWM)", "D4", "D5 (PWM)", "D6 (PWM)", "D7", "D8", "D9 (PWM)", "D10 (SS)", "D11 (MOSI)", "D12 (MISO)", "D13 (SCK/LED)"],
                    "analog_pins": ["A0", "A1", "A2", "A3", "A4 (SDA)", "A5 (SCL)"],
                    "power_pins": ["5V", "3.3V", "GND", "VIN", "RESET", "AREF"]
                },
                "default_template_code": (
                    "// Arduino Uno R3 - Standard Firmware\n"
                    "#include <Arduino.h>\n\n"
                    "#define LED_PIN 13\n\n"
                    "void setup() {\n"
                    "    Serial.begin(115200);\n"
                    "    pinMode(LED_PIN, OUTPUT);\n"
                    "    Serial.println(\"[SkilTrix] Arduino Uno R3 initialized.\");\n"
                    "}\n\n"
                    "void loop() {\n"
                    "    digitalWrite(LED_PIN, HIGH);\n"
                    "    delay(500);\n"
                    "    digitalWrite(LED_PIN, LOW);\n"
                    "    delay(500);\n"
                    "    Serial.println(\"[Heartbeat] Active tick.\");\n"
                    "}\n"
                )
            },
            {
                "board_id": "arduino_nano",
                "name": "Arduino Nano v3",
                "family": "arduino",
                "mcu": "ATmega328P",
                "clock_speed_mhz": 16,
                "flash_size_mb": 0.032,
                "ram_kb": 2.0,
                "operating_voltage": 5.0,
                "gpio_count": 14,
                "has_wifi": False,
                "has_ble": False,
                "platformio_env": "nanoatmega328",
                "arduino_fqbn": "arduino:avr:nano",
                "schematic_symbol": "MCU_Module:Arduino_Nano_v3.x",
                "pinout_data": {
                    "digital_pins": ["D0-D13"],
                    "analog_pins": ["A0-A7"],
                    "power_pins": ["VIN", "5V", "3.3V", "GND", "RESET"]
                },
                "default_template_code": (
                    "// Arduino Nano v3 Firmware\n"
                    "#include <Arduino.h>\n\n"
                    "void setup() {\n"
                    "    Serial.begin(115200);\n"
                    "    pinMode(13, OUTPUT);\n"
                    "}\n\n"
                    "void loop() {\n"
                    "    digitalWrite(13, !digitalRead(13));\n"
                    "    delay(300);\n"
                    "}\n"
                )
            },
            {
                "board_id": "esp32_wroom_32",
                "name": "ESP32 Dev Module (WROOM-32)",
                "family": "esp32",
                "mcu": "ESP32-D0WDQ6 Dual-Core Xtensa LX6",
                "clock_speed_mhz": 240,
                "flash_size_mb": 4.0,
                "ram_kb": 520.0,
                "operating_voltage": 3.3,
                "gpio_count": 34,
                "has_wifi": True,
                "has_ble": True,
                "platformio_env": "esp32dev",
                "arduino_fqbn": "esp32:esp32:esp32",
                "schematic_symbol": "RF_Module:ESP32-WROOM-32",
                "pinout_data": {
                    "strapping_pins": ["GPIO0 (Boot)", "GPIO2 (LED)", "GPIO12", "GPIO15"],
                    "adc1_pins": ["GPIO36 (VP)", "GPIO39 (VN)", "GPIO34", "GPIO35", "GPIO32", "GPIO33"],
                    "dac_pins": ["GPIO25 (DAC1)", "GPIO26 (DAC2)"],
                    "spi_pins": ["MOSI: 23", "MISO: 19", "SCK: 18", "CS: 5"],
                    "i2c_pins": ["SDA: 21", "SCL: 22"],
                    "uart0_pins": ["TX: 1", "RX: 3"]
                },
                "default_template_code": (
                    "// ESP32-WROOM-32 Native Production Firmware\n"
                    "#include <Arduino.h>\n"
                    "#include <WiFi.h>\n\n"
                    "#define LED_PIN 2\n\n"
                    "void setup() {\n"
                    "    Serial.begin(115200);\n"
                    "    pinMode(LED_PIN, OUTPUT);\n"
                    "    Serial.println(\"\\n========================================\");\n"
                    "    Serial.println(\"  SkilTrix ESP32 Production Workspace   \");\n"
                    "    Serial.println(\"========================================\");\n"
                    "    Serial.printf(\"Chip: ESP32 Rev %d | Cores: %d | Freq: %d MHz\\n\",\n"
                    "                  ESP.getChipRevision(), ESP.getChipCores(), ESP.getCpuFreqMHz());\n"
                    "}\n\n"
                    "void loop() {\n"
                    "    digitalWrite(LED_PIN, HIGH);\n"
                    "    delay(200);\n"
                    "    digitalWrite(LED_PIN, LOW);\n"
                    "    delay(800);\n"
                    "    Serial.printf(\"[Uptime: %lu ms] Free Heap: %u bytes\\n\", millis(), ESP.getFreeHeap());\n"
                    "}\n"
                )
            },
            {
                "board_id": "esp32_s3_devkitc",
                "name": "ESP32-S3 DevKitC-1",
                "family": "esp32",
                "mcu": "ESP32-S3 Dual-Core Xtensa LX7",
                "clock_speed_mhz": 240,
                "flash_size_mb": 8.0,
                "ram_kb": 512.0,
                "operating_voltage": 3.3,
                "gpio_count": 45,
                "has_wifi": True,
                "has_ble": True,
                "platformio_env": "esp32-s3-devkitc-1",
                "arduino_fqbn": "esp32:esp32:esp32s3",
                "schematic_symbol": "RF_Module:ESP32-S3-WROOM-1",
                "pinout_data": {
                    "usb_otg": ["GPIO19 (D-)", "GPIO20 (D+)"],
                    "uart0": ["TX: 43", "RX: 44"],
                    "i2c0": ["SDA: 8", "SCL: 9"],
                    "rgb_builtin": "GPIO48"
                },
                "default_template_code": (
                    "// ESP32-S3 AI Edge & High Performance Firmware\n"
                    "#include <Arduino.h>\n\n"
                    "void setup() {\n"
                    "    Serial.begin(115200);\n"
                    "    Serial.println(\"[SkilTrix] ESP32-S3 Dual LX7 Vector Extension Ready.\");\n"
                    "}\n\n"
                    "void loop() {\n"
                    "    Serial.printf(\"Heap: %u | PSRAM: %u\\n\", ESP.getFreeHeap(), ESP.getFreePsram());\n"
                    "    delay(1000);\n"
                    "}\n"
                )
            },
            {
                "board_id": "esp32_c3_devkitm",
                "name": "ESP32-C3 DevKitM-1 (RISC-V)",
                "family": "esp32",
                "mcu": "ESP32-C3 Single-Core 32-bit RISC-V",
                "clock_speed_mhz": 160,
                "flash_size_mb": 4.0,
                "ram_kb": 400.0,
                "operating_voltage": 3.3,
                "gpio_count": 22,
                "has_wifi": True,
                "has_ble": True,
                "platformio_env": "esp32-c3-devkitm-1",
                "arduino_fqbn": "esp32:esp32:esp32c3",
                "schematic_symbol": "RF_Module:ESP32-C3-WROOM-02",
                "pinout_data": {
                    "usb_serial_jtag": ["GPIO18 (D-)", "GPIO19 (D+)"],
                    "uart": ["TX: 21", "RX: 20"],
                    "i2c": ["SDA: 8", "SCL: 9"]
                },
                "default_template_code": (
                    "// ESP32-C3 RISC-V Firmware\n"
                    "#include <Arduino.h>\n\n"
                    "void setup() {\n"
                    "    Serial.begin(115200);\n"
                    "    Serial.println(\"[SkilTrix] ESP32-C3 RISC-V Core online.\");\n"
                    "}\n\n"
                    "void loop() {\n"
                    "    delay(1000);\n"
                    "}\n"
                )
            },
            {
                "board_id": "rp2040_pico",
                "name": "Raspberry Pi Pico",
                "family": "rp2040",
                "mcu": "RP2040 Dual ARM Cortex-M0+",
                "clock_speed_mhz": 133,
                "flash_size_mb": 2.0,
                "ram_kb": 264.0,
                "operating_voltage": 3.3,
                "gpio_count": 30,
                "has_wifi": False,
                "has_ble": False,
                "platformio_env": "pico",
                "arduino_fqbn": "rp2040:rp2040:rpipico",
                "schematic_symbol": "MCU_Module:RaspberryPi_Pico",
                "pinout_data": {
                    "uart0": ["GP0 (TX)", "GP1 (RX)"],
                    "i2c0": ["GP4 (SDA)", "GP5 (SCL)"],
                    "spi0": ["GP16 (MISO)", "GP17 (CS)", "GP18 (SCK)", "GP19 (MOSI)"],
                    "led": "GP25"
                },
                "default_template_code": (
                    "// Raspberry Pi Pico Dual Core Firmware\n"
                    "#include <Arduino.h>\n\n"
                    "void setup() {\n"
                    "    pinMode(LED_BUILTIN, OUTPUT);\n"
                    "}\n\n"
                    "void loop() {\n"
                    "    digitalWrite(LED_BUILTIN, HIGH);\n"
                    "    delay(250);\n"
                    "    digitalWrite(LED_BUILTIN, LOW);\n"
                    "    delay(250);\n"
                    "}\n"
                )
            },
            {
                "board_id": "stm32_bluepill",
                "name": "STM32F103C8T6 'Blue Pill'",
                "family": "stm32",
                "mcu": "STM32F103C8T6 ARM Cortex-M3",
                "clock_speed_mhz": 72,
                "flash_size_mb": 0.064,
                "ram_kb": 20.0,
                "operating_voltage": 3.3,
                "gpio_count": 32,
                "has_wifi": False,
                "has_ble": False,
                "platformio_env": "bluepill_f103c8",
                "arduino_fqbn": "STMicroelectronics:stm32:GenF1",
                "schematic_symbol": "MCU_Module:STM32_BluePill",
                "pinout_data": {
                    "swd": ["PA13 (SWDIO)", "PA14 (SWCLK)"],
                    "usart1": ["PA9 (TX)", "PA10 (RX)"],
                    "i2c1": ["PB6 (SCL)", "PB7 (SDA)"]
                },
                "default_template_code": (
                    "// STM32 Blue Pill ARM Cortex-M3 Firmware\n"
                    "#include <Arduino.h>\n\n"
                    "void setup() {\n"
                    "    pinMode(PC13, OUTPUT);\n"
                    "}\n\n"
                    "void loop() {\n"
                    "    digitalWrite(PC13, LOW);  // Active low on BluePill\n"
                    "    delay(500);\n"
                    "    digitalWrite(PC13, HIGH);\n"
                    "    delay(500);\n"
                    "}\n"
                )
            }
        ]

        created_count = 0
        updated_count = 0
        for b in boards:
            obj, created = HardwareBoard.objects.update_or_create(
                board_id=b["board_id"],
                defaults=b
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Hardware boards seeded successfully: {created_count} created, {updated_count} updated."
        ))

