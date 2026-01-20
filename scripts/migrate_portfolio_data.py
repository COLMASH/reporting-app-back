"""
Portfolio Data Migration Script

This script:
1. Clears all existing portfolio data (assets, structured_notes, real_estate_assets)
2. Imports data from Excel file (3 sheets: Various, StructuredNotes, RealEstate)
3. Handles data type conversions and validations
4. Creates assets with specialized extensions (structured notes, real estate)

Usage:
    uv run python scripts/migrate_portfolio_data.py [--file PATH_TO_EXCEL]
"""

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database.core import SessionLocal
from src.modules.portfolio.models import Asset, RealEstateAsset, StructuredNote


def clean_numeric_value(value) -> Decimal | None:
    """Convert value to Decimal, handling NaN, empty values, and formatting."""
    if pd.isna(value) or value == "" or value == "-":
        return None
    try:
        if isinstance(value, str):
            # Remove commas and convert
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


def clear_existing_data(db: SessionLocal) -> None:
    """Clear all existing portfolio data."""
    print("\n🗑️  Clearing existing portfolio data...")

    structured_count = db.query(StructuredNote).count()
    real_estate_count = db.query(RealEstateAsset).count()
    asset_count = db.query(Asset).count()

    # Delete assets (will cascade to structured_notes and real_estate_assets)
    db.query(Asset).delete()
    db.commit()

    print(f"   ✓ Deleted {asset_count} assets")
    print(f"   ✓ Deleted {structured_count} structured notes (cascade)")
    print(f"   ✓ Deleted {real_estate_count} real estate assets (cascade)")


def import_various_sheet(excel_file: str, db: SessionLocal) -> tuple[dict[int, Asset], list[str]]:
    """Import main asset data from Various sheet. Returns (assets_by_id, errors)."""
    print(f"\n📥 Importing Various sheet (main assets)...")

    # Read Various sheet (skip metadata row 1)
    df = pd.read_excel(excel_file, sheet_name="Various", skiprows=1)

    assets_by_id = {}
    errors = []

    for idx, row in df.iterrows():
        try:
            display_id = int(row["ID"]) if pd.notna(row.get("ID")) else None
            if not display_id:
                continue

            # Check for duplicate IDs
            if display_id in assets_by_id:
                errors.append(f"Row {idx + 2}: Duplicate ID {display_id}")
                continue

            # Create Asset instance
            asset = Asset(
                display_id=display_id,
                # Excel columns - NEW column names
                report_date=clean_date_value(row.get("report_date")),
                holding_company=clean_string_value(row.get("holding_company")),  # NEW
                ownership_holding_entity=clean_string_value(row.get("ownership_holding_entity")) or "Unknown",
                managing_entity=clean_string_value(row.get("managing_entity")) or "Unknown",  # Renamed from asset_group
                asset_group=clean_string_value(row.get("asset_group")),  # Renamed from asset_group_strategy
                asset_type=clean_string_value(row.get("asset_type")) or "Unknown",
                asset_subtype=clean_string_value(row.get("asset_subtype")),
                asset_subtype_2=clean_string_value(row.get("asset_subtype_2")),
                asset_name=clean_string_value(row.get("asset_name")) or f"Asset {display_id}",
                geographic_focus=clean_string_value(row.get("geographic_focus")),
                asset_identifier=clean_string_value(row.get("asset_identifier")),
                asset_status=clean_string_value(row.get("asset_status")) or "Active in portfolio",
                broker_asset_manager=clean_string_value(row.get("broker_asset_manager")),
                denomination_currency=clean_string_value(row.get("denomination_currency")) or "USD",
                # Investment details - Base Currency
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
                unrealized_gain_usd=clean_numeric_value(row.get("unrealized_gain_usd")),  # NEW
                # Multi-currency values - EUR
                total_investment_commitment_eur=clean_numeric_value(row.get("total_investment_commitment_eur")),
                paid_in_capital_eur=clean_numeric_value(row.get("paid_in_capital_eur")),
                unfunded_commitment_eur=clean_numeric_value(row.get("unfunded_commitment_eur")),
                estimated_asset_value_eur=clean_numeric_value(row.get("estimated_asset_value_eur")),
                total_asset_return_eur=clean_numeric_value(row.get("total_asset_return_eur")),
                unrealized_gain_eur=clean_numeric_value(row.get("unrealized_gain_eur")),  # NEW
            )

            db.add(asset)
            db.flush()  # Get the asset ID
            assets_by_id[display_id] = asset

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            continue

    db.commit()

    print(f"   ✓ Created {len(assets_by_id)} assets")

    if errors:
        print(f"\n⚠️  Errors in Various sheet:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"   • {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    return assets_by_id, errors


def import_structured_notes_sheet(excel_file: str, db: SessionLocal, assets_by_id: dict[int, Asset]) -> tuple[int, int, list[str]]:
    """Import structured notes as new assets with extensions. Returns (assets_created, notes_created, errors)."""
    print(f"\n📥 Importing StructuredNotes sheet (additional assets)...")

    # Read StructuredNotes sheet (skip metadata row 1)
    df = pd.read_excel(excel_file, sheet_name="StructuredNotes", skiprows=1)

    assets_created = 0
    notes_created = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            display_id = int(row["ID"]) if pd.notna(row.get("ID")) else None
            if not display_id:
                continue

            # Check for duplicate IDs
            if display_id in assets_by_id:
                errors.append(f"Row {idx + 2}: Duplicate ID {display_id}")
                continue

            # Create new Asset from StructuredNotes sheet (using NEW column names)
            asset = Asset(
                display_id=display_id,
                report_date=clean_date_value(row.get("report_date")),
                holding_company=clean_string_value(row.get("holding_company")),  # NEW
                ownership_holding_entity=clean_string_value(row.get("ownership_holding_entity")) or "Unknown",
                managing_entity=clean_string_value(row.get("managing_entity")) or "Unknown",  # Renamed from asset_group
                asset_group=clean_string_value(row.get("asset_group")),  # Renamed from asset_group_strategy
                asset_type=clean_string_value(row.get("asset_type")) or "Unknown",
                asset_subtype=clean_string_value(row.get("asset_subtype")),
                asset_subtype_2=clean_string_value(row.get("asset_subtype_2")),
                asset_name=clean_string_value(row.get("asset_name")) or f"Asset {display_id}",
                geographic_focus=clean_string_value(row.get("geographic_focus")),  # Renamed from location
                asset_identifier=clean_string_value(row.get("asset_identifier")),
                asset_status=clean_string_value(row.get("asset_status")) or "Active in portfolio",
                broker_asset_manager=clean_string_value(row.get("broker_asset_manager")),
                denomination_currency=clean_string_value(row.get("denomination_currency")) or "USD",
                initial_investment_date=clean_date_value(row.get("initial_investment_date")),
                number_of_shares=clean_numeric_value(row.get("number_of_shares")) or Decimal(0),
                # Note: Excel has old-style names for some columns
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
                # Multi-currency values - USD
                total_investment_commitment_usd=clean_numeric_value(row.get("total_investment_commitment_usd")),
                paid_in_capital_usd=clean_numeric_value(row.get("paid_in_capital_usd")),
                estimated_asset_value_usd=clean_numeric_value(row.get("estimated_asset_value_usd")),
                total_asset_return_usd=clean_numeric_value(row.get("total_asset_return_usd")),
                unrealized_gain_usd=clean_numeric_value(row.get("unrealized_gain_usd")),
                # Multi-currency values - EUR
                total_investment_commitment_eur=clean_numeric_value(row.get("total_investment_commitment_eur")),
                paid_in_capital_eur=clean_numeric_value(row.get("paid_in_capital_eur")),
                estimated_asset_value_eur=clean_numeric_value(row.get("estimated_asset_value_eur")),
                total_asset_return_eur=clean_numeric_value(row.get("total_asset_return_eur")),
                unrealized_gain_eur=clean_numeric_value(row.get("unrealized_gain_eur")),
            )

            db.add(asset)
            db.flush()
            assets_by_id[display_id] = asset
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
            # Don't rollback - just skip this row and continue with others
            continue

    db.commit()

    print(f"   ✓ Created {assets_created} assets")
    print(f"   ✓ Created {notes_created} structured notes")

    if errors:
        print(f"\n⚠️  Errors in StructuredNotes sheet:")
        for error in errors[:5]:
            print(f"   • {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    return assets_created, notes_created, errors


def import_real_estate_sheet(excel_file: str, db: SessionLocal, assets_by_id: dict[int, Asset]) -> tuple[int, int, list[str]]:
    """Import real estate as new assets with extensions. Returns (assets_created, real_estate_created, errors)."""
    print(f"\n📥 Importing RealEstate sheet (additional assets)...")

    # Read RealEstate sheet (skip metadata row 1)
    df = pd.read_excel(excel_file, sheet_name="RealEstate", skiprows=1)

    assets_created = 0
    real_estate_created = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            display_id = int(row["ID"]) if pd.notna(row.get("ID")) else None
            if not display_id:
                continue

            # Check for duplicate IDs
            if display_id in assets_by_id:
                errors.append(f"Row {idx + 2}: Duplicate ID {display_id}")
                continue

            # Create new Asset from RealEstate sheet (using NEW column names)
            asset = Asset(
                display_id=display_id,
                report_date=clean_date_value(row.get("report_date")),
                holding_company=clean_string_value(row.get("holding_company")),  # NEW
                ownership_holding_entity=clean_string_value(row.get("ownership_holding_entity")) or "Unknown",
                managing_entity=clean_string_value(row.get("managing_entity")) or "Unknown",  # Renamed from asset_group
                asset_group=clean_string_value(row.get("asset_group")),  # Renamed from asset_group_strategy
                asset_type=clean_string_value(row.get("asset_type")) or "Unknown",
                asset_subtype=clean_string_value(row.get("asset_subtype")),
                asset_subtype_2=clean_string_value(row.get("asset_subtype_2")),
                asset_name=clean_string_value(row.get("asset_name")) or f"Asset {display_id}",
                geographic_focus=clean_string_value(row.get("geographic_focus")),  # Renamed from location
                asset_identifier=clean_string_value(row.get("asset_identifier")),
                asset_status=clean_string_value(row.get("asset_status")) or "Active in portfolio",
                broker_asset_manager=clean_string_value(row.get("broker_asset_manager")),
                denomination_currency=clean_string_value(row.get("denomination_currency")) or "USD",
                initial_investment_date=clean_date_value(row.get("initial_investment_date")),
                asset_level_financing_base_currency=clean_numeric_value(row.get("asset_level_financing_eur")) or Decimal(0),  # Renamed
                estimated_asset_value_base_currency=clean_numeric_value(row.get("estimated_asset_value_eur")),
                # FX Rates (NEW for RealEstate)
                usd_eur_inception=clean_numeric_value(row.get("usd_eur_inception")),
                usd_eur_current=clean_numeric_value(row.get("usd_eur_current")),
                # Multi-currency values
                estimated_asset_value_usd=clean_numeric_value(row.get("estimated_asset_value_usd")),
                estimated_asset_value_eur=clean_numeric_value(row.get("estimated_asset_value_eur")),
            )

            db.add(asset)
            db.flush()
            assets_by_id[display_id] = asset
            assets_created += 1

            # Create RealEstateAsset extension (using NEW column names)
            real_estate = RealEstateAsset(
                asset_id=asset.id,
                real_estate_status=clean_string_value(row.get("real_estate_status")),  # NEW
                # EUR columns (renamed with _eur suffix)
                cost_original_asset_eur=clean_numeric_value(row.get("cost_original_asset_eur")) or Decimal(0),
                estimated_capex_budget_eur=clean_numeric_value(row.get("estimated_capex_budget_eur")) or Decimal(0),
                pivert_development_fees_eur=clean_numeric_value(row.get("pivert_development_fees_eur")) or Decimal(0),
                estimated_total_cost_eur=clean_numeric_value(row.get("estimated_total_cost_eur")) or Decimal(0),
                capex_invested_eur=clean_numeric_value(row.get("capex_invested_eur")) or Decimal(0),
                total_investment_to_date_eur=clean_numeric_value(row.get("total_investment_to_date_eur")) or Decimal(0),
                equity_investment_to_date_eur=clean_numeric_value(row.get("equity_investment_to_date_eur")) or Decimal(0),
                pending_equity_investment_eur=clean_numeric_value(row.get("pending_equity_investment_eur")) or Decimal(0),
                estimated_capital_gain_eur=clean_numeric_value(row.get("estimated_capital_gain_eur")),
                # NEW USD columns
                estimated_total_cost_usd=clean_numeric_value(row.get("estimated_total_cost_usd")),
                total_investment_to_date_usd=clean_numeric_value(row.get("total_investment_to_date_usd")),
                equity_investment_to_date_usd=clean_numeric_value(row.get("equity_investment_to_date_usd")),
                pending_equity_investment_usd=clean_numeric_value(row.get("pending_equity_investment_usd")),
                estimated_capital_gain_usd=clean_numeric_value(row.get("estimated_capital_gain_usd")),
                # Return columns
                total_asset_return_usd=clean_numeric_value(row.get("total_asset_return_USD")),
                total_asset_return_eur=clean_numeric_value(row.get("total_asset_return_EUR")),
            )

            db.add(real_estate)
            real_estate_created += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            # Don't rollback - just skip this row and continue with others
            continue

    db.commit()

    print(f"   ✓ Created {assets_created} assets")
    print(f"   ✓ Created {real_estate_created} real estate assets")

    if errors:
        print(f"\n⚠️  Errors in RealEstate sheet:")
        for error in errors[:5]:
            print(f"   • {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    return assets_created, real_estate_created, errors


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate portfolio data from Excel file')
    parser.add_argument(
        '--file',
        default="/Users/miguelsantana/Downloads/Portafolio Grupo Malatesta desagregado 25.11.10.xlsx",
        help='Path to Excel file (default: Downloads/Portafolio Grupo Malatesta desagregado 25.11.10.xlsx)'
    )
    args = parser.parse_args()
    excel_file = args.file

    print("=" * 80)
    print("PORTFOLIO DATA MIGRATION")
    print("=" * 80)
    print(f"Excel file: {excel_file}")

    # Check if Excel file exists
    if not Path(excel_file).exists():
        print(f"\n❌ Error: Excel file not found at {excel_file}")
        sys.exit(1)

    db = SessionLocal()

    try:
        # Step 1: Clear existing data
        clear_existing_data(db)

        # Step 2: Import Various sheet (main assets)
        assets_by_id, various_errors = import_various_sheet(excel_file, db)
        various_asset_count = len(assets_by_id)

        # Step 3: Import StructuredNotes sheet (additional assets + extensions)
        structured_assets, structured_notes, structured_errors = import_structured_notes_sheet(excel_file, db, assets_by_id)

        # Step 4: Import RealEstate sheet (additional assets + extensions)
        real_estate_assets, real_estate_extensions, real_estate_errors = import_real_estate_sheet(excel_file, db, assets_by_id)

        total_assets = various_asset_count + structured_assets + real_estate_assets
        total_errors = len(various_errors) + len(structured_errors) + len(real_estate_errors)

        print("\n" + "=" * 80)
        if total_errors > 0:
            print(f"⚠️  MIGRATION COMPLETED WITH {total_errors} ERRORS")
        else:
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"\nTotal imported:")
        print(f"  • {total_assets} total assets")
        print(f"    - {various_asset_count} from Various sheet")
        print(f"    - {structured_assets} from StructuredNotes sheet")
        print(f"    - {real_estate_assets} from RealEstate sheet")
        print(f"  • {structured_notes} structured note extensions")
        print(f"  • {real_estate_extensions} real estate extensions")
        if total_errors > 0:
            print(f"\n⚠️  Total errors: {total_errors} rows failed to import")
        print("=" * 80)

        # Exit with error code if there were any import errors
        if total_errors > 0:
            sys.exit(1)

    except SQLAlchemyError as e:
        print(f"\n❌ Database error: {str(e)}")
        db.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
