"""
CircuitSathi Deterministic Safety & Calculation Engine
Provides deterministic electrical rules, safety checks, calculations, and hazard warnings.
Never delegates basic arithmetic or life-safety checks to probabilistic language models.
"""

from typing import Any
import math

# Standard E12 Resistor values (multiplier base)
E12_SERIES = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]


def find_nearest_standard_resistor(resistance_ohms: float) -> float:
    """Find the nearest standard E12 resistor value equal to or greater than target."""
    if resistance_ohms <= 0:
        return 0.0
    
    exponent = math.floor(math.log10(resistance_ohms))
    base = resistance_ohms / (10 ** exponent)
    
    # Pick next higher standard value
    selected_base = None
    for val in E12_SERIES:
        if val >= round(base, 2):
            selected_base = val
            break
            
    if selected_base is None:
        # Value exceeds 8.2 -> roll over to 1.0 * 10^(exponent + 1)
        return round(1.0 * (10 ** (exponent + 1)), 2)
            
    return round(selected_base * (10 ** exponent), 2)


def calculate_led_resistor(
    supply_voltage: float,
    forward_voltage: float = 2.0,
    desired_current_ma: float = 15.0
) -> dict[str, Any]:
    """
    Deterministically calculates LED current-limiting resistor, power dissipation,
    and recommended standard E12 component rating.
    """
    if supply_voltage <= forward_voltage:
        return {
            "success": False,
            "error": f"Supply voltage ({supply_voltage}V) must be greater than LED forward voltage ({forward_voltage}V).",
        }
    
    current_amperes = desired_current_ma / 1000.0
    voltage_drop = supply_voltage - forward_voltage
    ideal_resistance = voltage_drop / current_amperes
    standard_resistor = find_nearest_standard_resistor(ideal_resistance)
    
    actual_current_ma = (voltage_drop / standard_resistor) * 1000.0
    actual_power_watts = (voltage_drop ** 2) / standard_resistor
    
    # Derating rule: Use 2x power margin for reliability
    recommended_rating_watts = 0.25 if actual_power_watts <= 0.125 else (
        0.5 if actual_power_watts <= 0.25 else 1.0
    )
    
    return {
        "success": True,
        "supply_voltage_v": supply_voltage,
        "forward_voltage_v": forward_voltage,
        "target_current_ma": desired_current_ma,
        "voltage_drop_v": round(voltage_drop, 2),
        "ideal_resistance_ohms": round(ideal_resistance, 2),
        "standard_e12_resistor_ohms": standard_resistor,
        "actual_current_ma": round(actual_current_ma, 2),
        "power_dissipation_watts": round(actual_power_watts, 4),
        "recommended_package_rating": f"{recommended_rating_watts}W",
    }


def calculate_voltage_divider(
    vin: float,
    r1_ohms: float,
    r2_ohms: float
) -> dict[str, Any]:
    """Calculate unloaded voltage divider output and quiescent current."""
    if r1_ohms + r2_ohms <= 0:
        return {"success": False, "error": "Total resistance must be strictly positive."}
    
    total_r = r1_ohms + r2_ohms
    vout = vin * (r2_ohms / total_r)
    current_ma = (vin / total_r) * 1000.0
    p_r1 = ((vin - vout) ** 2) / r1_ohms
    p_r2 = (vout ** 2) / r2_ohms
    
    return {
        "success": True,
        "vin": vin,
        "r1_ohms": r1_ohms,
        "r2_ohms": r2_ohms,
        "vout": round(vout, 3),
        "quiescent_current_ma": round(current_ma, 3),
        "power_r1_watts": round(p_r1, 4),
        "power_r2_watts": round(p_r2, 4),
    }


def check_circuit_safety(
    supply_voltage: float,
    current_draw_a: float,
    has_inductive_load: bool = False,
    is_battery_powered: bool = False,
    battery_type: str = "",
    controller_logic_v: float = 3.3,
    peripheral_logic_v: float = 3.3,
) -> list[dict[str, str]]:
    """
    Evaluates safety hazards and electrical constraints deterministically.
    Returns categorized warnings and actionable engineering checks.
    """
    warnings: list[dict[str, str]] = []
    
    # 1. Hazardous voltage check (SELV threshold: 50V DC / 30V AC RMS)
    if supply_voltage >= 50.0:
        warnings.append({
            "severity": "CRITICAL HAZARD",
            "category": "High Voltage Contact Risk",
            "message": f"Circuit voltage ({supply_voltage}V) exceeds Extra-Low Voltage (SELV) safety limit (50V DC). Risk of electric shock. Never touch live conductors, and ensure safety enclosures and insulated test probes are used."
        })
    elif supply_voltage >= 24.0:
        warnings.append({
            "severity": "WARNING",
            "category": "Elevated Voltage",
            "message": f"Operating at {supply_voltage}V. Verify capacitor voltage ratings are at least 35V or 50V (minimum 25-50% safety derating)."
        })
        
    # 2. High Current check
    if current_draw_a >= 3.0:
        warnings.append({
            "severity": "WARNING",
            "category": "High Current / Trace Heating",
            "message": f"Total current ({current_draw_a}A) will cause substantial $I^2R$ trace heating on standard 1oz copper PCB traces or breadboard spring contacts. Use breadboard power rails carefully or wire directly with at least 18-20 AWG wiring."
        })

    # 3. Inductive Load & Flyback Protection Check
    if has_inductive_load:
        warnings.append({
            "severity": "WARNING",
            "category": "Inductive Kickback (Back-EMF)",
            "message": "Inductive loads (motors, relays, solenoids) generate severe negative voltage spikes $(V = -L \\cdot di/dt)$ during PWM turn-off. A flyback/freewheeling diode (e.g. 1N4007 or Schottky 1N5819) across the coil, or an integrated H-Bridge with internal clamping diodes, is mandatory to prevent destroying switching MOSFETs/transistors."
        })

    # 4. Battery Safety
    if is_battery_powered:
        bat_lower = battery_type.lower()
        if "lipo" in bat_lower or "li-ion" in bat_lower or "18650" in bat_lower:
            warnings.append({
                "severity": "CRITICAL HAZARD",
                "category": "Lithium Battery Thermal Runaway",
                "message": "Lithium-based cells (LiPo / Li-Ion / 18650) require a dedicated Battery Management System (BMS) / Protection Circuit Module (PCM). Never discharge below 3.0V per cell or overcharge above 4.2V. Short-circuits can lead to instantaneous fire or explosion."
            })
        else:
            warnings.append({
                "severity": "ADVISORY",
                "category": "Battery Discharge & Reverse Polarity",
                "message": "Include reverse polarity protection (Schottky diode or P-channel MOSFET gate switch) and an inline fuse to protect against accidental reverse battery insertion."
            })

    # 5. Logic Level Mismatch
    if abs(controller_logic_v - peripheral_logic_v) > 0.5:
        if controller_logic_v < peripheral_logic_v:
            warnings.append({
                "severity": "WARNING",
                "category": "Logic Level Overvoltage Mismatch",
                "message": f"Controller logic ({controller_logic_v}V) is lower than peripheral logic ({peripheral_logic_v}V). Connecting a {peripheral_logic_v}V output directly into a {controller_logic_v}V GPIO pin (e.g. ESP32/STM32) without a bidirectional level shifter or resistor divider will damage the microcontroller's internal ESD protection diodes."
            })
        else:
            warnings.append({
                "severity": "ADVISORY",
                "category": "Logic Threshold Sensitivity",
                "message": f"Controller output ({controller_logic_v}V) may not reliably meet high-level input threshold $(V_{{IH}})$ of a {peripheral_logic_v}V peripheral. Verify $V_{{IH}}$ specifications in the datasheet."
            })

    return warnings
