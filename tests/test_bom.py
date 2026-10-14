"""
Tests for Bill of Materials (BOM) schema validation, math, and export.
"""

import pytest
import pandas as pd
from src.bom import BOMItem, BOMProject


def test_bom_item_validation():
    """Verify validation of BOMItem fields."""
    # Valid item with price
    item1 = BOMItem(
        name="TB6612FNG Driver Module",
        quantity=2,
        purpose="Drive two N20 DC gearmotors",
        specifications="4.5V-15V motor, 1.2A continuous",
        suggested_part_number="TB6612FNG",
        unit_price_inr=150.0,
        is_price_verified=True
    )
    assert item1.subtotal_inr == 300.0

    # Unverified item without price
    item2 = BOMItem(
        name="Custom Acrylic Chassis",
        quantity=1,
        purpose="Robot structural frame",
        specifications="3mm laser-cut acrylic",
        unit_price_inr=None,
        is_price_verified=False
    )
    assert item2.subtotal_inr is None

    # Invalid negative quantity
    with pytest.raises(Exception):
        BOMItem(
            name="Resistor",
            quantity=0,
            purpose="Pullup",
            specifications="10k 0.25W"
        )


def test_bom_project_total_calculation():
    """Verify deterministic financial arithmetic on mixed priced items."""
    item1 = BOMItem(
        name="ESP32 DevKit",
        quantity=1,
        purpose="MCU",
        specifications="3.3V, Dual Core",
        unit_price_inr=450.0,
        is_price_verified=True
    )
    item2 = BOMItem(
        name="100nF Ceramic Capacitor",
        quantity=5,
        purpose="Decoupling",
        specifications="50V X7R",
        unit_price_inr=2.5,
        is_price_verified=True
    )
    item3 = BOMItem(
        name="Custom Motor Bracket",
        quantity=2,
        purpose="Mounting",
        specifications="Aluminium 6061",
        unit_price_inr=None
    )

    project = BOMProject(
        project_name="Line Following Robot",
        project_objective="Autonomous high-speed track navigation",
        supply_voltage="7.4V 2S LiPo",
        controller="ESP32",
        budget_inr=2000.0,
        items=[item1, item2, item3]
    )

    # 1 * 450 + 5 * 2.5 = 450 + 12.5 = 462.5
    assert project.verified_total_inr == 462.5
    assert project.unpriced_items_count == 1

    # Verify DataFrame structure
    df = project.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "Subtotal (INR)" in df.columns


def test_bom_export_excel_and_csv():
    """Verify Excel .xlsx bytes and CSV string generation."""
    item = BOMItem(
        name="LM7805 Regulator",
        quantity=2,
        purpose="5V step-down",
        specifications="TO-220, 1A",
        unit_price_inr=25.0,
        is_price_verified=True
    )
    project = BOMProject(
        project_name="Power Supply",
        project_objective="Dual rail 5V/3.3V supply",
        supply_voltage="12V DC Adapter",
        controller="None",
        items=[item]
    )

    csv_data = project.export_csv()
    assert "LM7805 Regulator" in csv_data
    assert "₹50.00" in csv_data or "50.00" in csv_data

    xlsx_bytes = project.export_excel_bytes()
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 1000
    # Check standard zip/excel magic header PK\x03\x04
    assert xlsx_bytes[:4] == b"PK\x03\x04"
