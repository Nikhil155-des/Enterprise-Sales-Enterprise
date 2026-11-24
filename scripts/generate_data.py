"""
Enterprise Sales Synthetic Data Generator
-----------------------------------------
Standard-library-only generator: no NumPy, Pandas, or Faker required.

Generates CSV files for the 13 project tables:
regions, territories, employees, employee_territories, customers, products,
sales_orders, sales_order_lines, sales_targets, incentive_plans,
commission_tiers, employee_incentive_plans, commission_results.

IMPORTANT:
The CSV column names follow the column assumptions used in the earlier
project generator. Review them against your actual PostgreSQL DDL before
loading data. This script generates CSVs only; it does not modify PostgreSQL.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import logging
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = 20261124
TARGET_YEAR = 2025

SMALL_SCALE = {
    "employees": 120,
    "customers": 1_000,
    "products": 100,
    "orders": 5_000,
}
FULL_SCALE = {
    "employees": 5_000,
    "customers": 50_000,
    "products": 1_000,
    "orders": 500_000,
}

REGIONS = [
    ("North India", "India"),
    ("South India", "India"),
    ("East India", "India"),
    ("West India", "India"),
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Reyansh", "Ishaan", "Kabir",
    "Rohan", "Vihaan", "Ananya", "Aadhya", "Diya", "Ira", "Meera",
    "Anika", "Saanvi", "Priya", "Neha", "Kavya", "Aanya",
]
LAST_NAMES = [
    "Sharma", "Desai", "Patel", "Rao", "Iyer", "Nair", "Reddy",
    "Mehta", "Kulkarni", "Joshi", "Kapoor", "Malhotra", "Das",
    "Mukherjee", "Menon", "Verma", "Gupta", "Khan", "Pillai", "Shetty",
]
CITIES = [
    "Bengaluru", "Mumbai", "Pune", "Hyderabad", "Chennai", "Delhi",
    "Kolkata", "Ahmedabad", "Jaipur", "Kochi", "Mysuru", "Hubballi",
    "Noida", "Gurugram", "Coimbatore", "Indore", "Lucknow", "Surat",
]
COMPANY_PREFIXES = [
    "Apex", "Vertex", "BluePeak", "Northstar", "Summit", "Evergreen",
    "Pioneer", "Nimbus", "Crest", "Quantum", "Silverline", "BrightPath",
    "Meridian", "Horizon", "Oakwood", "NextGen", "Atlas", "Redwood",
]
COMPANY_SUFFIXES = [
    "Technologies", "Solutions", "Systems", "Industries", "Enterprises",
    "Consulting", "Global", "Digital", "Networks", "Services",
]
INDUSTRIES = [
    "Technology", "Financial Services", "Manufacturing", "Healthcare",
    "Retail", "Telecommunications", "Education", "Logistics",
    "Professional Services", "Energy",
]
SEGMENTS = ["SMB", "Mid-Market", "Enterprise", "Startup"]
COUNTRIES = [
    "India", "United States", "United Kingdom", "Germany",
    "United Arab Emirates", "Singapore",
]
COUNTRY_WEIGHTS = [55, 15, 8, 8, 8, 6]
PRODUCT_CATEGORIES = [
    "Analytics", "CRM", "ERP", "Cloud", "Security",
    "Data Platform", "Automation", "Consulting",
]
PRODUCT_WORDS = [
    "Advanced", "Enterprise", "Professional", "Unified", "Intelligent",
    "Secure", "Integrated", "Business", "Cloud", "Strategic",
]
ORDER_STATUSES = ["PENDING", "CONFIRMED", "COMPLETED", "CANCELLED"]
ORDER_STATUS_WEIGHTS = [5, 15, 72, 8]
EMPLOYMENT_STATUSES = ["ACTIVE", "INACTIVE", "TERMINATED"]
EMPLOYMENT_STATUS_WEIGHTS = [94, 4, 2]
COMMISSION_STATUSES = ["DRAFT", "APPROVED", "PAID", "REJECTED"]
COMMISSION_STATUS_WEIGHTS = [10, 20, 65, 5]


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def random_date(rng: random.Random, start: date, end: date) -> date:
    days = (end - start).days
    return start + timedelta(days=rng.randint(0, days))


def company_name(rng: random.Random, number: int) -> str:
    prefix = rng.choice(COMPANY_PREFIXES)
    suffix = rng.choice(COMPANY_SUFFIXES)
    return f"{prefix} {suffix} {number:05d}"


def open_csv(output_dir: Path, table_name: str, headers: Sequence[str]):
    path = output_dir / f"{table_name}.csv"
    file_obj = path.open("w", newline="", encoding="utf-8")
    writer = csv.writer(file_obj)
    writer.writerow(headers)
    return file_obj, writer


def log_progress(table_name: str, current: int, total: int) -> None:
    if current == total or current % 50_000 == 0:
        logging.info("%s: %s / %s rows", table_name, f"{current:,}", f"{total:,}")


def generate_regions(output_dir: Path) -> int:
    file_obj, writer = open_csv(
        output_dir, "regions", ["region_id", "region_name", "country"]
    )
    try:
        for region_id, (name, country) in enumerate(REGIONS, start=1):
            writer.writerow([region_id, name, country])
    finally:
        file_obj.close()
    return len(REGIONS)


def generate_territories(output_dir: Path, rng: random.Random, count: int = 100) -> int:
    file_obj, writer = open_csv(
        output_dir,
        "territories",
        ["territory_id", "region_id", "territory_name", "territory_code", "is_active"],
    )
    try:
        for territory_id in range(1, count + 1):
            region_id = ((territory_id - 1) % len(REGIONS)) + 1
            city = rng.choice(CITIES)
            writer.writerow([
                territory_id,
                region_id,
                f"{city} Territory {territory_id:03d}",
                f"TER-{territory_id:04d}",
                True,
            ])
    finally:
        file_obj.close()
    return count


def generate_employees(
    output_dir: Path,
    rng: random.Random,
    employee_count: int,
    territory_count: int,
) -> tuple[int, list[int], list[int], list[str]]:
    director_count = max(1, min(4, employee_count // 30))
    manager_count = max(5, min(100, employee_count // 10))
    first_director_id = 2
    last_director_id = first_director_id + director_count - 1
    first_manager_id = last_director_id + 1
    last_manager_id = first_manager_id + manager_count - 1

    if last_manager_id >= employee_count:
        raise ValueError("Employee count is too small for the management hierarchy.")

    file_obj, writer = open_csv(
        output_dir,
        "employees",
        [
            "employee_id", "manager_id", "first_name", "last_name",
            "email", "job_title", "hire_date", "employment_status",
        ],
    )

    active_employee_ids: list[int] = []
    employee_territory_ids = [0] * employee_count
    statuses: list[str] = []

    try:
        for employee_id in range(1, employee_count + 1):
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)

            if employee_id == 1:
                manager_id = ""
                title = "Chief Sales Officer"
            elif employee_id <= last_director_id:
                manager_id = 1
                title = "Regional Sales Director"
            elif employee_id <= last_manager_id:
                manager_id = rng.randint(first_director_id, last_director_id)
                title = "Territory Sales Manager"
            else:
                manager_id = rng.randint(first_manager_id, last_manager_id)
                title = "Account Executive"

            status = rng.choices(
                EMPLOYMENT_STATUSES, weights=EMPLOYMENT_STATUS_WEIGHTS, k=1
            )[0]
            if employee_id == 1:
                status = "ACTIVE"

            hire = random_date(rng, date(2017, 1, 1), date(2024, 12, 31))
            email = f"{first.lower()}.{last.lower()}.{employee_id}@example.com"
            territory_id = rng.randint(1, territory_count)

            writer.writerow([
                employee_id, manager_id, first, last, email, title,
                hire.isoformat(), status,
            ])

            employee_territory_ids[employee_id - 1] = territory_id
            statuses.append(status)
            if status == "ACTIVE":
                active_employee_ids.append(employee_id)
    finally:
        file_obj.close()

    return employee_count, active_employee_ids, employee_territory_ids, statuses


def generate_employee_territories(
    output_dir: Path,
    employee_count: int,
    territory_ids: list[int],
    statuses: list[str],
) -> int:
    file_obj, writer = open_csv(
        output_dir,
        "employee_territories",
        ["assignment_id", "employee_id", "territory_id", "start_date", "end_date"],
    )
    try:
        for employee_id in range(1, employee_count + 1):
            end_date = "" if statuses[employee_id - 1] == "ACTIVE" else "2025-12-31"
            writer.writerow([
                employee_id,
                employee_id,
                territory_ids[employee_id - 1],
                "2020-01-01",
                end_date,
            ])
    finally:
        file_obj.close()
    return employee_count


def generate_customers(output_dir: Path, rng: random.Random, count: int) -> int:
    file_obj, writer = open_csv(
        output_dir,
        "customers",
        ["customer_id", "customer_name", "industry", "country", "customer_segment"],
    )
    try:
        for customer_id in range(1, count + 1):
            country = rng.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
            writer.writerow([
                customer_id,
                company_name(rng, customer_id),
                rng.choice(INDUSTRIES),
                country,
                rng.choices(SEGMENTS, weights=[35, 30, 20, 15], k=1)[0],
            ])
            log_progress("customers", customer_id, count)
    finally:
        file_obj.close()
    return count


def generate_products(output_dir: Path, rng: random.Random, count: int) -> list[Decimal]:
    prices: list[Decimal] = []
    file_obj, writer = open_csv(
        output_dir,
        "products",
        ["product_id", "product_name", "category", "list_price", "is_active"],
    )
    try:
        for product_id in range(1, count + 1):
            category = rng.choice(PRODUCT_CATEGORIES)
            price = Decimal(rng.randint(5_000, 2_000_000)) / Decimal("1")
            prices.append(price)
            writer.writerow([
                product_id,
                f"{rng.choice(PRODUCT_WORDS)} {category} {product_id:04d}",
                category,
                money(price),
                rng.random() >= 0.03,
            ])
    finally:
        file_obj.close()
    return prices


def generate_sales_orders(
    output_dir: Path,
    rng: random.Random,
    order_count: int,
    customer_count: int,
    active_employee_ids: list[int],
    employee_territory_ids: list[int],
) -> int:
    if not active_employee_ids:
        raise ValueError("No active employees available for sales orders.")

    file_obj, writer = open_csv(
        output_dir,
        "sales_orders",
        [
            "order_id", "order_reference", "customer_id", "employee_id",
            "territory_id", "order_date", "order_status", "currency_code",
        ],
    )
    start_date = date(2024, 1, 1)
    end_date = date(2026, 11, 24)

    try:
        for order_id in range(1, order_count + 1):
            employee_id = rng.choice(active_employee_ids)
            writer.writerow([
                order_id,
                f"SO-{order_id:09d}",
                rng.randint(1, customer_count),
                employee_id,
                employee_territory_ids[employee_id - 1],
                random_date(rng, start_date, end_date).isoformat(),
                rng.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS, k=1)[0],
                "INR",
            ])
            log_progress("sales_orders", order_id, order_count)
    finally:
        file_obj.close()
    return order_count


def generate_sales_order_lines(
    output_dir: Path,
    rng: random.Random,
    order_count: int,
    product_prices: list[Decimal],
    lines_per_order: int = 2,
) -> int:
    total = order_count * lines_per_order
    file_obj, writer = open_csv(
        output_dir,
        "sales_order_lines",
        [
            "order_line_id", "order_id", "product_id", "line_number",
            "quantity", "unit_price", "discount_amount",
        ],
    )
    try:
        line_id = 0
        for order_id in range(1, order_count + 1):
            for line_number in range(1, lines_per_order + 1):
                line_id += 1
                product_id = rng.randint(1, len(product_prices))
                quantity = rng.randint(1, 10)
                unit_price = product_prices[product_id - 1]
                gross = unit_price * quantity
                discount_rate = Decimal(rng.randint(0, 1500)) / Decimal("10000")
                discount = (gross * discount_rate).quantize(Decimal("0.01"))
                writer.writerow([
                    line_id,
                    order_id,
                    product_id,
                    line_number,
                    quantity,
                    money(unit_price),
                    money(discount),
                ])
            log_progress("sales_order_lines", order_id * lines_per_order, total)
    finally:
        file_obj.close()
    return total


def month_periods(year: int = TARGET_YEAR) -> list[tuple[str, str]]:
    periods = []
    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        periods.append((
            date(year, month, 1).isoformat(),
            date(year, month, last_day).isoformat(),
        ))
    return periods


def generate_sales_targets(
    output_dir: Path,
    rng: random.Random,
    employee_count: int,
) -> tuple[int, list[list[Decimal]]]:
    periods = month_periods()
    target_matrix: list[list[Decimal]] = []
    file_obj, writer = open_csv(
        output_dir,
        "sales_targets",
        ["target_id", "employee_id", "period_start", "period_end", "target_amount", "currency_code"],
    )
    try:
        target_id = 0
        for employee_id in range(1, employee_count + 1):
            employee_targets = []
            for period_start, period_end in periods:
                target_id += 1
                target = Decimal(rng.randint(150_000, 600_000))
                employee_targets.append(target)
                writer.writerow([
                    target_id, employee_id, period_start, period_end,
                    money(target), "INR",
                ])
            target_matrix.append(employee_targets)
    finally:
        file_obj.close()
    return employee_count * 12, target_matrix


def generate_incentive_plans(output_dir: Path, count: int = 20) -> int:
    file_obj, writer = open_csv(
        output_dir,
        "incentive_plans",
        ["plan_id", "plan_name", "plan_description", "plan_type", "effective_from", "effective_to", "is_active"],
    )
    try:
        for plan_id in range(1, count + 1):
            writer.writerow([
                plan_id,
                f"Sales Incentive Plan {plan_id:02d}",
                "Progressive commission plan for enterprise sales teams",
                "PROGRESSIVE",
                "2025-01-01",
                "",
                True,
            ])
    finally:
        file_obj.close()
    return count


def generate_commission_tiers(output_dir: Path, plan_count: int = 20) -> int:
    mins = [0.0, 50.0, 75.0, 100.0, 125.0]
    maxs = [50.0, 75.0, 100.0, 125.0, ""]
    rates = [0.01, 0.015, 0.02, 0.03, 0.04]

    file_obj, writer = open_csv(
        output_dir,
        "commission_tiers",
        ["tier_id", "plan_id", "min_attainment", "max_attainment", "commission_rate"],
    )
    try:
        tier_id = 0
        for plan_id in range(1, plan_count + 1):
            for minimum, maximum, rate in zip(mins, maxs, rates):
                tier_id += 1
                writer.writerow([tier_id, plan_id, minimum, maximum, rate])
    finally:
        file_obj.close()
    return plan_count * len(mins)


def generate_employee_incentive_plans(
    output_dir: Path,
    rng: random.Random,
    employee_count: int,
    plan_count: int = 20,
) -> tuple[int, list[int]]:
    assignments: list[int] = []
    file_obj, writer = open_csv(
        output_dir,
        "employee_incentive_plans",
        ["assignment_id", "employee_id", "plan_id", "effective_from", "effective_to"],
    )
    try:
        for employee_id in range(1, employee_count + 1):
            plan_id = rng.randint(1, plan_count)
            assignments.append(plan_id)
            writer.writerow([
                employee_id, employee_id, plan_id, "2025-01-01", "",
            ])
    finally:
        file_obj.close()
    return employee_count, assignments


def generate_commission_results(
    output_dir: Path,
    rng: random.Random,
    employee_count: int,
    target_matrix: list[list[Decimal]],
) -> int:
    periods = month_periods()
    total = employee_count * 12
    file_obj, writer = open_csv(
        output_dir,
        "commission_results",
        [
            "result_id", "assignment_id", "period_start", "period_end",
            "eligible_revenue", "target_amount", "attainment_percentage",
            "commission_rate", "commission_amount", "calculation_status",
        ],
    )
    try:
        result_id = 0
        for employee_id in range(1, employee_count + 1):
            for month_index, (period_start, period_end) in enumerate(periods):
                result_id += 1
                target = target_matrix[employee_id - 1][month_index]
                attainment = Decimal(rng.randint(4000, 16500)) / Decimal("100")
                revenue = (target * attainment / Decimal("100")).quantize(Decimal("0.01"))

                if attainment < 50:
                    rate = Decimal("0.01")
                elif attainment < 75:
                    rate = Decimal("0.015")
                elif attainment < 100:
                    rate = Decimal("0.02")
                elif attainment < 125:
                    rate = Decimal("0.03")
                else:
                    rate = Decimal("0.04")

                commission = (revenue * rate).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
                status = rng.choices(
                    COMMISSION_STATUSES,
                    weights=COMMISSION_STATUS_WEIGHTS,
                    k=1,
                )[0]

                writer.writerow([
                    result_id,
                    employee_id,
                    period_start,
                    period_end,
                    money(revenue),
                    money(target),
                    money(attainment),
                    f"{rate:.4f}",
                    money(commission),
                    status,
                ])
                log_progress("commission_results", result_id, total)
    finally:
        file_obj.close()
    return total


def validate_csv_counts(output_dir: Path, expected: dict[str, int]) -> dict[str, int]:
    actual: dict[str, int] = {}
    for table_name, expected_count in expected.items():
        path = output_dir / f"{table_name}.csv"
        with path.open("r", newline="", encoding="utf-8") as file_obj:
            row_count = sum(1 for _ in csv.reader(file_obj)) - 1
        actual[table_name] = row_count
        if row_count != expected_count:
            raise RuntimeError(
                f"{table_name}: expected {expected_count:,} rows, found {row_count:,}"
            )
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic enterprise sales CSV files using Python's standard library."
    )
    parser.add_argument("--scale", choices=["small", "full"], default="small")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    setup_logging()
    config = SMALL_SCALE if args.scale == "small" else FULL_SCALE

    employee_count = config["employees"]
    customer_count = config["customers"]
    product_count = config["products"]
    order_count = config["orders"]
    territory_count = 100
    plan_count = 20
    lines_per_order = 2

    rng = random.Random(args.seed)
    output_dir = PROJECT_ROOT / "data" / "generated" / args.scale
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Starting %s-scale generation (seed=%s).", args.scale, args.seed)
    logging.info("Output directory: %s", output_dir)

    # Only replace CSVs in the selected scale directory.
    for old_file in output_dir.glob("*.csv"):
        old_file.unlink()
    old_manifest = output_dir / "manifest.json"
    if old_manifest.exists():
        old_manifest.unlink()

    counts: dict[str, int] = {}
    counts["regions"] = generate_regions(output_dir)
    counts["territories"] = generate_territories(output_dir, rng, territory_count)

    (
        counts["employees"],
        active_employee_ids,
        employee_territory_ids,
        employee_statuses,
    ) = generate_employees(output_dir, rng, employee_count, territory_count)

    counts["employee_territories"] = generate_employee_territories(
        output_dir, employee_count, employee_territory_ids, employee_statuses
    )
    counts["customers"] = generate_customers(output_dir, rng, customer_count)
    product_prices = generate_products(output_dir, rng, product_count)
    counts["products"] = len(product_prices)

    counts["sales_orders"] = generate_sales_orders(
        output_dir, rng, order_count, customer_count,
        active_employee_ids, employee_territory_ids,
    )
    counts["sales_order_lines"] = generate_sales_order_lines(
        output_dir, rng, order_count, product_prices, lines_per_order
    )

    counts["sales_targets"], target_matrix = generate_sales_targets(
        output_dir, rng, employee_count
    )
    counts["incentive_plans"] = generate_incentive_plans(output_dir, plan_count)
    counts["commission_tiers"] = generate_commission_tiers(output_dir, plan_count)
    counts["employee_incentive_plans"], _ = generate_employee_incentive_plans(
        output_dir, rng, employee_count, plan_count
    )
    counts["commission_results"] = generate_commission_results(
        output_dir, rng, employee_count, target_matrix
    )

    expected = {
        "regions": 4,
        "territories": territory_count,
        "employees": employee_count,
        "employee_territories": employee_count,
        "customers": customer_count,
        "products": product_count,
        "sales_orders": order_count,
        "sales_order_lines": order_count * lines_per_order,
        "sales_targets": employee_count * 12,
        "incentive_plans": plan_count,
        "commission_tiers": plan_count * 5,
        "employee_incentive_plans": employee_count,
        "commission_results": employee_count * 12,
    }

    actual_counts = validate_csv_counts(output_dir, expected)
    total_rows = sum(actual_counts.values())

    manifest = {
        "generator": "Python standard library only",
        "scale": args.scale,
        "seed": args.seed,
        "counts": actual_counts,
        "total_rows": total_rows,
        "files_are_csv_only": True,
        "database_modified": False,
        "schema_note": (
            "CSV headers follow the project's earlier generator assumptions. "
            "Compare them with the actual PostgreSQL DDL before ingestion."
        ),
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    logging.info("Generation and CSV row-count validation completed.")
    for table_name, row_count in actual_counts.items():
        logging.info("%-28s %s", table_name, f"{row_count:,}")
    logging.info("TOTAL ROWS: %s", f"{total_rows:,}")
    logging.info("Manifest: %s", manifest_path)


if __name__ == "__main__":
    main()
