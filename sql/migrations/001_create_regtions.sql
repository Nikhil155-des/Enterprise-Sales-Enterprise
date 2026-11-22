CREATE TABLE analytics.regions (

    region_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    region_name VARCHAR(100) NOT NULL,

    country VARCHAR(100) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_region_name_country
        UNIQUE (region_name, country)

);