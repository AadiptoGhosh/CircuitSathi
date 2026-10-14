"""
Tests for Deterministic Safety & Calculation Engine.
"""

from src.safety import (
    calculate_led_resistor,
    calculate_voltage_divider,
    find_nearest_standard_resistor,
    check_circuit_safety
)


def test_find_nearest_standard_resistor():
    """Verify E12 standard resistor selection."""
    assert find_nearest_standard_resistor(215) == 220.0
    assert find_nearest_standard_resistor(980) == 1000.0  # 1.0 * 10^3
    assert find_nearest_standard_resistor(4500) == 4700.0
    assert find_nearest_standard_resistor(0) == 0.0


def test_calculate_led_resistor():
    """Verify deterministic LED resistor calculation."""
    # 5V supply, 2V forward drop, 15mA target current
    # Ideal R = (5 - 2) / 0.015 = 200 ohms -> nearest E12 is 220 ohms
    res = calculate_led_resistor(supply_voltage=5.0, forward_voltage=2.0, desired_current_ma=15.0)
    assert res["success"] is True
    assert res["voltage_drop_v"] == 3.0
    assert res["ideal_resistance_ohms"] == 200.0
    assert res["standard_e12_resistor_ohms"] == 220.0
    assert round(res["actual_current_ma"], 1) == 13.6
    assert res["power_dissipation_watts"] > 0
    assert res["recommended_package_rating"] == "0.25W"

    # Test error when supply voltage is less than forward voltage
    err_res = calculate_led_resistor(supply_voltage=1.8, forward_voltage=2.0)
    assert err_res["success"] is False
    assert "must be greater than" in err_res["error"]


def test_calculate_voltage_divider():
    """Verify voltage divider calculations."""
    # 12V in, R1=10k, R2=10k -> 6V out
    res = calculate_voltage_divider(vin=12.0, r1_ohms=10000, r2_ohms=10000)
    assert res["success"] is True
    assert res["vout"] == 6.0
    assert res["quiescent_current_ma"] == 0.6
    assert res["power_r1_watts"] == 0.0036


def test_check_circuit_safety_critical_voltage():
    """Verify critical hazard triggers above 50V DC."""
    warnings = check_circuit_safety(
        supply_voltage=60.0,
        current_draw_a=1.0,
        has_inductive_load=False
    )
    severities = [w["severity"] for w in warnings]
    assert "CRITICAL HAZARD" in severities
    assert any("SELV" in w["message"] for w in warnings)


def test_check_circuit_safety_inductive_flyback():
    """Verify inductive flyback warning when motors are present."""
    warnings = check_circuit_safety(
        supply_voltage=12.0,
        current_draw_a=1.5,
        has_inductive_load=True
    )
    categories = [w["category"] for w in warnings]
    assert "Inductive Kickback (Back-EMF)" in categories


def test_check_circuit_safety_logic_mismatch():
    """Verify logic level warning when 5V logic meets 3.3V controller."""
    warnings = check_circuit_safety(
        supply_voltage=5.0,
        current_draw_a=0.2,
        controller_logic_v=3.3,
        peripheral_logic_v=5.0
    )
    categories = [w["category"] for w in warnings]
    assert "Logic Level Overvoltage Mismatch" in categories


def test_check_circuit_safety_lithium_battery():
    """Verify critical battery safety warning for LiPo."""
    warnings = check_circuit_safety(
        supply_voltage=7.4,
        current_draw_a=2.0,
        is_battery_powered=True,
        battery_type="2S LiPo battery"
    )
    categories = [w["category"] for w in warnings]
    assert "Lithium Battery Thermal Runaway" in categories
