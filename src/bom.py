"""
CircuitSathi Bill of Materials (BOM) Engine
Provides structured Pydantic schemas, deterministic financial math (Python-calculated subtotals),
validation, Excel (.xlsx) formatting, and CSV export.
Never invents prices or uses LLM arithmetic for accounting.
"""

from pathlib import Path
from typing import Any, Optional
import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from pydantic import BaseModel, Field, field_validator


class BOMItem(BaseModel):
    """Individual line item in an engineering Bill of Materials."""
    name: str = Field(..., description="Component or subsystem name")
    quantity: int = Field(default=1, ge=1, description="Required quantity (positive integer)")
    purpose: str = Field(..., description="Role/subsystem in the circuit")
    specifications: str = Field(..., description="Electrical rating, tolerance, package")
    suggested_part_number: Optional[str] = Field(default="Standard Component", description="Standard part number")
    unit_price_inr: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Verified or user-specified unit price in INR. None if unverified."
    )
    is_price_verified: bool = Field(default=False, description="True if price comes from verified source/user input")
    source_reference: Optional[str] = Field(default="Engineering Best Practice", description="Datasheet or supplier reference")
    compatibility_notes: Optional[str] = Field(default="", description="Voltage levels, logic matching, decoupling")
    warning: Optional[str] = Field(default="", description="Unresolved risk or safety warning")

    @field_validator("quantity")
    @classmethod
    def check_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v

    @property
    def subtotal_inr(self) -> Optional[float]:
        """Deterministically calculated subtotal in Python."""
        if self.unit_price_inr is not None:
            return round(self.quantity * self.unit_price_inr, 2)
        return None


class BOMProject(BaseModel):
    """Complete project BOM specification."""
    project_name: str
    project_objective: str
    supply_voltage: str
    controller: str
    budget_inr: Optional[float] = None
    items: list[BOMItem] = Field(default_factory=list)
    unresolved_constraints: list[str] = Field(default_factory=list)

    @property
    def verified_total_inr(self) -> float:
        """Sum of all items with verified or entered prices."""
        total = 0.0
        for item in self.items:
            sub = item.subtotal_inr
            if sub is not None:
                total += sub
        return round(total, 2)

    @property
    def unpriced_items_count(self) -> int:
        """Number of items lacking verified pricing."""
        return sum(1 for item in self.items if item.unit_price_inr is None)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert BOM to pandas DataFrame for tabular display and export."""
        rows = []
        for idx, it in enumerate(self.items, 1):
            sub = it.subtotal_inr
            rows.append({
                "Item #": idx,
                "Component Name": it.name,
                "Qty": it.quantity,
                "Purpose": it.purpose,
                "Specifications": it.specifications,
                "Part Number": it.suggested_part_number or "-",
                "Unit Price (INR)": f"₹{it.unit_price_inr:.2f}" if it.unit_price_inr is not None else "Unverified",
                "Subtotal (INR)": f"₹{sub:.2f}" if sub is not None else "Unverified",
                "Price Status": "Verified" if it.is_price_verified else "Estimated / Pending",
                "Source Reference": it.source_reference or "-",
                "Compatibility & Warnings": f"{it.compatibility_notes} {it.warning}".strip() or "OK"
            })
        return pd.DataFrame(rows)

    def export_csv(self) -> str:
        """Export BOM as RFC-4180 compliant CSV string."""
        df = self.to_dataframe()
        return df.to_csv(index=False)

    def export_excel_bytes(self) -> bytes:
        """
        Generate a styled, professional Excel (.xlsx) workbook using OpenPyXL.
        Includes title banner, metadata header, styled columns, and verified cost summary.
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "CircuitSathi BOM"

        # Styling definitions
        font_title = Font(name="Segoe UI", size=15, bold=True, color="0F172A")
        font_sub = Font(name="Segoe UI", size=10, italic=True, color="475569")
        font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        font_body = Font(name="Segoe UI", size=10, color="1E293B")
        font_bold = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
        
        fill_header = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Deep Navy
        fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        fill_summary = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")

        thin_border = Border(
            left=Side(style='thin', color="CBD5E1"),
            right=Side(style='thin', color="CBD5E1"),
            top=Side(style='thin', color="CBD5E1"),
            bottom=Side(style='thin', color="CBD5E1")
        )

        # Title Block
        ws.merge_cells("A1:K1")
        ws["A1"] = f"CircuitSathi — Bill of Materials: {self.project_name}"
        ws["A1"].font = font_title
        ws["A1"].alignment = Alignment(vertical="center")

        ws.merge_cells("A2:K2")
        ws["A2"] = f"Objective: {self.project_objective} | Supply: {self.supply_voltage} | Controller: {self.controller}"
        ws["A2"].font = font_sub

        # Table Headers
        headers = [
            "Item #", "Component Name", "Qty", "Purpose", "Specifications",
            "Part Number", "Unit Price (INR)", "Subtotal (INR)", "Price Verified?",
            "Source Reference", "Compatibility & Safety Notes"
        ]
        
        ws.append([])  # Row 3 empty
        ws.append(headers)  # Row 4
        header_row = 4
        
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

        # Populate rows
        curr_row = 5
        for idx, item in enumerate(self.items, 1):
            sub = item.subtotal_inr
            row_data = [
                idx,
                item.name,
                item.quantity,
                item.purpose,
                item.specifications,
                item.suggested_part_number or "-",
                f"{item.unit_price_inr:.2f}" if item.unit_price_inr is not None else "Unverified",
                f"{sub:.2f}" if sub is not None else "Unverified",
                "Yes" if item.is_price_verified else "No",
                item.source_reference or "-",
                f"{item.compatibility_notes} {item.warning}".strip() or "-"
            ]
            ws.append(row_data)

            # Style row
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=curr_row, column=col_idx)
                cell.font = font_body
                cell.border = thin_border
                cell.alignment = Alignment(
                    horizontal="center" if col_idx in [1, 3, 7, 8, 9] else "left",
                    vertical="center",
                    wrap_text=True
                )
                if idx % 2 == 0:
                    cell.fill = fill_zebra
            curr_row += 1

        # Summary Row
        ws.append([])
        curr_row += 1
        ws.merge_cells(f"A{curr_row}:G{curr_row}")
        ws[f"A{curr_row}"] = f"Total Verified Cost ({len(self.items) - self.unpriced_items_count} of {len(self.items)} priced items):"
        ws[f"A{curr_row}"].font = font_bold
        ws[f"A{curr_row}"].alignment = Alignment(horizontal="right")

        ws[f"H{curr_row}"] = f"₹{self.verified_total_inr:.2f}"
        ws[f"H{curr_row}"].font = font_bold
        ws[f"H{curr_row}"].fill = fill_summary
        ws[f"H{curr_row}"].alignment = Alignment(horizontal="center")

        if self.budget_inr:
            curr_row += 1
            ws.merge_cells(f"A{curr_row}:G{curr_row}")
            ws[f"A{curr_row}"] = f"Allocated Budget: ₹{self.budget_inr:.2f} | Remaining Margin:"
            ws[f"A{curr_row}"].font = font_bold
            ws[f"A{curr_row}"].alignment = Alignment(horizontal="right")
            margin = self.budget_inr - self.verified_total_inr
            ws[f"H{curr_row}"] = f"₹{margin:.2f}"
            ws[f"H{curr_row}"].font = font_bold
            ws[f"H{curr_row}"].alignment = Alignment(horizontal="center")

        # Column widths adjustment
        col_widths = {
            "A": 8, "B": 24, "C": 8, "D": 22, "E": 25,
            "F": 18, "G": 16, "H": 16, "I": 15, "J": 22, "K": 32
        }
        for col_letter, width in col_widths.items():
            ws.column_dimensions[col_letter].width = width

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
