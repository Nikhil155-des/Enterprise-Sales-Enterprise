
BEGIN;

-- =========================================
-- 1. TERRITORIES
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.territories (
    territory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region_id BIGINT NOT NULL,
    territory_name VARCHAR(100) NOT NULL,
    territory_code VARCHAR(30) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_territory_region
        FOREIGN KEY (region_id)
        REFERENCES analytics.regions(region_id),

    CONSTRAINT uq_territory_region
        UNIQUE (region_id, territory_name)
);


-- =========================================
-- 2. EMPLOYEES
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.employees (
    employee_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    manager_id BIGINT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    job_title VARCHAR(100) NOT NULL,
    hire_date DATE NOT NULL,
    employment_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_employee_manager
        FOREIGN KEY (manager_id)
        REFERENCES analytics.employees(employee_id),

    CONSTRAINT chk_employment_status
        CHECK (employment_status IN ('ACTIVE', 'INACTIVE', 'TERMINATED')),

    CONSTRAINT chk_employee_manager
        CHECK (manager_id IS NULL OR manager_id <> employee_id)
);


-- =========================================
-- 3. EMPLOYEE TERRITORIES
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.employee_territories (
    assignment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    territory_id BIGINT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_assignment_employee
        FOREIGN KEY (employee_id)
        REFERENCES analytics.employees(employee_id),

    CONSTRAINT fk_assignment_territory
        FOREIGN KEY (territory_id)
        REFERENCES analytics.territories(territory_id),

    CONSTRAINT chk_assignment_dates
        CHECK (end_date IS NULL OR end_date >= start_date),

    CONSTRAINT uq_employee_territory_start
        UNIQUE (employee_id, territory_id, start_date)
);


-- =========================================
-- 4. CUSTOMERS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR(200) NOT NULL,
    industry VARCHAR(100),
    country VARCHAR(100) NOT NULL,
    customer_segment VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =========================================
-- 5. PRODUCTS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    list_price NUMERIC(14,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_product_price
        CHECK (list_price >= 0)
);


-- =========================================
-- 6. SALES ORDERS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.sales_orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_reference VARCHAR(50) NOT NULL UNIQUE,
    customer_id BIGINT NOT NULL,
    employee_id BIGINT NOT NULL,
    territory_id BIGINT NOT NULL,
    order_date DATE NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    currency_code CHAR(3) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id)
        REFERENCES analytics.customers(customer_id),

    CONSTRAINT fk_order_employee
        FOREIGN KEY (employee_id)
        REFERENCES analytics.employees(employee_id),

    CONSTRAINT fk_order_territory
        FOREIGN KEY (territory_id)
        REFERENCES analytics.territories(territory_id),

    CONSTRAINT chk_order_status
        CHECK (order_status IN ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED'))
);


-- =========================================
-- 7. SALES ORDER LINES
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.sales_order_lines (
    order_line_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    line_number INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(14,2) NOT NULL,
    discount_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_line_order
        FOREIGN KEY (order_id)
        REFERENCES analytics.sales_orders(order_id),

    CONSTRAINT fk_line_product
        FOREIGN KEY (product_id)
        REFERENCES analytics.products(product_id),

    CONSTRAINT chk_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_unit_price
        CHECK (unit_price >= 0),

    CONSTRAINT chk_discount
        CHECK (discount_amount >= 0 AND discount_amount <= quantity * unit_price),

    CONSTRAINT chk_line_number
        CHECK (line_number > 0),

    CONSTRAINT uq_order_line
        UNIQUE (order_id, line_number)
);


-- =========================================
-- 8. SALES TARGETS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.sales_targets (
    target_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    target_amount NUMERIC(16,2) NOT NULL,
    currency_code CHAR(3) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_target_employee
        FOREIGN KEY (employee_id)
        REFERENCES analytics.employees(employee_id),

    CONSTRAINT chk_target_amount
        CHECK (target_amount >= 0),

    CONSTRAINT chk_target_period
        CHECK (period_end >= period_start),

    CONSTRAINT uq_employee_target_period
        UNIQUE (employee_id, period_start, period_end)
);


-- =========================================
-- 9. INCENTIVE PLANS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.incentive_plans (
    plan_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_name VARCHAR(150) NOT NULL,
    plan_description TEXT,
    plan_type VARCHAR(30) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT chk_plan_type
        CHECK (plan_type IN ('FLAT_RATE', 'PROGRESSIVE')),

    CONSTRAINT chk_plan_dates
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);


-- =========================================
-- 10. COMMISSION TIERS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.commission_tiers (
    tier_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id BIGINT NOT NULL,
    min_attainment NUMERIC(7,2) NOT NULL,
    max_attainment NUMERIC(7,2),
    commission_rate NUMERIC(7,5) NOT NULL,

    CONSTRAINT fk_tier_plan
        FOREIGN KEY (plan_id)
        REFERENCES analytics.incentive_plans(plan_id),

    CONSTRAINT chk_tier_attainment
        CHECK (
            min_attainment >= 0
            AND (max_attainment IS NULL OR max_attainment > min_attainment)
        ),

    CONSTRAINT chk_commission_rate
        CHECK (commission_rate BETWEEN 0 AND 1),

    CONSTRAINT uq_plan_tier_min
        UNIQUE (plan_id, min_attainment)
);


-- =========================================
-- 11. EMPLOYEE INCENTIVE PLANS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.employee_incentive_plans (
    assignment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    plan_id BIGINT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,

    CONSTRAINT fk_incentive_employee
        FOREIGN KEY (employee_id)
        REFERENCES analytics.employees(employee_id),

    CONSTRAINT fk_incentive_plan
        FOREIGN KEY (plan_id)
        REFERENCES analytics.incentive_plans(plan_id),

    CONSTRAINT chk_incentive_assignment_dates
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);


-- =========================================
-- 12. COMMISSION RESULTS
-- =========================================

CREATE TABLE IF NOT EXISTS analytics.commission_results (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assignment_id BIGINT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    eligible_revenue NUMERIC(16,2) NOT NULL,
    target_amount NUMERIC(16,2) NOT NULL,
    attainment_percentage NUMERIC(7,2) NOT NULL,
    commission_rate NUMERIC(7,5) NOT NULL,
    commission_amount NUMERIC(16,2) NOT NULL,
    calculation_status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_commission_assignment
        FOREIGN KEY (assignment_id)
        REFERENCES analytics.employee_incentive_plans(assignment_id),

    CONSTRAINT chk_commission_period
        CHECK (period_end >= period_start),

    CONSTRAINT chk_commission_values
        CHECK (
            eligible_revenue >= 0
            AND target_amount >= 0
            AND attainment_percentage >= 0
            AND commission_rate BETWEEN 0 AND 1
            AND commission_amount >= 0
        ),

    CONSTRAINT chk_commission_status
        CHECK (calculation_status IN ('DRAFT', 'APPROVED', 'PAID', 'REJECTED')),

    CONSTRAINT uq_commission_period
        UNIQUE (assignment_id, period_start, period_end)
);


-- =========================================
-- 13. INDEXES
-- =========================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_active_territory
ON analytics.employee_territories(employee_id)
WHERE end_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_employees_manager
ON analytics.employees(manager_id);

CREATE INDEX IF NOT EXISTS idx_territories_region
ON analytics.territories(region_id);

CREATE INDEX IF NOT EXISTS idx_assignment_territory
ON analytics.employee_territories(territory_id);

CREATE INDEX IF NOT EXISTS idx_orders_employee_date
ON analytics.sales_orders(employee_id, order_date);

CREATE INDEX IF NOT EXISTS idx_orders_customer
ON analytics.sales_orders(customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_territory_date
ON analytics.sales_orders(territory_id, order_date);

CREATE INDEX IF NOT EXISTS idx_order_lines_product
ON analytics.sales_order_lines(product_id);

CREATE INDEX IF NOT EXISTS idx_targets_employee_period
ON analytics.sales_targets(employee_id, period_start);

CREATE INDEX IF NOT EXISTS idx_commission_period
ON analytics.commission_results(period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_employee_incentive
ON analytics.employee_incentive_plans(employee_id, effective_from);

CREATE INDEX IF NOT EXISTS idx_tiers_plan
ON analytics.commission_tiers(plan_id);

COMMIT;
