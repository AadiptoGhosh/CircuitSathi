"""
Generate authentic test PDF datasheets using PyMuPDF.
Creates sample datasheets with real electrical parameters, pinouts, and page numbers.
"""

from pathlib import Path
import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BASE_DIR / "data" / "sample_docs"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def create_tb6612fng_datasheet():
    """Generates a 3-page authentic TB6612FNG datasheet PDF."""
    pdf_path = SAMPLE_DIR / "TB6612FNG_Datasheet.pdf"
    doc = pymupdf.open()

    # --- Page 1: Features & Overview ---
    page1 = doc.new_page(width=595, height=842)
    text1 = """TOSHIBA Bi-CD Integrated Circuit Silicon Monolithic
TB6612FNG
Driver IC for Dual DC Motor

1. Description & Features
The TB6612FNG is a driver IC for dual DC motor with output transistor in LD MOS structure with low ON-resistor.
Two input signals, IN1 and IN2, can choose one of four modes such as CW, CCW, short brake, and stop mode.

Key Features:
- Power supply voltage: Large motor drive capability (VM = 15 V max)
- Output current: IOUT = 1.2 A (average) / 3.2 A (peak pulse < 20 ms)
- Output low ON resistance: Ron = 0.5 ohm (upper + lower typ. at VM = 5V)
- Standby (power save) system: STBY pin (Active HIGH)
- Built-in thermal shutdown (TSD) circuit
- Built-in low voltage detection circuit (UVLO: VCC < 2.2V typ)
- Small package: SSOP24 (0.65 mm pin pitch)

Absolute Maximum Ratings (Ta = 25 deg C):
- Supply voltage (VM): 15.0 V
- Control supply voltage (VCC): 6.0 V
- Output current (IOUT peak): 3.2 A
- Operating temperature (Topr): -20 to 85 deg C
- Storage temperature (Tstg): -55 to 150 deg C
"""
    rect = pymupdf.Rect(50, 50, 550, 800)
    page1.insert_textbox(rect, text1, fontsize=11, fontname="helv")

    # --- Page 2: Pin Functions & Recommended Operating Conditions ---
    page2 = doc.new_page(width=595, height=842)
    text2 = """TB6612FNG Technical Specification
Page 2: Pin Functions and Recommended Operating Conditions

2. Pin Functions
- Pin 24 (VM1) & Pin 13 (VM2, VM3): Motor supply voltage pins (4.5 V to 13.5 V recommended).
- Pin 20 (VCC): Control logic supply voltage pin (2.7 V to 5.5 V).
- Pin 19 (STBY): Standby input pin. HIGH = Normal operation, LOW = Standby (all outputs Hi-Z).
- Pin 21 (PWMA) & Pin 16 (PWMB): PWM speed control input (up to 100 kHz frequency).
- Pin 22 (AIN1) & Pin 23 (AIN2): Motor A direction logic control pins.
- Pin 17 (BIN1) & Pin 18 (BIN2): Motor B direction logic control pins.
- Pin 1, 2 (AO1) & Pin 5, 6 (AO2): Motor A driver outputs.
- Pin 7, 8 (BO2) & Pin 11, 12 (BO1): Motor B driver outputs.
- Pin 3, 4, 9, 10, 14, 15 (PGND, SGND): Ground connection pins. Must connect to system GND.

3. Recommended Operating Conditions (Ta = -20 to 85 deg C):
- Supply voltage (VM): 4.5 V to 13.5 V
- Logic supply voltage (VCC): 2.7 V to 5.5 V
- Output current (IOUT continuous): 1.0 A (per channel)
- PWM frequency (fPWM): Up to 100 kHz
"""
    page2.insert_textbox(rect, text2, fontsize=11, fontname="helv")

    # --- Page 3: Control Logic Truth Table & Thermal Protection ---
    page3 = doc.new_page(width=595, height=842)
    text3 = """TB6612FNG Technical Specification
Page 3: Truth Table and Application Considerations

4. Input/Output Control Function Truth Table
IN1 | IN2 | PWM | STBY | OUT1 | OUT2 | Mode
 H  |  L  |  H  |  H   |  H   |  L   | Clockwise (CW)
 L  |  H  |  H  |  H   |  L   |  H   | Counter-Clockwise (CCW)
 H  |  H  |  X  |  H   |  L   |  L   | Short Brake
 L  |  L  |  X  |  H   | OFF  | OFF  | Stop (Hi-Z coast)
 X  |  X  |  X  |  L   | OFF  | OFF  | Standby Mode (Outputs Hi-Z, low current)

5. Thermal Shutdown and Circuit Protection
- Thermal shutdown operates at junction temperature Tj >= 175 deg C (typ).
- Hysteresis temperature is approximately 40 deg C.
- Bypass capacitor: Connect a 0.1 uF ceramic capacitor and a 10 uF electrolytic capacitor
  between VM and GND, and between VCC and GND, as close as possible to the IC pins.
- Flyback protection: Internal parasitic diodes clamp inductive flyback from motor coils.
"""
    page3.insert_textbox(rect, text3, fontsize=11, fontname="helv")

    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


def create_lm7805_datasheet():
    """Generates a 2-page authentic LM7805 voltage regulator datasheet PDF."""
    pdf_path = SAMPLE_DIR / "LM7805_Datasheet.pdf"
    doc = pymupdf.open()
    rect = pymupdf.Rect(50, 50, 550, 800)

    page1 = doc.new_page(width=595, height=842)
    text1 = """TEXAS INSTRUMENTS / NATIONAL SEMICONDUCTOR
LM7805 3-Terminal 1.5A Positive Voltage Regulator

1. General Description
The LM7805 is a 3-terminal positive voltage regulator designed for local on-card regulation.
It employs internal current-limiting, thermal-shutdown, and safe-area compensation.

Key Specifications:
- Output Voltage: 5.0 V DC (+/- 4% over temperature)
- Maximum Input Voltage: 35 V DC (Absolute Maximum)
- Recommended Input Voltage Range: 7.0 V to 25.0 V
- Dropout Voltage: 2.0 V typical at IOUT = 1.0 A
- Output Current: Up to 1.5 A with adequate heatsinking
- Quiescent Current: 5.0 mA typical (8.0 mA max)
- Ripple Rejection: 78 dB at 120 Hz

Pin Assignment (TO-220 Package):
- Pin 1: Input (Unregulated DC, minimum 7V)
- Pin 2: Ground
- Pin 3: Output (+5.0V Regulated)
"""
    page1.insert_textbox(rect, text1, fontsize=11, fontname="helv")

    page2 = doc.new_page(width=595, height=842)
    text2 = """LM7805 3-Terminal Positive Voltage Regulator
Page 2: Design Considerations & Thermal Management

2. Thermal Considerations
Power dissipation is calculated as:
PD = (VIN - VOUT) * IOUT + (VIN * IQ)
For example, with VIN = 12 V, VOUT = 5 V, and IOUT = 500 mA:
PD = (12 - 5) * 0.5 A = 3.5 Watts.
Without a heatsink, the thermal resistance junction-to-ambient (RthetaJA) is 50 deg C/W.
Temperature rise = 3.5 W * 50 deg C/W = 175 deg C above ambient!
The IC will quickly reach thermal shutdown (150 deg C junction). A substantial heatsink is mandatory.

3. External Capacitors
- Input Capacitor: A 0.33 uF ceramic or tantalum capacitor is required if the regulator
  is located more than 2 inches from the power supply filter capacitor.
- Output Capacitor: An output capacitor of 0.1 uF ceramic is recommended to improve
  transient response and stability.
"""
    page2.insert_textbox(rect, text2, fontsize=11, fontname="helv")

    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


if __name__ == "__main__":
    create_tb6612fng_datasheet()
    create_lm7805_datasheet()
