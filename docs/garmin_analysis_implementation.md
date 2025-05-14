# Garmin Data Analysis Framework Implementation Plan

## Overview

This document outlines the implementation plan for the Garmin data analysis framework described in `plan_for_analysis_engine.md`. The implementation will follow a phased approach, starting with the foundation and core sleep/recovery metrics.

## Current State Assessment

The codebase already includes:

- `GarminDataAnalysisService` class that uses DuckDB for storing raw Garmin data
- Basic table structure with `garmin_raw_data` including JSON columns
- Functions for fetching and storing data from Garmin Connect
- Basic querying capabilities for the stored data

## Implementation Approach

We'll implement the framework in phases, following the layered architecture described in the plan:

1. Foundation & Core Sleep/Recovery Metrics (Stage 1) - Current focus
2. Training Load & Expanded Insights (Stage 2)
3. Advanced Analysis & Refinements (Stage 3)
4. Iterative Refinement & ML (Future)

## Directory Structure

We'll extend the existing service by adding a structured module within the `telegram_bot/service/` directory:

```
telegram_bot/service/
├── garmin_data_analysis_service.py  (existing)
└── garmin_analysis/  (new)
    ├── __init__.py
    ├── common/
    │   ├── __init__.py
    │   ├── db_utils.py
    │   ├── data_models.py
    │   └── constants.py
    ├── core_metrics/
    │   ├── __init__.py
    │   ├── sleep_metrics.py
    │   ├── recovery_metrics.py
    │   └── queries/
    │       ├── sleep_quality.sql
    │       └── ans_status.sql
    ├── baselining/
    │   ├── __init__.py
    │   ├── baseline_calculator.py
    │   ├── threshold_engine.py
    │   └── queries/
    │       └── calculate_baselines.sql
    ├── interpretation/
    │   ├── __init__.py
    │   ├── interpretation_engine.py
    │   └── rules/
    │       └── readiness_rules.py
    └── insights/
        ├── __init__.py
        ├── insight_generator.py
        └── templates/
            └── daily_briefing.txt
```

## Stage 1 Implementation Todos

### 1. Data Foundation

1. **Enhance GarminDataAnalysisService**
   - [x] Review current implementation in `telegram_bot/service/garmin_data_analysis_service.py` 
   - [x] Ensure the `garmin_raw_data` table has the correct schema
   - [x] Add robust error handling for database operations
   - [x] Add logging for tracking data processing steps

2. **DB Utilities**
   - [x] Create `telegram_bot/service/garmin_analysis/common/db_utils.py`
   - [x] Implement helper functions for DuckDB connections
   - [x] Create `execute_query` function for running SQL with parameters
   - [x] Create function to load SQL queries from files
   - [x] Implement transaction management utilities

3. **Data Models**
   - [x] Create `telegram_bot/service/garmin_analysis/common/data_models.py`
   - [x] Implement Pydantic models for all metrics outputs
   - [x] Create models for insights and interpretation results
   - [x] Add models for baseline calculations

4. **Constants**
   - [x] Create `telegram_bot/service/garmin_analysis/common/constants.py`
   - [x] Define threshold values (e.g., for Z-scores)
   - [x] Set up configuration constants for baselines
   - [x] Add any other necessary constants

### 2. Core Sleep & Recovery Metrics Layer

1. **Sleep Metrics Calculation**
   - [x] Create `telegram_bot/service/garmin_analysis/core_metrics/sleep_metrics.py`
   - [x] Implement Total Sleep Time (TST) calculation
   - [x] Implement Sleep Efficiency (SE) calculation
   - [x] Implement WASO calculation (simplified initially)
   - [x] Implement Sleep Stage Percentages calculation
   - [x] Add Avg. Stress During Sleep calculation
   - [x] Create SQL queries in `queries/sleep_quality.sql`

2. **Recovery & ANS Metrics**
   - [x] Create `telegram_bot/service/garmin_analysis/core_metrics/recovery_metrics.py`
   - [x] Implement Resting Heart Rate (RHR) extraction
   - [x] Implement Nightly HRV extraction
   - [x] Implement 7-Day Rolling Average HRV calculation
   - [x] Implement Body Battery Dynamics calculation
   - [x] Create SQL queries in `queries/ans_status.sql`

### 3. Personalized Baselining Layer

1. **Baseline Calculator**
   - [x] Create `telegram_bot/service/garmin_analysis/baselining/baseline_calculator.py`
   - [x] Implement functions to calculate rolling baselines
   - [x] Add functions to fetch baseline values for metrics
   - [x] Implement `calculate_sleep_baselines` and `calculate_recovery_baselines` methods
   - [x] Create metric status calculation using Z-scores
   - [x] Add support for saving/loading baselines to/from files

2. **Status Determination**
   - [x] Implement status determination logic in `BaselineCalculator`
   - [x] Add customizable threshold values in `constants.py`
   - [x] Support different thresholds for metrics where lower vs. higher is better
   - [x] Create helper functions to compare current metrics against baselines

### 4. Basic Interpretation Engine

1. **Interpretation Engine**
   - [ ] Create `telegram_bot/service/garmin_analysis/interpretation/interpretation_engine.py`
   - [ ] Implement function to analyze metrics with status
   - [ ] Add initial rules for sleep and recovery assessment

2. **Rules Implementation**
   - [ ] Create `telegram_bot/service/garmin_analysis/interpretation/rules/readiness_rules.py`
   - [ ] Implement the recovery/readiness rules
   - [ ] Create simple rule functions for pattern detection

### 5. Basic Insight Generation

1. **Insight Generator**
   - [ ] Create `telegram_bot/service/garmin_analysis/insights/insight_generator.py`
   - [ ] Implement basic templating for insights
   - [ ] Add functions to generate daily briefings

2. **Templates**
   - [ ] Create `telegram_bot/service/garmin_analysis/insights/templates/`
   - [ ] Add template for daily briefing
   - [ ] Add template for recovery status

### 6. API & Integration

1. **Main Analysis Interface**
   - [ ] Update `garmin_data_analysis_service.py` with new endpoint methods
   - [ ] Add method to analyze daily sleep & recovery
   - [ ] Create method to generate basic insights

2. **Service Factory Integration**
   - [ ] Update `service_factory.py` to wire up new components
   - [ ] Ensure dependency injection is properly set up

### 7. Testing

1. **Unit Tests**
   - [x] Create unit tests for core metrics calculations
   - [x] Add tests for baseline calculations
   - [ ] Implement tests for interpretation rules

2. **Integration Tests**
   - [ ] Add test for the complete flow from data to insights
   - [ ] Create fixtures with sample Garmin data
   - [ ] Test performance with larger datasets

## Implementation Schedule

### Week 1: Foundation and Core Metrics
- **Days 1-2**: Set up project structure, implement common utilities
- **Days 3-5**: Implement core sleep and recovery metrics

### Week 2: Baselining, Interpretation, and Integration
- **Days 1-2**: Implement baselining system ✅
- **Days 3-4**: Create interpretation engine and insight generator
- **Day 5**: Integrate with existing service and add tests

## Technical Considerations

### 1. SQL Optimization

We'll need to ensure DuckDB queries are optimized for:
- Efficient JSON extraction
- Appropriate use of indexes
- Minimal processing of large arrays

### 2. Async Support

The implementation should maintain async compatibility with the rest of the application:
- Use async functions where needed
- Ensure non-blocking database operations
- Consider thread pool for heavy calculations

### 3. Error Handling

Robust error handling is essential for:
- Missing or incomplete data
- Edge cases in baseline calculations
- JSON parsing issues
- Database connection problems

### 4. Configuration Management

We'll implement a flexible configuration system to allow:
- Adjustable thresholds for different metrics
- Customizable baseline periods
- Tunable interpretation rules

## Implementation Guidelines

1. Follow the layered architecture in `plan_for_analysis_engine.md`
2. Reuse existing code patterns where appropriate
3. Maintain compatibility with the existing service approach
4. Use type hints throughout the implementation
5. Add docstrings to all functions and classes
6. Submit PRs after completing each major section for easier review
7. Run linting and type checking before submitting PRs

## DuckDB Best Practices

1. Use parameter binding for all SQL queries
2. Extract complex JSON with appropriate error handling
3. Use CTEs for better readability of complex queries
4. Consider performance impact of JSON operations
5. Separate metric extraction SQL for better maintenance