create table if not exists ACTUARIAL_SELECTION_VERSION (
    SELECTION_VERSION_ID varchar not null,
    MODEL_RUN_ID varchar not null,
    AS_OF_DATE date not null,
    STATUS varchar not null,
    CREATED_BY varchar not null,
    CREATED_AT timestamp_tz not null,
    COMMENT varchar,
    SUBMITTED_BY varchar,
    SUBMITTED_AT timestamp_tz,
    APPROVED_BY varchar,
    APPROVED_AT timestamp_tz,
    REJECTED_BY varchar,
    REJECTED_AT timestamp_tz,
    REVIEW_COMMENT varchar,
    ROW_VERSION integer not null,
    primary key (SELECTION_VERSION_ID)
);

create table if not exists ACTUARIAL_LDF_SELECTION (
    SELECTION_VERSION_ID varchar not null,
    TRIANGLE_GRAIN varchar not null,
    DEVELOPMENT_POOL_ID varchar not null,
    POOL_LEVEL varchar not null,
    LINE_OF_BUSINESS varchar not null,
    MEASURE_TYPE varchar not null,
    FROM_AGE_MONTHS integer not null,
    TO_AGE_MONTHS integer not null,
    SELECTED_METHOD varchar not null,
    SELECTED_LDF number(38, 12) not null,
    SELECTION_SOURCE varchar not null,
    SELECTION_REASON varchar,
    CREATED_BY varchar not null,
    CREATED_AT timestamp_tz not null
);

create table if not exists ACTUARIAL_TAIL_SELECTION (
    SELECTION_VERSION_ID varchar not null,
    TRIANGLE_GRAIN varchar not null,
    DEVELOPMENT_POOL_ID varchar not null,
    POOL_LEVEL varchar not null,
    LINE_OF_BUSINESS varchar not null,
    MEASURE_TYPE varchar not null,
    DEVELOPMENT_METHOD varchar not null,
    SELECTED_TAIL_METHOD varchar not null,
    SELECTED_TAIL_FACTOR number(38, 12) not null,
    SELECTION_SOURCE varchar not null,
    SELECTION_REASON varchar,
    CREATED_BY varchar not null,
    CREATED_AT timestamp_tz not null
);

create table if not exists ACTUARIAL_ULTIMATE_SELECTION (
    SELECTION_VERSION_ID varchar not null,
    TRIANGLE_GRAIN varchar not null,
    DEVELOPMENT_POOL_ID varchar not null,
    POOL_LEVEL varchar not null,
    LINE_OF_BUSINESS varchar not null,
    MEASURE_TYPE varchar not null,
    ACCIDENT_PERIOD date not null,
    DEVELOPMENT_METHOD varchar not null,
    TAIL_METHOD varchar not null,
    SELECTED_ULTIMATE_METHOD varchar not null,
    SELECTED_ULTIMATE_VALUE number(38, 8) not null,
    SELECTION_SOURCE varchar not null,
    SELECTION_REASON varchar,
    CREATED_BY varchar not null,
    CREATED_AT timestamp_tz not null
);

create table if not exists ACTUARIAL_APPROVAL_EVENT (
    EVENT_ID varchar not null,
    SELECTION_VERSION_ID varchar not null,
    EVENT_TYPE varchar not null,
    FROM_STATUS varchar,
    TO_STATUS varchar not null,
    ACTOR varchar not null,
    COMMENT varchar,
    DETAILS variant,
    CREATED_AT timestamp_tz not null,
    primary key (EVENT_ID)
);

create table if not exists ACTUARIAL_PIPELINE_RUN (
    PIPELINE_RUN_ID varchar not null,
    SELECTION_VERSION_ID varchar not null,
    MODEL_RUN_ID varchar not null,
    AIRFLOW_DAG_ID varchar not null,
    AIRFLOW_DAG_RUN_ID varchar not null,
    STATUS varchar not null,
    TRIGGERED_BY varchar not null,
    TRIGGERED_AT timestamp_tz not null,
    UPDATED_AT timestamp_tz,
    ERROR_MESSAGE varchar,
    primary key (PIPELINE_RUN_ID)
);
