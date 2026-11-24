"""
Enterprise Sales CSV Data Quality Validator
-------------------------------------------
Standard-library-only validation for data/generated/<scale>/.

Checks:
- Required files and columns
- Row counts against manifest
- Primary-key uniqueness
- Foreign-key integrity across generated CSVs
- Required fields and basic domain rules
- Sales order / line numeric rules
- Commission calculation consistency

Run from project root:
    python scripts/validate_data.py --scale small
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# These headers must match the generator. Before ingestion, compare them
# with the actual PostgreSQL DDL.
TABLES = {
    "regions": {
        "pk": "region_id",
        "required": ["region_name", "country"],
    },
    "territories": {
        "pk": "territory_id",
        "required": ["region_id", "territory_name", "territory_code"],
    },
    "employees": {
        "pk": "employee_id",
        "required": ["first_name", "last_name", "email", "job_title", "hire_date", "employment_status"],
    },
    "employee_territories": {
        "pk": "assignment_id",
        "required": ["employee_id", "territory_id", "start_date"],
    },
    "customers": {
        "pk": "customer_id",
        "required": ["customer_name", "industry", "country", "customer_segment"],
    },
    "products": {
        "pk": "product_id",
        "required": ["product_name", "category", "list_price", "is_active"],
    },
    "sales_orders": {
        "pk": "order_id",
        "required": ["order_reference", "customer_id", "employee_id", "territory_id", "order_date", "order_status", "currency_code"],
    },
    "sales_order_lines": {
        "pk": "order_line_id",
        "required": ["order_id", "product_id", "line_number", "quantity", "unit_price", "discount_amount"],
    },
    "sales_targets": {
        "pk": "target_id",
        "required": ["employee_id", "period_start", "period_end", "target_amount", "currency_code"],
    },
    "incentive_plans": {
        "pk": "plan_id",
        "required": ["plan_name", "plan_type", "effective_from", "is_active"],
    },
    "commission_tiers": {
        "pk": "tier_id",
        "required": ["plan_id", "min_attainment", "commission_rate"],
    },
    "employee_incentive_plans": {
        "pk": "assignment_id",
        "required": ["employee_id", "plan_id", "effective_from"],
    },
    "commission_results": {
        "pk": "result_id",
        "required": ["assignment_id", "period_start", "period_end", "eligible_revenue", "target_amount", "attainment_percentage", "commission_rate", "commission_amount", "calculation_status"],
    },
}

FOREIGN_KEYS = [
    ("territories", "region_id", "regions", "region_id"),
    ("employees", "manager_id", "employees", "employee_id"),
    ("employee_territories", "employee_id", "employees", "employee_id"),
    ("employee_territories", "territory_id", "territories", "territory_id"),
    ("sales_orders", "customer_id", "customers", "customer_id"),
    ("sales_orders", "employee_id", "employees", "employee_id"),
    ("sales_orders", "territory_id", "territories", "territory_id"),
    ("sales_order_lines", "order_id", "sales_orders", "order_id"),
    ("sales_order_lines", "product_id", "products", "product_id"),
    ("sales_targets", "employee_id", "employees", "employee_id"),
    ("commission_tiers", "plan_id", "incentive_plans", "plan_id"),
    ("employee_incentive_plans", "employee_id", "employees", "employee_id"),
    ("employee_incentive_plans", "plan_id", "incentive_plans", "plan_id"),
    ("commission_results", "assignment_id", "employee_incentive_plans", "assignment_id"),
]

EXPECTED_ENUMS = {
    ("employees", "employment_status"): {"ACTIVE", "INACTIVE", "TERMINATED"},
    ("sales_orders", "order_status"): {"PENDING", "CONFIRMED", "COMPLETED", "CANCELLED"},
    ("commission_results", "calculation_status"): {"DRAFT", "APPROVED", "PAID", "REJECTED"},
}


class ValidationReport:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks = 0

    def ok(self, message: str) -> None:
        self.checks += 1
        logging.info("PASS | %s", message)

    def fail(self, message: str) -> None:
        self.checks += 1
        self.errors.append(message)
        logging.error("FAIL | %s", message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        logging.warning("WARN | %s", message)


def load_table(folder: Path, table: str) -> tuple[list[dict[str, str]], list[str]]:
    path = folder / f"{table}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name} has no header row")
        rows = list(reader)
        return rows, list(reader.fieldnames)


def as_decimal(value: str, label: str, report: ValidationReport) -> Decimal | None:
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        report.fail(f"{label}: invalid decimal value {value!r}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated enterprise sales CSV data.")
    parser.add_argument("--scale", choices=["small", "full"], default="small")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    folder = PROJECT_ROOT / "data" / "generated" / args.scale
    manifest_path = folder / "manifest.json"

    if not manifest_path.exists():
        logging.error("Manifest not found: %s", manifest_path)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = ValidationReport()
    data: dict[str, list[dict[str, str]]] = {}
    id_sets: dict[str, set[str]] = {}

    logging.info("Starting %s-scale data validation.", args.scale)
    logging.info("Dataset directory: %s", folder)

    # Load tables, validate columns, required fields, row counts and PKs.
    for table, spec in TABLES.items():
        try:
            rows, columns = load_table(folder, table)
        except (OSError, ValueError) as exc:
            report.fail(str(exc))
            continue

        data[table] = rows
        expected_columns = {spec["pk"], *spec["required"]}
        missing_columns = expected_columns - set(columns)
        if missing_columns:
            report.fail(f"{table}: missing columns {sorted(missing_columns)}")
            continue
        report.ok(f"{table}: required columns present")

        expected_rows = manifest.get("counts", {}).get(table)
        if expected_rows is not None and len(rows) == expected_rows:
            report.ok(f"{table}: row count matches manifest ({len(rows):,})")
        else:
            report.fail(
                f"{table}: row count {len(rows):,} does not match manifest "
                f"({expected_rows!r})"
            )

        pk = spec["pk"]
        values = [row.get(pk, "") for row in rows]
        blank_count = sum(not value.strip() for value in values)
        duplicates = [value for value, count in Counter(values).items() if count > 1]
        if blank_count:
            report.fail(f"{table}: {blank_count} blank primary keys")
        elif duplicates:
            report.fail(f"{table}: duplicate primary keys, examples={duplicates[:5]}")
        else:
            report.ok(f"{table}: primary keys are nonblank and unique")
        id_sets[table] = set(values)

        missing_required = 0
        for row_number, row in enumerate(rows, start=2):
            for column in spec["required"]:
                if row.get(column) is None or not row[column].strip():
                    missing_required += 1
                    if missing_required <= 5:
                        report.errors.append(
                            f"{table} row {row_number}: required field {column} is blank"
                        )
        if missing_required:
            report.checks += 1
            logging.error("FAIL | %s: %s blank required-field values", table, missing_required)
        else:
            report.ok(f"{table}: required fields populated")

    # Foreign-key integrity.
    for child_table, child_col, parent_table, parent_col in FOREIGN_KEYS:
        if child_table not in data or parent_table not in data:
            continue
        parent_ids = {row[parent_col] for row in data[parent_table] if row.get(parent_col)}
        missing = []
        for row_number, row in enumerate(data[child_table], start=2):
            value = row.get(child_col, "")
            # manager_id is nullable for the top-level executive.
            if not value and child_table == "employees" and child_col == "manager_id":
                continue
            if value not in parent_ids:
                if len(missing) < 5:
                    missing.append((row_number, value))
        if missing:
            report.fail(
                f"FK {child_table}.{child_col} -> {parent_table}.{parent_col}: "
                f"orphan values, examples={missing}"
            )
        else:
            report.ok(f"FK {child_table}.{child_col} references valid {parent_table} IDs")

    # Enum/domain checks.
    for (table, column), allowed in EXPECTED_ENUMS.items():
        if table not in data:
            continue
        invalid = sorted({row[column] for row in data[table] if row.get(column) not in allowed})
        if invalid:
            report.fail(f"{table}.{column}: invalid values {invalid}")
        else:
            report.ok(f"{table}.{column}: values belong to allowed domain")

    # Numeric and date/business-rule checks.
    if "products" in data:
        invalid = [
            row["product_id"] for row in data["products"]
            if as_decimal(row["list_price"], "products.list_price", report) is not None
            and Decimal(row["list_price"]) <= 0
        ]
        if invalid:
            report.fail(f"products: non-positive list prices, IDs={invalid[:5]}")
        else:
            report.ok("products: all list prices are positive")

    if "sales_order_lines" in data:
        bad_qty, bad_price, bad_discount = [], [], []
        for row in data["sales_order_lines"]:
            try:
                qty = int(row["quantity"])
                price = Decimal(row["unit_price"])
                discount = Decimal(row["discount_amount"])
                gross = price * qty
                if qty <= 0:
                    bad_qty.append(row["order_line_id"])
                if price <= 0:
                    bad_price.append(row["order_line_id"])
                if discount < 0 or discount > gross:
                    bad_discount.append(row["order_line_id"])
            except (ValueError, InvalidOperation):
                bad_qty.append(row["order_line_id"])
        if bad_qty:
            report.fail(f"sales_order_lines: invalid quantities/numbers, IDs={bad_qty[:5]}")
        else:
            report.ok("sales_order_lines: quantities and numeric values valid")
        if bad_price:
            report.fail(f"sales_order_lines: non-positive unit prices, IDs={bad_price[:5]}")
        else:
            report.ok("sales_order_lines: unit prices are positive")
        if bad_discount:
            report.fail(f"sales_order_lines: invalid discounts, IDs={bad_discount[:5]}")
        else:
            report.ok("sales_order_lines: discounts are within gross line amounts")

    if "sales_targets" in data:
        bad_targets = []
        for row in data["sales_targets"]:
            value = as_decimal(row["target_amount"], "sales_targets.target_amount", report)
            if value is not None and value <= 0:
                bad_targets.append(row["target_id"])
        if bad_targets:
            report.fail(f"sales_targets: non-positive targets, IDs={bad_targets[:5]}")
        else:
            report.ok("sales_targets: all target amounts are positive")

    if "commission_results" in data:
        bad_attainment, bad_commission = [], []
        for row in data["commission_results"]:
            revenue = as_decimal(row["eligible_revenue"], "commission_results.eligible_revenue", report)
            target = as_decimal(row["target_amount"], "commission_results.target_amount", report)
            attainment = as_decimal(row["attainment_percentage"], "commission_results.attainment_percentage", report)
            rate = as_decimal(row["commission_rate"], "commission_results.commission_rate", report)
            commission = as_decimal(row["commission_amount"], "commission_results.commission_amount", report)
            if None in (revenue, target, attainment, rate, commission):
                continue
            if target <= 0 or revenue < 0 or rate < 0:
                bad_attainment.append(row["result_id"])
                continue
            expected_attainment = (revenue / target * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            expected_commission = (revenue * rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if abs(expected_attainment - attainment) > Decimal("0.02"):
                bad_attainment.append(row["result_id"])
            if expected_commission != commission:
                bad_commission.append(row["result_id"])

        if bad_attainment:
            report.fail(
                "commission_results: attainment does not match revenue / target; "
                f"IDs={bad_attainment[:5]}"
            )
        else:
            report.ok("commission_results: attainment matches revenue / target")
        if bad_commission:
            report.fail(
                "commission_results: commission amount does not match revenue * rate; "
                f"IDs={bad_commission[:5]}"
            )
        else:
            report.ok("commission_results: commission amounts match revenue * rate")

    logging.info("Validation checks executed: %s", report.checks)
    logging.info("Errors: %s | Warnings: %s", len(report.errors), len(report.warnings))

    if report.errors:
        logging.error("DATA QUALITY VALIDATION FAILED.")
        for error in report.errors[:30]:
            logging.error("DETAIL | %s", error)
        return 1

    logging.info("DATA QUALITY VALIDATION PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
