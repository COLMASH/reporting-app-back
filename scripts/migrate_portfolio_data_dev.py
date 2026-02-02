"""
Development Portfolio Data Migration Script

This script generates multiple monthly portfolio reports from a single Excel file
by duplicating data with different report_date values. This is useful for testing
the portfolio UI with multiple months of data.

Usage:
    uv run python scripts/migrate_portfolio_data_dev.py [--file PATH] [--base-date DATE] [--additional-months N]

Example:
    # Default: 4 reports (May-Aug 2025)
    uv run python scripts/migrate_portfolio_data_dev.py

    # Custom: 6 reports starting from Jan 2025
    uv run python scripts/migrate_portfolio_data_dev.py --base-date 2025-01-30 --additional-months 5
"""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database.core import SessionLocal
from src.modules.portfolio.models import Asset, RealEstateAsset, StructuredNote


# =============================================================================
# Helper Functions (copied from production script)
# =============================================================================


def clean_numeric_value(value) -> Decimal | None:
    """Convert value to Decimal, handling NaN, empty values, and formatting."""
    if pd.isna(value) or value == "" or value == "-":
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return Decimal(str(value))
    except (ValueError, Exception):
        return None


def clean_string_value(value) -> str | None:
    """Clean string value, return None for empty/NaN values."""
    if pd.isna(value) or value == "" or value == "-":
        return None
    return str(value).strip()


def clean_date_value(value) -> date | None:
    """Convert value to date object."""
    if pd.isna(value) or value == "" or value == "-":
        return None
    try:
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        return None
    except (ValueError, Exception):
        return None


# =============================================================================
# Date Generation
# =============================================================================


def generate_report_dates(base_date: date, num_additional_months: int = 3) -> list[date]:
    """
    Generate a list of report dates starting from base_date.

    Args:
        base_date: The original report date (e.g., 2025-05-30)
        num_additional_months: Number of additional months to generate

    Returns:
        List of dates [base_date, base_date+1mo, base_date+2mo, ...]
    """
    dates = [base_date]
    for i in range(1, num_additional_months + 1):
        dates.append(base_date + relativedelta(months=i))
    return dates


# =============================================================================
# Data Clearing
# =============================================================================


def clear_existing_data(db: SessionLocal) -> None:
    """Clear all existing portfolio data."""
    print("\n[Clearing existing portfolio data...]")

    structured_count = db.query(StructuredNote).count()
    real_estate_count = db.query(RealEstateAsset).count()
    asset_count = db.query(Asset).count()

    # Delete assets (will cascade to structured_notes and real_estate_assets)
    db.query(Asset).delete()
    db.commit()

    print(f"   Deleted {asset_count} assets")
    print(f"   Deleted {structured_count} structured notes (cascade)")
    print(f"   Deleted {real_estate_count} real estate assets (cascade)")


# =============================================================================
# Import Functions (Multi-Report)
# =============================================================================


def import_various_sheet_multi_report(
    excel_file: str,
    db: SessionLocal,
    report_dates: list[date],
) -> tuple[int, list[str]]:
    """
    Import main asset data from Various sheet for multiple report dates.

    Returns: (total_assets_created, errors)
    """
    print(f"\n[Importing Various sheet for {len(report_dates)} report dates...]")

    df = pd.read_excel(excel_file, sheet_name="Various", skiprows=1)

    assets_created = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            display_id = int(row["ID"]) if pd.notna(row.get("ID")) else None
            if not display_id:
                continue

            # Create one asset per report date
            for report_date in report_dates:
                asset = Asset(
                    display_id=display_id,
                    report_date=report_date,  # Use generated date
                    holding_company=clean_string_value(row.get("holding_company")),
                    ownership_holding_entity=clean_string_value(row.get("ownership_holding_entity")) or "Unknown",
                    managing_entity=clean_string_value(row.get("managing_entity")) or "Unknown",
                    asset_group=clean_string_value(row.get("asset_group")),
                    asset_type=clean_string_value(row.get("asset_type")) or "Unknown",
                    asset_subtype=clean_string_value(row.get("asset_subtype")),
                    asset_subtype_2=clean_string_value(row.get("asset_subtype_2")),
                    asset_name=clean_string_value(row.get("asset_name")) or f"Asset {display_id}",
                    geographic_focus=clean_string_value(row.get("geographic_focus")),
                    asset_identifier=clean_string_value(row.get("asset_identifier")),
                    asset_status=clean_string_value(row.get("asset_status")) or "Active in portfolio",
                    broker_asset_manager=clean_string_value(row.get("broker_asset_manager")),
                    denomination_currency=clean_string_value(row.get("denomination_currency")) or "USD",
                    # Investment details
                    initial_investment_date=clean_date_value(row.get("initial_investment_date")),
                    number_of_shares=clean_numeric_value(row.get("number_of_shares")) or Decimal(0),
                    avg_purchase_price_base_currency=clean_numeric_value(row.get("avg_purchase_price_base_currency")) or Decimal(0),
                    total_investment_commitment_base_currency=clean_numeric_value(row.get("total_investment_commitment_base_currency")) or Decimal(0),
                    paid_in_capital_base_currency=clean_numeric_value(row.get("paid_in_capital_base_currency")) or Decimal(0),
                    asset_level_financing_base_currency=clean_numeric_value(row.get("asset_level_financing_base_currency")) or Decimal(0),
                    unfunded_commitment_base_currency=clean_numeric_value(row.get("unfunded_commitment_base_currency")) or Decimal(0),
                    current_share_price=clean_numeric_value(row.get("current_share_price")),
                    estimated_asset_value_base_currency=clean_numeric_value(row.get("estimated_asset_value_base_currency")),
                    total_asset_return_base_currency=clean_numeric_value(row.get("total_asset_return_base_currency")),
                    # FX Rates
                    usd_eur_inception=clean_numeric_value(row.get("usd_eur_inception")),
                    usd_eur_current=clean_numeric_value(row.get("usd_eur_current")),
                    usd_cad_current=clean_numeric_value(row.get("usd_cad_current")),
                    usd_chf_current=clean_numeric_value(row.get("usd_chf_current")),
                    usd_hkd_current=clean_numeric_value(row.get("usd_hkd_current")),
                    # Multi-currency values - USD
                    total_investment_commitment_usd=clean_numeric_value(row.get("total_investment_commitment_usd")),
                    paid_in_capital_usd=clean_numeric_value(row.get("paid_in_capital_usd")),
                    unfunded_commitment_usd=clean_numeric_value(row.get("unfunded_commitment_usd")),
                    estimated_asset_value_usd=clean_numeric_value(row.get("estimated_asset_value_usd")),
                    total_asset_return_usd=clean_numeric_value(row.get("total_asset_return_usd")),
                    unrealized_gain_usd=clean_numeric_value(row.get("unrealized_gain_usd")),
                    # Multi-currency values - EUR
                    total_investment_commitment_eur=clean_numeric_value(row.get("total_investment_commitment_eur")),
                    paid_in_capital_eur=clean_numeric_value(row.get("paid_in_capital_eur")),
                    unfunded_commitment_eur=clean_numeric_value(row.get("unfunded_commitment_eur")),
                    estimated_asset_value_eur=clean_numeric_value(row.get("estimated_asset_value_eur")),
                    total_asset_return_eur=clean_numeric_value(row.get("total_asset_return_eur")),
                    unrealized_gain_eur=clean_numeric_value(row.get("unrealized_gain_eur")),
                )
                db.add(asset)
                assets_created += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            continue

    db.commit()
    print(f"   Created {assets_created} assets from Various sheet")

    if errors:
        print(f"\n   Errors in Various sheet:")
        for error in errors[:5]:
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    return assets_created, errors


def import_structured_notes_multi_report(
    excel_file: str,
    db: SessionLocal,
    report_dates: list[date],
) -> tuple[int, int, list[str]]:
    """
    Import structured notes as new assets with extensions for multiple report dates.

    Returns: (assets_created, notes_created, errors)
    """
    print(f"\n[Importing StructuredNotes sheet for {len(report_dates)} report dates...]")

    df = pd.read_excel(excel_file, sheet_name="StructuredNotes", skiprows=1)

    assets_created = 0
    notes_created = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            display_id = int(row["ID"]) if pd.notna(row.get("ID")) else None
            if not display_id:
                continue

            # Create one asset + extension per report date
            for report_date in report_dates:
                asset = Asset(
                    display_id=display_id,
                    report_date=report_date,
                    holding_company=clean_string_value(row.get("holding_company")),
                    ownership_holding_entity=clean_string_value(row.get("ownership_holding_entity")) or "Unknown",
                    managing_entity=clean_string_value(row.get("managing_entity")) or "Unknown",
                    asset_group=clean_string_value(row.get("asset_group")),
                    asset_type=clean_string_value(row.get("asset_type")) or "Unknown",
                    asset_subtype=clean_string_value(row.get("asset_subtype")),
                    asset_subtype_2=clean_string_value(row.get("asset_subtype_2")),
                    asset_name=clean_string_value(row.get("asset_name")) or f"Asset {display_id}",
                    geographic_focus=clean_string_value(row.get("geographic_focus")),
                    asset_identifier=clean_string_value(row.get("asset_identifier")),
                    asset_status=clean_string_value(row.get("asset_status")) or "Active in portfolio",
                    broker_asset_manager=clean_string_value(row.get("broker_asset_manager")),
                    denomination_currency=clean_string_value(row.get("denomination_currency")) or "USD",
                    initial_investment_date=clean_date_value(row.get("initial_investment_date")),
                    number_of_shares=clean_numeric_value(row.get("number_of_shares")) or Decimal(0),
                    avg_purchase_price_base_currency=clean_numeric_value(row.get("avg_purchase_price")) or Decimal(0),
                    total_investment_commitment_base_currency=clean_numeric_value(row.get("total_investment_commitment_base_currency")) or Decimal(0),
                    paid_in_capital_base_currency=clean_numeric_value(row.get("paid_in_capital_base_currency")) or Decimal(0),
                    asset_level_financing_base_currency=clean_numeric_value(row.get("asset_level_financing")) or Decimal(0),
                    unfunded_commitment_base_currency=clean_numeric_value(row.get("pending_investment")) or Decimal(0),
                    current_share_price=clean_numeric_value(row.get("current_share_price")),
                    estimated_asset_value_base_currency=clean_numeric_value(row.get("estimated_asset_value_base_currency")),
                    total_asset_return_base_currency=clean_numeric_value(row.get("total_asset_return")),
                    # FX Rates
                    usd_eur_inception=clean_numeric_value(row.get("usd_eur_inception")),
                    usd_eur_current=clean_numeric_value(row.get("usd_eur_current")),
                    # Multi-currency - USD
                    total_investment_commitment_usd=clean_numeric_value(row.get("total_investment_commitment_usd")),
                    paid_in_capital_usd=clean_numeric_value(row.get("paid_in_capital_usd")),
                    estimated_asset_value_usd=clean_numeric_value(row.get("estimated_asset_value_usd")),
                    total_asset_return_usd=clean_numeric_value(row.get("total_asset_return_usd")),
                    unrealized_gain_usd=clean_numeric_value(row.get("unrealized_gain_usd")),
                    # Multi-currency - EUR
                    total_investment_commitment_eur=clean_numeric_value(row.get("total_investment_commitment_eur")),
                    paid_in_capital_eur=clean_numeric_value(row.get("paid_in_capital_eur")),
                    estimated_asset_value_eur=clean_numeric_value(row.get("estimated_asset_value_eur")),
                    total_asset_return_eur=clean_numeric_value(row.get("total_asset_return_eur")),
                    unrealized_gain_eur=clean_numeric_value(row.get("unrealized_gain_eur")),
                    # Realized gains (NEW - for Structured Notes)
                    realized_gain_usd=clean_numeric_value(row.get("realized_gain_usd")),
                    realized_gain_eur=clean_numeric_value(row.get("realized_gain_eur")),
                )
                db.add(asset)
                db.flush()  # Get the asset ID
                assets_created += 1

                # Create StructuredNote extension
                structured_note = StructuredNote(
                    asset_id=asset.id,
                    annual_coupon=clean_numeric_value(row.get("annual_coupon")),
                    coupon_payment_frequency=clean_string_value(row.get("coupon_payment_frequency")),
                    next_coupon_review_date=clean_string_value(row.get("next_coupon_review_date")),
                    next_principal_review_date=clean_date_value(row.get("next_principal_review_date")),
                    final_due_date=clean_date_value(row.get("final_due_date")),
                    redemption_type=clean_string_value(row.get("redemption_type")),
                    underlying_index_name=clean_string_value(row.get("underlying_index_name")),
                    underlying_index_code=clean_string_value(row.get("underlying_index_code")),
                    strike_level=clean_numeric_value(row.get("strike_level")),
                    underlying_index_level=clean_numeric_value(row.get("underlying_index_level")),
                    performance_vs_strike=clean_numeric_value(row.get("performance_vs_strike")),
                    effective_strike_percentage=clean_numeric_value(row.get("effective_strike_percentage")),
                    note_leverage=clean_string_value(row.get("note_leverage")),
                    capital_protection=clean_numeric_value(row.get("capital_protection")),
                    capital_protection_barrier=clean_numeric_value(row.get("capital_protection_barrier")),
                    coupon_protection_barrier_pct=clean_numeric_value(row.get("coupon_protection_barrier_pct")),
                    coupon_protection_barrier_value=clean_numeric_value(row.get("coupon_protection_barrier_value")),
                )
                db.add(structured_note)
                notes_created += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            continue

    db.commit()
    print(f"   Created {assets_created} assets from StructuredNotes sheet")
    print(f"   Created {notes_created} structured note extensions")

    if errors:
        print(f"\n   Errors in StructuredNotes sheet:")
        for error in errors[:5]:
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    return assets_created, notes_created, errors


def import_real_estate_multi_report(
    excel_file: str,
    db: SessionLocal,
    report_dates: list[date],
) -> tuple[int, int, list[str]]:
    """
    Import real estate as new assets with extensions for multiple report dates.

    Returns: (assets_created, real_estate_created, errors)
    """
    print(f"\n[Importing RealEstate sheet for {len(report_dates)} report dates...]")

    df = pd.read_excel(excel_file, sheet_name="RealEstate", skiprows=1)

    assets_created = 0
    real_estate_created = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            display_id = int(row["ID"]) if pd.notna(row.get("ID")) else None
            if not display_id:
                continue

            # Create one asset + extension per report date
            for report_date in report_dates:
                asset = Asset(
                    display_id=display_id,
                    report_date=report_date,
                    holding_company=clean_string_value(row.get("holding_company")),
                    ownership_holding_entity=clean_string_value(row.get("ownership_holding_entity")) or "Unknown",
                    managing_entity=clean_string_value(row.get("managing_entity")) or "Unknown",
                    asset_group=clean_string_value(row.get("asset_group")),
                    asset_type=clean_string_value(row.get("asset_type")) or "Unknown",
                    asset_subtype=clean_string_value(row.get("asset_subtype")),
                    asset_subtype_2=clean_string_value(row.get("asset_subtype_2")),
                    asset_name=clean_string_value(row.get("asset_name")) or f"Asset {display_id}",
                    geographic_focus=clean_string_value(row.get("geographic_focus")),
                    asset_identifier=clean_string_value(row.get("asset_identifier")),
                    asset_status=clean_string_value(row.get("asset_status")) or "Active in portfolio",
                    broker_asset_manager=clean_string_value(row.get("broker_asset_manager")),
                    denomination_currency=clean_string_value(row.get("denomination_currency")) or "USD",
                    initial_investment_date=clean_date_value(row.get("initial_investment_date")),
                    asset_level_financing_base_currency=clean_numeric_value(row.get("asset_level_financing_eur")) or Decimal(0),
                    estimated_asset_value_base_currency=clean_numeric_value(row.get("estimated_asset_value_eur")),
                    # FX Rates
                    usd_eur_inception=clean_numeric_value(row.get("usd_eur_inception")),
                    usd_eur_current=clean_numeric_value(row.get("usd_eur_current")),
                    # Multi-currency
                    estimated_asset_value_usd=clean_numeric_value(row.get("estimated_asset_value_usd")),
                    estimated_asset_value_eur=clean_numeric_value(row.get("estimated_asset_value_eur")),
                    # Return columns (at Asset level like all other assets)
                    total_asset_return_usd=clean_numeric_value(row.get("total_asset_return_USD")),
                    total_asset_return_eur=clean_numeric_value(row.get("total_asset_return_EUR")),
                    # Unrealized gains (from Excel)
                    unrealized_gain_usd=clean_numeric_value(row.get("unrealized_gain_usd")),
                    unrealized_gain_eur=clean_numeric_value(row.get("unrealized_gain_eur")),
                    # Normalized fields (Real Estate uses different column names)
                    paid_in_capital_usd=clean_numeric_value(row.get("equity_investment_to_date_usd")),
                    paid_in_capital_eur=clean_numeric_value(row.get("equity_investment_to_date_eur")),
                    realized_gain_usd=clean_numeric_value(row.get("estimated_capital_gain_usd")),
                    realized_gain_eur=clean_numeric_value(row.get("estimated_capital_gain_eur")),
                )
                db.add(asset)
                db.flush()
                assets_created += 1

                # Create RealEstateAsset extension
                real_estate = RealEstateAsset(
                    asset_id=asset.id,
                    real_estate_status=clean_string_value(row.get("real_estate_status")),
                    cost_original_asset_eur=clean_numeric_value(row.get("cost_original_asset_eur")) or Decimal(0),
                    estimated_capex_budget_eur=clean_numeric_value(row.get("estimated_capex_budget_eur")) or Decimal(0),
                    pivert_development_fees_eur=clean_numeric_value(row.get("pivert_development_fees_eur")) or Decimal(0),
                    estimated_total_cost_eur=clean_numeric_value(row.get("estimated_total_cost_eur")) or Decimal(0),
                    capex_invested_eur=clean_numeric_value(row.get("capex_invested_eur")) or Decimal(0),
                    total_investment_to_date_eur=clean_numeric_value(row.get("total_investment_to_date_eur")) or Decimal(0),
                    equity_investment_to_date_eur=clean_numeric_value(row.get("equity_investment_to_date_eur")) or Decimal(0),
                    pending_equity_investment_eur=clean_numeric_value(row.get("pending_equity_investment_eur")) or Decimal(0),
                    estimated_capital_gain_eur=clean_numeric_value(row.get("estimated_capital_gain_eur")),
                    # USD columns
                    estimated_total_cost_usd=clean_numeric_value(row.get("estimated_total_cost_usd")),
                    total_investment_to_date_usd=clean_numeric_value(row.get("total_investment_to_date_usd")),
                    equity_investment_to_date_usd=clean_numeric_value(row.get("equity_investment_to_date_usd")),
                    pending_equity_investment_usd=clean_numeric_value(row.get("pending_equity_investment_usd")),
                    estimated_capital_gain_usd=clean_numeric_value(row.get("estimated_capital_gain_usd")),
                )
                db.add(real_estate)
                real_estate_created += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            continue

    db.commit()
    print(f"   Created {assets_created} assets from RealEstate sheet")
    print(f"   Created {real_estate_created} real estate extensions")

    if errors:
        print(f"\n   Errors in RealEstate sheet:")
        for error in errors[:5]:
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    return assets_created, real_estate_created, errors


# =============================================================================
# Main Function
# =============================================================================


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Development ETL: Import portfolio data with multiple report dates"
    )
    parser.add_argument(
        "--file",
        default="/Users/miguelsantana/Downloads/Portafolio Grupo Malatesta-Fixed-23-12-25.xlsx",
        help="Path to Excel file",
    )
    parser.add_argument(
        "--base-date",
        type=str,
        default="2025-05-30",
        help="Base report date in YYYY-MM-DD format (default: 2025-05-30)",
    )
    parser.add_argument(
        "--additional-months",
        type=int,
        default=3,
        help="Number of additional months to generate (default: 3 for Jun/Jul/Aug)",
    )
    return parser.parse_args()


def main() -> None:
    """Main migration function."""
    args = parse_arguments()
    excel_file = args.file

    # Parse base date
    base_date = datetime.strptime(args.base_date, "%Y-%m-%d").date()

    # Generate report dates
    report_dates = generate_report_dates(base_date, args.additional_months)

    print("=" * 80)
    print("DEVELOPMENT PORTFOLIO DATA MIGRATION")
    print("=" * 80)
    print(f"Excel file: {excel_file}")
    print(f"Base date: {base_date}")
    print(f"Report dates: {[d.strftime('%Y-%m-%d') for d in report_dates]}")
    print(f"Total reports: {len(report_dates)}")

    # Check if Excel file exists
    if not Path(excel_file).exists():
        print(f"\nError: Excel file not found at {excel_file}")
        sys.exit(1)

    db = SessionLocal()

    try:
        # Step 1: Clear existing data
        clear_existing_data(db)

        # Step 2: Import Various sheet
        various_assets, various_errors = import_various_sheet_multi_report(
            excel_file, db, report_dates
        )

        # Step 3: Import StructuredNotes sheet
        structured_assets, structured_notes, structured_errors = import_structured_notes_multi_report(
            excel_file, db, report_dates
        )

        # Step 4: Import RealEstate sheet
        real_estate_assets, real_estate_extensions, real_estate_errors = import_real_estate_multi_report(
            excel_file, db, report_dates
        )

        total_assets = various_assets + structured_assets + real_estate_assets
        total_errors = len(various_errors) + len(structured_errors) + len(real_estate_errors)

        print("\n" + "=" * 80)
        if total_errors > 0:
            print(f"MIGRATION COMPLETED WITH {total_errors} ERRORS")
        else:
            print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"\nTotal imported:")
        print(f"  - {total_assets} total assets")
        print(f"    - {various_assets} from Various sheet")
        print(f"    - {structured_assets} from StructuredNotes sheet")
        print(f"    - {real_estate_assets} from RealEstate sheet")
        print(f"  - {structured_notes} structured note extensions")
        print(f"  - {real_estate_extensions} real estate extensions")
        print(f"\nReport dates created: {[d.strftime('%Y-%m-%d') for d in report_dates]}")
        if total_errors > 0:
            print(f"\nTotal errors: {total_errors} rows failed to import")
        print("=" * 80)

        if total_errors > 0:
            sys.exit(1)

    except SQLAlchemyError as e:
        print(f"\nDatabase error: {str(e)}")
        db.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
