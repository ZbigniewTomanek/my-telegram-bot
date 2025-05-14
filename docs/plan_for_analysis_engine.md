Okay, here is a comprehensive implementation plan for the Garmin data analysis framework using DuckDB.

## Garmin Data Analysis Framework Implementation Plan

**Current Date:** Wednesday, May 14, 2025

### 1\. High-Level Architecture Diagram (Text Description)

The framework follows a layered architecture, promoting separation of concerns and modularity.

```
[Garmin Connect API] -> [Data Acquisition & Preparation Layer (Python Service)]
                                       | (Stores data in DuckDB)
                                       V
                -------------------- [DuckDB: garmin_raw_data table] --------------------
                |                       |                       |                       |
                V                       V                       V                       V
[Core Metric Calculation Layer (DuckDB SQL)] -> [Personalized Baselining & Thresholding Layer (DuckDB SQL & Python)]
                |                                       |
                V                                       V
[Multi-Dimensional Interpretation Engine (Python rules, potentially SQL for patterns)]
                |
                V
[Actionable Insight & Recommendation Generation Layer (Python logic, text templates)]
                |
                V
[Exploratory Correlation Analysis Layer (DuckDB SQL for correlations, Python for complex analysis)]
```

  * **Data Acquisition & Preparation Layer**: Existing `GarminDataAnalysisService` fetches data from Garmin Connect and stores it in a user-specific DuckDB database in the `garmin_raw_data` table. This layer ensures data is available in a structured (JSON) format.
  * **DuckDB (`garmin_raw_data` table)**: Central data store. Contains raw JSON blobs for different data types, per user, per date. This is the primary source for all analytical queries.
  * **Core Metric Calculation Layer**: Consists of DuckDB SQL queries that process the raw JSON data to calculate fundamental health and performance metrics.
  * **Personalized Baselining and Thresholding Layer**: Uses DuckDB SQL to calculate rolling baselines for key metrics and applies logic (SQL or Python) to determine deviation thresholds.
  * **Multi-Dimensional Interpretation Engine**: Python-based logic that combines multiple metrics and their states (relative to baselines) to infer user status (e.g., recovery, fatigue). May use SQL for identifying specific patterns.
  * **Actionable Insight and Recommendation Generation Layer**: Python logic that translates interpretations into human-readable and actionable advice.
  * **Exploratory Correlation Analysis Layer**: Utilizes DuckDB SQL for statistical correlations and Python for more advanced event coincidence analysis or pattern matching.

### 2\. File Structure

```
garmin_analyzer/
├── main.py                     # Main application entry point, orchestrator
├── config.py                   # Configuration settings (DB paths, API keys, etc.)
│
├── data_acquisition/
│   └── garmin_data_service.py  # Existing service (modified for clarity if needed)
│
├── core_metrics/
│   ├── __init__.py
│   ├── sleep_metrics.py        # Functions/classes for sleep metric calculations
│   ├── recovery_metrics.py     # Functions/classes for recovery/ANS metrics
│   ├── training_load_metrics.py # Functions/classes for training load metrics
│   ├── fitness_metrics.py      # Functions/classes for long-term fitness metrics
│   └── queries/                # SQL queries for core metrics
│       ├── sleep_quality.sql
│       ├── ans_status.sql
│       ├── training_load.sql
│       └── long_term_fitness.sql
│
├── baselining/
│   ├── __init__.py
│   ├── baseline_calculator.py  # Calculates and stores/updates baselines
│   ├── threshold_engine.py     # Determines deviation status based on baselines
│   └── queries/
│       └── calculate_baselines.sql
│
├── interpretation/
│   ├── __init__.py
│   ├── interpretation_engine.py # Rules for combined metric analysis
│   └── rules/
│       ├── readiness_rules.py
│       └── fatigue_rules.py
│
├── insights/
│   ├── __init__.py
│   ├── insight_generator.py    # Generates actionable insights and recommendations
│   └── templates/              # Text templates for insights
│       ├── daily_briefing.txt
│       └── training_guidance.txt
│
├── correlation_analysis/
│   ├── __init__.py
│   ├── correlation_engine.py   # Performs correlation analyses
│   └── queries/
│       └── lagged_correlations.sql
│
├── common/
│   ├── __init__.py
│   ├── db_utils.py             # DuckDB connection management, query execution helpers
│   ├── data_models.py          # Pydantic models for structured data, inputs, outputs
│   └── constants.py            # Threshold values, EWMA alpha, etc.
│
├── tests/                      # Unit and integration tests
│   ├── test_core_metrics.py
│   ├── test_baselining.py
│   └── ...
│
└── docs/                       # Documentation
    ├── architecture.md
    └── api_reference.md

```

### 3\. Detailed Component Specifications

#### A. Data Acquisition & Preparation Layer

  * **Purpose**: Fetch data from Garmin Connect, preprocess (minimal, as it's stored as JSON), and store it in DuckDB. This layer is largely covered by the existing `GarminDataAnalysisService`.
  * **File Structure**: `garmin_analyzer/data_acquisition/garmin_data_service.py`
  * **Key Class**: `GarminDataAnalysisService` (as provided, potentially refactored for clarity if needed).
      * `_setup_database(user_id)`: Ensures the `garmin_raw_data` table exists.
          * `garmin_raw_data` schema: `(user_id INTEGER, date DATE, data_type VARCHAR, json_data JSON, fetch_timestamp TIMESTAMP, PRIMARY KEY (user_id, date, data_type))`
      * `Workspace_and_store_period_data(...)`: Fetches data and stores it.
  * **Dependencies**: External Garmin Connect API, `common/db_utils.py`.
  * **Error Handling**:
      * Retry mechanisms for API calls.
      * Logging of fetching errors.
      * Graceful handling of missing data for a day/data\_type by not inserting a row or inserting with null `json_data`.
      * Database connection errors.

#### B. Core Metric Calculation Layer

  * **Purpose**: Calculate all fundamental metrics from the raw JSON data stored in DuckDB.
  * **File Structure**: `garmin_analyzer/core_metrics/`
  * **Function/Class Definitions**: Each `*.py` file in `core_metrics` will contain Python functions that orchestrate the execution of SQL queries and potentially perform minor transformations if absolutely necessary (though preference is for SQL).
      * Example: `core_metrics/sleep_metrics.py`
        ```python
        from ..common.db_utils import execute_query
        from ..common.data_models import SleepMetricsOutput # Pydantic model

        def calculate_daily_sleep_metrics(db_conn, user_id: int, date_str: str) -> SleepMetricsOutput:
            """Calculates sleep metrics for a given user and date."""
            query = """... SQL query from sleep_quality.sql ...""" # Loaded from file
            params = {'user_id': user_id, 'target_date': date_str}
            result = execute_query(db_conn, query, params)
            # Transform result to Pydantic model, handle None cases
            return SleepMetricsOutput(**result[0]) if result else None
        ```
  * **Dependencies**: `common/db_utils.py`, `common/data_models.py`. SQL queries in `core_metrics/queries/`.
  * **Error Handling**:
      * SQL query execution errors (logged, may return None or raise custom exceptions).
      * Handling of missing `data_type` entries in `garmin_raw_data` (queries should use `LEFT JOIN` and handle `NULL`s gracefully).
      * Type conversion errors if data in JSON is not as expected.
  * **DuckDB Queries**: See Section 4.

#### C. Personalized Baselining and Thresholding Layer

  * **Purpose**: Establish individual baselines for key metrics and define thresholds for normal, warning, and concerning deviations.
  * **File Structure**: `garmin_analyzer/baselining/`
  * **Function/Class Definitions**:
      * `baselining/baseline_calculator.py`:
        ```python
        from ..common.db_utils import execute_query
        from ..common.data_models import BaselineMetrics # Pydantic model

        class BaselineCalculator:
            def __init__(self, db_conn):
                self.db_conn = db_conn

            def update_baselines(self, user_id: int, metrics_df): # metrics_df is a DataFrame of daily core metrics
                """Calculates and updates/stores rolling baselines (e.g., 30/60 day averages, SDs).
                   This might involve more complex logic than a single query if baselines are stored.
                   Alternatively, baselines can be calculated on-the-fly.
                   For this plan, we'll assume on-the-fly calculation integrated into metric queries or specific baseline queries.
                """
                # For simplicity, baselines will often be calculated directly in queries needing them.
                # If stored, this class would manage a 'user_baselines' table.
                pass

            def get_metric_with_baseline_status(self, user_id: int, date_str: str, metric_name: str, current_value: float):
                # This function would fetch baseline values (mean, std_dev) for the metric
                # and then use ThresholdEngine to determine status.
                # Example for RHR baseline (30-day rolling average and SD):
                query = """
                    WITH UserDailyRHR AS (
                        SELECT
                            date,
                            CAST(json_extract_string(json_data, '$.dailySleepDTO.restingHeartRateInBeatsPerMinute') AS INTEGER) AS rhr
                        FROM garmin_raw_data
                        WHERE user_id = :user_id AND data_type = 'sleep' AND json_extract_string(json_data, '$.dailySleepDTO.restingHeartRateInBeatsPerMinute') IS NOT NULL
                        ORDER BY date
                    ),
                    RollingRHRBaseline AS (
                        SELECT
                            AVG(rhr) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS baseline_rhr_30d_avg,
                            STDDEV_SAMP(rhr) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS baseline_rhr_30d_stddev
                        FROM UserDailyRHR
                        WHERE date <= :target_date -- or a range for calculating baseline up to a point
                        ORDER BY date DESC
                        LIMIT 1 -- Get the latest baseline calculation up to target_date
                    )
                    SELECT baseline_rhr_30d_avg, baseline_rhr_30d_stddev FROM RollingRHRBaseline;
                """
                params = {'user_id': user_id, 'target_date': date_str}
                baseline_data = execute_query(self.db_conn, query, params)
                if not baseline_data or baseline_data[0]['baseline_rhr_30d_avg'] is None:
                    return "No Baseline", None

                mean_val = baseline_data[0]['baseline_rhr_30d_avg']
                std_dev_val = baseline_data[0]['baseline_rhr_30d_stddev'] if baseline_data[0]['baseline_rhr_30d_stddev'] is not None else 0 # Handle cases with insufficient data for STDEV

                # Use ThresholdEngine
                engine = ThresholdEngine(metric_name, lower_is_better=(metric_name == "RHR")) # Example
                status = engine.determine_status(current_value, mean_val, std_dev_val)
                return status, {'mean': mean_val, 'std_dev': std_dev_val}

        ```
      * `baselining/threshold_engine.py`:
        ```python
        from enum import Enum

        class DeviationStatus(Enum):
            NORMAL = "Normal"
            OPTIMAL = "Optimal" # For metrics like HRV where higher is better or RHR where lower is better
            SLIGHT_DEVIATION_WARNING = "Slight Deviation/Warning"
            CONCERNING_DEVIATION_RED = "Concerning Deviation"
            NO_BASELINE = "No Baseline"

        class ThresholdEngine:
            def __init__(self, metric_name: str, lower_is_better: bool = False, higher_is_better: bool = False):
                self.metric_name = metric_name
                self.lower_is_better = lower_is_better
                self.higher_is_better = higher_is_better
                # Thresholds (can be made configurable)
                self.sd_warning_lower = -1.5
                self.sd_warning_upper = 1.5
                self.sd_optimal_lower_ดี = -0.75 # for lower_is_better, e.g. RHR
                self.sd_optimal_upper_ดี = 0.75 # for higher_is_better, e.g. HRV

                if lower_is_better:
                    self.sd_normal_upper = 0.75
                    self.sd_warning_upper_threshold = 1.5 # e.g. RHR +1.5SD from mean
                    self.sd_red_upper_threshold = 2.0 # e.g. RHR +2.0SD (or clinical)

                elif higher_is_better:
                    self.sd_normal_lower = -0.75
                    self.sd_warning_lower_threshold = -1.5 # e.g. HRV -1.5SD from mean
                    self.sd_red_lower_threshold = -2.0 # e.g. HRV -2.0SD

                else: # Default: symmetrical deviation
                    self.sd_normal_lower = -0.75
                    self.sd_normal_upper = 0.75
                    self.sd_warning_threshold = 1.5 # abs deviation
                    self.sd_red_threshold = 2.0 # abs deviation


            def determine_status(self, current_value: float, baseline_mean: float, baseline_std_dev: float) -> DeviationStatus:
                if baseline_mean is None or baseline_std_dev is None: # or baseline_std_dev == 0 after few samples
                    return DeviationStatus.NO_BASELINE
                if baseline_std_dev == 0: # Avoid division by zero if all baseline values are the same
                    if current_value == baseline_mean:
                        return DeviationStatus.NORMAL
                    else: # Any deviation is large if std_dev is 0
                        return DeviationStatus.CONCERNING_DEVIATION_RED

                z_score = (current_value - baseline_mean) / baseline_std_dev

                if self.lower_is_better:
                    if z_score < self.sd_warning_lower: # Significantly lower than usual (very good for RHR)
                        return DeviationStatus.OPTIMAL # Example: RHR much lower than baseline
                    elif z_score <= self.sd_normal_upper: # Normal or slightly better
                        return DeviationStatus.NORMAL
                    elif z_score <= self.sd_warning_upper_threshold:
                        return DeviationStatus.SLIGHT_DEVIATION_WARNING
                    else: # z_score > self.sd_warning_upper_threshold
                        return DeviationStatus.CONCERNING_DEVIATION_RED
                elif self.higher_is_better:
                    if z_score > self.sd_optimal_upper_ดี: # Significantly higher than usual (very good for HRV)
                        return DeviationStatus.OPTIMAL
                    elif z_score >= self.sd_normal_lower: # Normal or slightly better
                        return DeviationStatus.NORMAL
                    elif z_score >= self.sd_warning_lower_threshold:
                        return DeviationStatus.SLIGHT_DEVIATION_WARNING
                    else: # z_score < self.sd_warning_lower_threshold
                        return DeviationStatus.CONCERNING_DEVIATION_RED
                else: # Symmetrical
                    if abs(z_score) <= self.sd_normal_upper:
                        return DeviationStatus.NORMAL
                    elif abs(z_score) <= self.sd_warning_threshold:
                        return DeviationStatus.SLIGHT_DEVIATION_WARNING
                    else:
                        return DeviationStatus.CONCERNING_DEVIATION_RED
                return DeviationStatus.NORMAL # Default
        ```
  * **Dependencies**: `core_metrics` (for input values), `common/db_utils.py`.
  * **Error Handling**: Division by zero if SD is 0 (handled), insufficient data for baseline calculation.
  * **DuckDB Queries**: Rolling averages and standard deviations (see example in `BaselineCalculator` and specific baseline queries in Section 4).

#### D. Multi-Dimensional Interpretation Engine

  * **Purpose**: Combine multiple metrics and their deviation statuses to provide holistic interpretations (e.g., readiness, fatigue).
  * **File Structure**: `garmin_analyzer/interpretation/`
  * **Function/Class Definitions**:
      * `interpretation/interpretation_engine.py`:
        ```python
        from .rules.readiness_rules import check_high_recovery_readiness
        from .rules.fatigue_rules import check_accumulating_fatigue
        from ..common.data_models import DailyContext, InterpretationOutput # Pydantic models

        class InterpretationEngine:
            def __init__(self, db_conn):
                self.db_conn = db_conn # May need to fetch additional data for context

            def interpret_daily_status(self, user_id: int, date_str: str, daily_metrics_with_status: dict) -> InterpretationOutput:
                """
                Analyzes a collection of metrics (with their baseline status) to provide an overall interpretation.
                Args:
                    daily_metrics_with_status: A dict where keys are metric names and values are dicts
                                               containing 'value', 'baseline_mean', 'baseline_std_dev', 'status' (DeviationStatus).
                """
                interpretations = []
                # Example:
                # daily_metrics_with_status = {
                # 'RHR': {'value': 55, 'status': DeviationStatus.NORMAL, ...},
                # 'HRV': {'value': 60, 'status': DeviationStatus.SLIGHT_DEVIATION_WARNING, ...},
                # ...
                # }

                if check_high_recovery_readiness(daily_metrics_with_status):
                    interpretations.append("High Recovery / Readiness")

                if check_accumulating_fatigue(daily_metrics_with_status, user_id, date_str, self.db_conn):
                     interpretations.append("Accumulating Fatigue / Overtraining Risk")

                # Add more rule checks: PotentialIllness, PoorAdaptation, LifestyleImpacts

                return InterpretationOutput(summary_interpretations=interpretations, details={})
        ```
      * `interpretation/rules/*.py`: Contain specific rule functions.
          * Example: `readiness_rules.py`
            ```python
            from ..baselining.threshold_engine import DeviationStatus

            def check_high_recovery_readiness(metrics: dict) -> bool:
                hrv_ok = metrics.get('HRV', {}).get('status') in [DeviationStatus.NORMAL, DeviationStatus.OPTIMAL]
                rhr_ok = metrics.get('RHR', {}).get('status') in [DeviationStatus.NORMAL, DeviationStatus.OPTIMAL]
                # Assuming TST, SE are directly passed or their status
                good_sleep_qty = metrics.get('TST', {}).get('value', 0) >= 7 * 3600 # 7 hours
                good_sleep_quality = metrics.get('SE', {}).get('value', 0) >= 80 # 80%
                # TSB can be calculated and passed in metrics dict
                tsb_positive = metrics.get('TSB', {}).get('value', 0) > 0 # Or slightly negative is also fine
                body_battery_high = metrics.get('BodyBatteryMax', {}).get('value', 0) >= 80

                return hrv_ok and rhr_ok and good_sleep_qty and good_sleep_quality and tsb_positive and body_battery_high
            ```
  * **Dependencies**: `baselining` (for `DeviationStatus`), `core_metrics` (implicitly, via input `daily_metrics_with_status`).
  * **Error Handling**: Missing metrics in the input; rules should gracefully handle this.

#### E. Actionable Insight and Recommendation Generation Layer

  * **Purpose**: Convert interpretations into clear, specific, and actionable guidance.
  * **File Structure**: `garmin_analyzer/insights/`
  * **Function/Class Definitions**:
      * `insights/insight_generator.py`:
        ```python
        from ..common.data_models import InterpretationOutput, ActionableInsight
        import jinja2 # For templating
        from pathlib import Path

        class InsightGenerator:
            def __init__(self):
                template_loader = jinja2.FileSystemLoader(searchpath=Path(__file__).parent / "templates")
                self.template_env = jinja2.Environment(loader=template_loader)

            def generate_insights(self, interpretation: InterpretationOutput, daily_metrics_with_status: dict) -> List[ActionableInsight]:
                insights = []
                # Example for daily briefing
                if "High Recovery / Readiness" in interpretation.summary_interpretations:
                    template = self.template_env.get_template("daily_briefing_good_recovery.txt")
                    # Pass relevant metrics to the template
                    insight_text = template.render(
                        hrv_value=daily_metrics_with_status.get('HRV',{}).get('value'),
                        hrv_baseline_mean=daily_metrics_with_status.get('HRV',{}).get('baseline_mean'),
                        rhr_value=daily_metrics_with_status.get('RHR',{}).get('value'),
                        tst_hours=daily_metrics_with_status.get('TST',{}).get('value',0)/3600
                    )
                    insights.append(ActionableInsight(category="DailyReadiness", text=insight_text, priority=1))

                if "Accumulating Fatigue / Overtraining Risk" in interpretation.summary_interpretations:
                    template = self.template_env.get_template("training_guidance_fatigue.txt")
                    insight_text = template.render(
                        acwr_value=daily_metrics_with_status.get('ACWR',{}).get('value'),
                        # ... other metrics
                    )
                    insights.append(ActionableInsight(category="TrainingGuidance", text=insight_text, priority=2))

                # Add more insight generation based on other interpretations (SleepHygiene, StressManagement, LongTerm)
                return insights
        ```
  * **Dependencies**: `interpretation` (for `InterpretationOutput`), `common/data_models.py`. Text templates in `insights/templates/`.
  * **Error Handling**: Template not found, rendering errors.

#### F. Exploratory Correlation Analysis Layer

  * **Purpose**: Identify non-obvious, personalized relationships between data streams.
  * **File Structure**: `garmin_analyzer/correlation_analysis/`
  * **Function/Class Definitions**:
      * `correlation_analysis/correlation_engine.py`:
        ```python
        from ..common.db_utils import execute_query
        import pandas as pd

        class CorrelationEngine:
            def __init__(self, db_conn):
                self.db_conn = db_conn

            def lagged_cross_correlation(self, user_id: int, metric1_path: str, metric1_type: str,
                                         metric2_path: str, metric2_type: str, max_lag: int = 3):
                """
                Calculates lagged cross-correlation between two metrics.
                metric_path is the JSON path, metric_type is the data_type from garmin_raw_data.
                Example: metric1_path='$.avgStressLevel', metric1_type='stress'
                         metric2_path='$.hrvSummary.lastNightAvg', metric2_type='hrv' (for next day's HRV)
                """
                # This query would be complex: fetch time series for both metrics, align them, calculate correlations.
                # It might be easier to fetch raw series into pandas and use its correlation functions.
                query = f"""
                WITH Metric1 AS (
                    SELECT date, CAST(json_extract_string(json_data, '{metric1_path}') AS DOUBLE) as value
                    FROM garmin_raw_data
                    WHERE user_id = :user_id AND data_type = :metric1_type AND json_extract_string(json_data, '{metric1_path}') IS NOT NULL
                ),
                Metric2 AS (
                    SELECT date, CAST(json_extract_string(json_data, '{metric2_path}') AS DOUBLE) as value
                    FROM garmin_raw_data
                    WHERE user_id = :user_id AND data_type = :metric2_type AND json_extract_string(json_data, '{metric2_path}') IS NOT NULL
                )
                SELECT m1.date as date_m1, m1.value as value_m1, m2.date as date_m2, m2.value as value_m2
                FROM Metric1 m1
                JOIN Metric2 m2 ON m1.user_id = m2.user_id -- This join needs to be adapted for lags
                WHERE m1.user_id = :user_id
                ORDER BY m1.date;
                """
                # For actual correlation with lags, pandas is more straightforward:
                # 1. Fetch both time series.
                # 2. Align them by date.
                # 3. For each lag k from 0 to max_lag:
                #    df['metric2_lagged'] = df['metric2'].shift(-k) (for metric2 occurring k days after metric1)
                #    correlation = df['metric1'].corr(df['metric2_lagged'])
                # Placeholder for now, actual implementation likely uses pandas.
                return "Lagged correlation analysis to be implemented using pandas with data fetched from DuckDB."

            # Other methods: event_coincidence_analysis, simple_pattern_matching
        ```
  * **Dependencies**: `common/db_utils.py`, `pandas` (for complex correlations). SQL queries in `correlation_analysis/queries/`.
  * **Error Handling**: Insufficient data for correlation, non-numeric data.
  * **DuckDB Queries**: See Section 4 for basic correlation examples. Complex analysis might be Python-driven.

### 4\. DuckDB Query Implementations

All queries assume the `garmin_raw_data (user_id INTEGER, date DATE, data_type VARCHAR, json_data JSON, ...)` table structure.
Parameters like `:user_id`, `:target_date`, `:start_date`, `:end_date`, `:hr_max`, `:hr_rest`, `:gender` should be supplied by the Python layer.

#### 4.1 Core Metrics: Sleep Quality & Architecture

Common CTE for sleep data:

```sql
CREATE OR REPLACE MACRO get_sleep_data_for_day(user_id_param, date_param) AS TABLE
SELECT
    json_data
FROM garmin_raw_data
WHERE user_id = user_id_param AND date = date_param AND data_type = 'sleep';

CREATE OR REPLACE MACRO get_sleep_levels_for_day(user_id_param, date_param) AS TABLE
SELECT
    json_extract_path(json_data, '$.sleepLevels') AS sleep_levels_json
FROM garmin_raw_data
WHERE user_id = user_id_param AND date = date_param AND data_type = 'sleep';
```

  * **Total Sleep Time (TST)**

      * Description: Sum of deep, light, and REM sleep in seconds.
      * Source: `sleep` (from `dailySleepDTO`)
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        SELECT
            CAST(json_extract_string(s.json_data, '$.dailySleepDTO.deepSleepSeconds') AS INTEGER) +
            CAST(json_extract_string(s.json_data, '$.dailySleepDTO.lightSleepSeconds') AS INTEGER) +
            CAST(json_extract_string(s.json_data, '$.dailySleepDTO.remSleepSeconds') AS INTEGER) AS total_sleep_seconds
        FROM garmin_raw_data s
        WHERE s.user_id = :user_id AND s.date = :target_date AND s.data_type = 'sleep';
        ```
      * Output: `(total_sleep_seconds INTEGER)`
      * Perf: Fast, direct extraction.

  * **Sleep Efficiency (SE)**

      * Description: TST / (Time in Bed) \* 100.
      * Source: `sleep` (from `dailySleepDTO`)
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        WITH SleepData AS (
            SELECT
                CAST(json_extract_string(json_data, '$.dailySleepDTO.deepSleepSeconds') AS BIGINT) AS deep_s,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.lightSleepSeconds') AS BIGINT) AS light_s,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.remSleepSeconds') AS BIGINT) AS rem_s,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.sleepStartTimestampGMT') AS BIGINT) AS start_ts,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.sleepEndTimestampGMT') AS BIGINT) AS end_ts
            FROM garmin_raw_data
            WHERE user_id = :user_id AND date = :target_date AND data_type = 'sleep'
        )
        SELECT
            CASE
                WHEN (end_ts - start_ts) > 0 THEN
                    (deep_s + light_s + rem_s) * 100.0 / ((end_ts - start_ts)/1000) -- Timestamps are in ms
                ELSE NULL
            END AS sleep_efficiency_percentage
        FROM SleepData;
        ```
      * Output: `(sleep_efficiency_percentage DOUBLE)`
      * Perf: Fast. Handles division by zero.

  * **Wake After Sleep Onset (WASO)**

      * Description: Sum of 'AWAKE' durations from `sleepLevels` after first sleep epoch and before final awakening.
      * Source: `sleep` (from `sleepLevels`)
      * Input: `user_id`, `target_date`
      * SQL (Complex due to JSON array processing and logic; might need UDF or Python post-processing for full accuracy based on "first sleep epoch"):
        ```sql
        -- Simplified WASO: Sum of all 'AWAKE' durations from sleepLevels.
        -- Accurate WASO requires identifying first non-awake phase.
        -- This query sums all awake time during the sleep window as an approximation.
        SELECT
            SUM(CAST(level.durationInSeconds AS INTEGER)) AS waso_seconds
        FROM garmin_raw_data s,
             JSON_ARRAY_ELEMENTS(JSON_EXTRACT(s.json_data, '$.sleepLevels')) levels_json,
             UNNEST(levels_json) AS level_item(level_json),
             (SELECT level_json ->> 'activityLevel' AS activityLevel, level_json ->> 'durationInSeconds' AS durationInSeconds) AS level
        WHERE s.user_id = :user_id
          AND s.date = :target_date
          AND s.data_type = 'sleep'
          AND level.activityLevel = 'awake';
        -- For more precise WASO:
        -- 1. Find first 'asleep' (non-AWAKE) state.
        -- 2. Sum 'AWAKE' durations after that point until the last 'asleep' state.
        -- This typically requires procedural logic or more advanced SQL JSON processing.
        -- A UDF or Python processing of the sleepLevels array is recommended for accuracy.
        ```
      * Output: `(waso_seconds INTEGER)`
      * Perf: `JSON_ARRAY_ELEMENTS` can be costly on large arrays. The provided schema `sleepLevels` is an array of transitions. The actual structure of `sleepLevels` items (e.g., `{'activityLevel': 'AWAKE', 'startTimeGMT': ..., 'endTimeGMT': ...}` or `durationInSeconds`) is key. Assuming `durationInSeconds` per level is available. If using `startTimeGMT` and `endTimeGMT`, calculate duration.
      * *Refined based on provided `sleepLevels` structure being likely `[{type: 'DEEP', start:ts, end:ts}, ...]`. If it has `durationInSeconds` per segment, use that. Otherwise, `(end_ts - start_ts)/1000`.*

  * **Sleep Stage Percentages**

      * Description: % Deep, % REM, % Light of TST.
      * Source: `sleep` (from `dailySleepDTO`)
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        WITH SleepTimes AS (
            SELECT
                CAST(json_extract_string(json_data, '$.dailySleepDTO.deepSleepSeconds') AS DOUBLE) AS deep_s,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.lightSleepSeconds') AS DOUBLE) AS light_s,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.remSleepSeconds') AS DOUBLE) AS rem_s
            FROM garmin_raw_data
            WHERE user_id = :user_id AND date = :target_date AND data_type = 'sleep'
        ), TotalSleep AS (
            SELECT deep_s + light_s + rem_s AS tst_s FROM SleepTimes
        )
        SELECT
            CASE WHEN (SELECT tst_s FROM TotalSleep) > 0 THEN (SELECT deep_s FROM SleepTimes) * 100.0 / (SELECT tst_s FROM TotalSleep) ELSE NULL END AS deep_percentage,
            CASE WHEN (SELECT tst_s FROM TotalSleep) > 0 THEN (SELECT light_s FROM SleepTimes) * 100.0 / (SELECT tst_s FROM TotalSleep) ELSE NULL END AS light_percentage,
            CASE WHEN (SELECT tst_s FROM TotalSleep) > 0 THEN (SELECT rem_s FROM SleepTimes) * 100.0 / (SELECT tst_s FROM TotalSleep) ELSE NULL END AS rem_percentage
        FROM SleepTimes;
        ```
      * Output: `(deep_percentage DOUBLE, light_percentage DOUBLE, rem_percentage DOUBLE)`
      * Perf: Fast.

  * **Sleep Consistency (Std Dev of Bedtimes/Wake Times over 7 & 30 days)**

      * Description: Standard deviation of bedtimes and wake times.
      * Source: `sleep` (from `dailySleepDTO.sleepStartTimestampGMT`, `sleepEndTimestampGMT`)
      * Input: `user_id`, `target_date` (consistency is calculated up to this date)
      * SQL:
        ```sql
        WITH DailySleepTimes AS (
            SELECT
                date,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.sleepStartTimestampGMT') AS BIGINT) AS start_ts_gmt,
                CAST(json_extract_string(json_data, '$.dailySleepDTO.sleepEndTimestampGMT') AS BIGINT) AS end_ts_gmt
            FROM garmin_raw_data
            WHERE user_id = :user_id AND data_type = 'sleep'
              AND date BETWEEN (:target_date - INTERVAL '29 days') AND :target_date -- For 30-day window
        ),
        TimeParts AS (
            SELECT
                -- Convert GMT timestamp to time of day in seconds from midnight
                -- This requires date_trunc and epoch conversion careful with timezones if local time is preferred
                -- Assuming timestamps are consistent, using (timestamp % (24*60*60*1000)) / 1000 might give time of day in seconds
                -- For simplicity, using hour for STDEV. For minute-level, (start_ts_gmt / (1000*60)) % (24*60)
                EXTRACT(HOUR FROM epoch_ms(start_ts_gmt) + EXTRACT(MINUTE FROM epoch_ms(start_ts_gmt))/60.0) AS bedtime_hour_float,
                EXTRACT(HOUR FROM epoch_ms(end_ts_gmt) + EXTRACT(MINUTE FROM epoch_ms(end_ts_gmt))/60.0) AS waketime_hour_float,
                date
            FROM DailySleepTimes
        )
        SELECT
            (SELECT STDDEV_SAMP(bedtime_hour_float) FROM TimeParts WHERE date BETWEEN (:target_date - INTERVAL '6 days') AND :target_date) AS bedtime_stddev_7d,
            (SELECT STDDEV_SAMP(waketime_hour_float) FROM TimeParts WHERE date BETWEEN (:target_date - INTERVAL '6 days') AND :target_date) AS waketime_stddev_7d,
            (SELECT STDDEV_SAMP(bedtime_hour_float) FROM TimeParts) AS bedtime_stddev_30d, -- Full 30 day window from CTE
            (SELECT STDDEV_SAMP(waketime_hour_float) FROM TimeParts) AS waketime_stddev_30d
        ;
        -- Note: STDDEV_SAMP of time can be tricky. If bedtimes cross midnight, this simple hour extraction is problematic.
        -- A more robust way is to calculate minutes from a fixed point (e.g., previous day's noon) or normalize to shortest duration from median.
        -- For this example, using hour as a float is a simplification.
        ```
      * Output: `(bedtime_stddev_7d DOUBLE, waketime_stddev_7d DOUBLE, bedtime_stddev_30d DOUBLE, waketime_stddev_30d DOUBLE)`
      * Perf: Moderate, involves window functions or subqueries on a limited range. `epoch_ms` is a DuckDB function.

  * **Avg. Stress During Sleep**

      * Description: Average stress level during the sleep period.
      * Source: `daily_summary` (from `allDayStress.aggregatorList` type SLEEP\_STRESS) OR `sleep` (from `avgSleepStress` in Garmin Data Reference)
      * Input: `user_id`, `target_date`
      * SQL (using `sleep.avgSleepStress` as it's simpler if available):
        ```sql
        SELECT
            CAST(json_extract_string(json_data, '$.avgSleepStress') AS DOUBLE) AS avg_stress_during_sleep
        FROM garmin_raw_data
        WHERE user_id = :user_id AND date = :target_date AND data_type = 'sleep'
          AND json_extract_string(json_data, '$.avgSleepStress') IS NOT NULL;
        -- Alternative using daily_summary if sleep.avgSleepStress is not populated:
        -- This requires parsing aggregatorList which can be more complex.
        -- SELECT
        --     agg.value AS avg_stress_during_sleep
        -- FROM
        --     garmin_raw_data ds,
        --     JSON_ARRAY_ELEMENTS(JSON_EXTRACT(ds.json_data, '$.allDayStress.aggregatorList')) aggregators_json,
        --     UNNEST(aggregators_json) AS agg_item(agg_json),
        --     (SELECT agg_json ->> 'type' AS type, agg_json ->> 'value' AS value) AS agg
        -- WHERE
        --     ds.user_id = :user_id AND ds.date = :target_date AND ds.data_type = 'daily_summary'
        --     AND agg.type = 'SLEEP_STRESS';
        ```
      * Output: `(avg_stress_during_sleep DOUBLE)`
      * Perf: Fast if direct path exists. Parsing arrays is slower.

#### 4.2 Core Metrics: Recovery & Autonomic Nervous System (ANS) Status

  * **Resting Heart Rate (RHR)**

      * Description: Resting heart rate, typically from `dailySleepDTO`.
      * Source: `sleep` or `daily_summary`
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        SELECT
            COALESCE(
                CAST(json_extract_string(s.json_data, '$.dailySleepDTO.restingHeartRateInBeatsPerMinute') AS INTEGER),
                CAST(json_extract_string(ds.json_data, '$.restingHeartRate') AS INTEGER) -- from daily_summary (UDS)
            ) AS rhr
        FROM garmin_raw_data s
        LEFT JOIN garmin_raw_data ds ON s.user_id = ds.user_id AND s.date = ds.date AND ds.data_type = 'daily_summary'
        WHERE s.user_id = :user_id AND s.date = :target_date AND s.data_type = 'sleep';
        -- If sleep data might be missing, an outer join or union approach might be better
        ```
      * Output: `(rhr INTEGER)`
      * Perf: Fast.

  * **Nightly HRV (RMSSD-based)**

      * Description: Last night's average HRV.
      * Source: `hrv` (from `hrvSummary.lastNightAvg`)
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        SELECT
            CAST(json_extract_string(json_data, '$.hrvSummary.lastNightAvg') AS DOUBLE) AS nightly_hrv_rmssd
        FROM garmin_raw_data
        WHERE user_id = :user_id AND date = :target_date AND data_type = 'hrv'
          AND json_extract_string(json_data, '$.hrvSummary.lastNightAvg') IS NOT NULL;
        -- If raw R-R intervals are used from sleep.hrvData:
        -- This would be a very complex SQL query involving unnesting, lag, diff, square, sum, sqrt.
        -- Recommended to do via UDF or Python if raw R-R is the source.
        ```
      * Output: `(nightly_hrv_rmssd DOUBLE)`
      * Perf: Fast for summary. Very slow if from raw R-R.

  * **7-Day Rolling Average HRV (RMSSD)**

      * Description: Smoothed trend of nightly HRV.
      * Source: `hrv`
      * Input: `user_id`, `target_date` (average up to this date)
      * SQL:
        ```sql
        WITH DailyHRV AS (
            SELECT
                date,
                CAST(json_extract_string(json_data, '$.hrvSummary.lastNightAvg') AS DOUBLE) AS hrv_value
            FROM garmin_raw_data
            WHERE user_id = :user_id AND data_type = 'hrv'
              AND json_extract_string(json_data, '$.hrvSummary.lastNightAvg') IS NOT NULL
              AND date BETWEEN (:target_date - INTERVAL '6 days') AND :target_date
        )
        SELECT
            AVG(hrv_value) AS hrv_7d_rolling_avg
        FROM DailyHRV;
        -- For a value for each day in a range, use window function:
        -- SELECT date, AVG(hrv_value) OVER (ORDER BY date ASC ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS hrv_7d_rolling_avg
        -- FROM ... WHERE user_id = :user_id AND date BETWEEN :start_date AND :end_date ...
        ```
      * Output: `(hrv_7d_rolling_avg DOUBLE)`
      * Perf: Moderate due to range scan and aggregation.

  * **Body Battery Dynamics (Daily Max, Min, Net Change, Charge Rate during sleep)**

      * Description: Changes in Body Battery.
      * Source: `bodyBattery` or `stress` (from `bodyBatteryValuesArray`)
      * Input: `user_id`, `target_date`
      * SQL (Max, Min, Net Change):
        ```sql
        WITH BBValues AS (
            SELECT
                CAST(val.entry ->> 1 AS INTEGER) AS bb_value -- Assuming array of [timestamp, value]
            FROM garmin_raw_data bb_data,
                 JSON_ARRAY_ELEMENTS(JSON_EXTRACT(bb_data.json_data, '$.bodyBatteryValuesArray')) entries_json, -- Path from framework doc
                 UNNEST(entries_json) AS entry_item(entry_json),
                 (SELECT JSON_EXTRACT(entry_json, '$[0]') AS ts_val, JSON_EXTRACT(entry_json, '$[1]') AS bb_val_val) AS val
            WHERE bb_data.user_id = :user_id
              AND bb_data.date = :target_date -- Assumes bodyBatteryValuesArray is for the specific date
              AND (bb_data.data_type = 'bodyBattery' OR bb_data.data_type = 'stress') -- Check both possible sources
              AND JSON_TYPE(val.entry ->> 1) = 'NUMBER' -- Ensure value is a number
        ),
        OrderedBB AS (
            SELECT
                CAST(val.entry ->> 0 AS BIGINT) AS ts, -- Timestamp
                CAST(val.entry ->> 1 AS INTEGER) AS bb_value
            FROM garmin_raw_data bb_data,
                 JSON_ARRAY_ELEMENTS(JSON_EXTRACT(bb_data.json_data, '$.bodyBatteryValuesArray')) entries_json,
                 UNNEST(entries_json) AS entry_item(entry_json),
                 (SELECT JSON_EXTRACT(entry_json, '$[0]') AS ts, JSON_EXTRACT(entry_json, '$[1]') AS bb_value) AS val
            WHERE bb_data.user_id = :user_id
              AND bb_data.date = :target_date
              AND (bb_data.data_type = 'bodyBattery' OR bb_data.data_type = 'stress')
              AND JSON_TYPE(val.entry ->> 1) = 'NUMBER'
            ORDER BY ts ASC
        )
        SELECT
            MAX(bb_value) AS body_battery_max,
            MIN(bb_value) AS body_battery_min,
            (SELECT bb_value FROM OrderedBB ORDER BY ts DESC LIMIT 1) - (SELECT bb_value FROM OrderedBB ORDER BY ts ASC LIMIT 1) AS body_battery_net_change
        FROM BBValues;
        -- Charge Rate during sleep: Needs sleep window timestamps.
        -- 1. Get sleepStartTimestampGMT, sleepEndTimestampGMT from 'sleep' data_type.
        -- 2. Filter bodyBatteryValuesArray for timestamps within sleep window.
        -- 3. Calculate slope (change in BB / change in time). This is complex for pure SQL; Python/UDF recommended.
        -- Simplified: Net BB change during sleep window / sleep duration
        ```
      * Output: `(body_battery_max INTEGER, body_battery_min INTEGER, body_battery_net_change INTEGER)`
      * Perf: Potentially slow due to JSON array processing. `UNNEST` is better if DuckDB version supports it well for JSON. The provided `garmin_data_reference.md` shows `bodyBatteryValuesArray` inside `stress` data.
      * *Note*: `bodyBatteryValuesArray` might be directly under `bodyBattery` type as per framework or nested in `stress` type as per reference. Query adapted for this.

#### 4.3 Core Metrics: Training Load & Response

  * **Training Impulse (TRIMP - Banister's)**

      * Description: Calculates TRIMP for each activity. (Edwards' requires HR zones not easily parsed/standardized from all Garmin JSON).
      * Source: `activities_detailed` or `activity`, user profile for HRmax/HRrest.
      * Input: `user_id`, `target_date`, `hr_max`, `hr_rest`, `gender ('male'/'female')`
      * SQL (Calculates for all activities on a given day):
        ```sql
        WITH ActivityData AS (
            SELECT
                json_extract_string(act.json_data, '$.activityId') as activity_id,
                CAST(json_extract_string(act.json_data, '$.duration') AS DOUBLE) / 60.0 AS duration_min, -- Duration in minutes
                CAST(json_extract_string(act.json_data, '$.averageHR') AS DOUBLE) AS avg_hr
            FROM garmin_raw_data act
            WHERE act.user_id = :user_id AND act.date = :target_date
              AND (act.data_type = 'activities_detailed' OR act.data_type = 'activity') -- Assuming one activity per row if type is 'activity'
              AND json_extract_string(act.json_data, '$.averageHR') IS NOT NULL
              AND CAST(json_extract_string(act.json_data, '$.duration') AS DOUBLE) > 0
        ),
        HRRatio AS (
            SELECT
                activity_id,
                duration_min,
                avg_hr,
                CASE
                    WHEN (:hr_max - :hr_rest) > 0 THEN (avg_hr - :hr_rest) / (:hr_max - :hr_rest)
                    ELSE 0
                END AS delta_hr_ratio
            FROM ActivityData
            WHERE avg_hr IS NOT NULL AND avg_hr > :hr_rest -- Ensure avg_hr is sensible
        )
        SELECT
            activity_id,
            duration_min * delta_hr_ratio *
            (CASE WHEN :gender = 'male' THEN 0.64 * exp(1.92 * delta_hr_ratio)
                  WHEN :gender = 'female' THEN 0.86 * exp(1.67 * delta_hr_ratio)
                  ELSE 0.75 * exp(1.795 * delta_hr_ratio) -- Average/Unisex as fallback
             END) AS trimp_banister
        FROM HRRatio;
        -- Alternative using Garmin's Training Load (if available and preferred initially):
        -- SELECT json_extract_string(act.json_data, '$.trainingLoad') AS garmin_training_load ...
        ```
      * Output: `(activity_id VARCHAR, trimp_banister DOUBLE)` for each activity. Sum them for daily TRIMP.
      * Perf: Fast for a few activities per day. `exp()` is a standard math function.

  * **Daily Total TRIMP**

      * Description: Sum of TRIMP from all activities in a day.
      * SQL (building on previous query):
        ```sql
        WITH UserActivityTRIMP AS (
            -- ... (TRIMP calculation CTEs from above for a user over a date range :start_date, :end_date)
            -- Output of that would be (date, activity_id, trimp_banister)
            -- For this example, we assume daily TRIMP values are pre-calculated or obtained
            -- by summing the previous query's output per day.
            -- Let's create a placeholder CTE for daily TRIMP values.
            -- In a real scenario, you'd join the above activity TRIMP calculation with a date series.
            SELECT date, SUM(calculated_trimp) as daily_trimp
            FROM ( /* ... subquery to calculate TRIMP for each activity and its date ... */ )
            WHERE user_id = :user_id AND date BETWEEN :start_date AND :end_date
            GROUP BY date
        )
        SELECT date, daily_trimp FROM UserActivityTRIMP;
        ```
      * Output: `(date DATE, daily_trimp DOUBLE)`

  * **Acute Training Load (ATL - 7-day EWMA of TRIMP)** & **Chronic Training Load (CTL - 42-day EWMA of TRIMP)**

      * Description: Exponentially weighted moving averages of daily TRIMP.
      * Source: Daily TRIMP values.
      * Input: `user_id`, `target_date` (ATL/CTL up to this date)
      * SQL for EWMA (Approximation using weighted sum over N days, requires daily TRIMP values):
        ```sql
        -- This query calculates EWMA for a single target_date.
        -- To get a series, adapt it to run over a date range.
        -- Assumes a CTE 'DailyTotalTRIMP(date DATE, total_trimp DOUBLE)' is available for the user.
        -- For ATL (N=7, alpha = 2/(7+1) = 0.25)
        -- For CTL (N=42, alpha = 2/(42+1) = 0.0465116)
        CREATE OR REPLACE MACRO calculate_ewma(data_table, value_column, date_column, period, alpha_val) AS TABLE
        WITH WeightedValues AS (
            SELECT
                d.{{date_column}},
                d.{{value_column}},
                POWER(1.0 - alpha_val, ROW_NUMBER() OVER (ORDER BY d.{{date_column}} DESC) - 1) as weight_factor
            FROM {{data_table}} d
            WHERE d.{{date_column}} <= :target_date -- Up to the target date
              AND d.{{date_column}} >= :target_date - MAKE_INTERVAL(days => period -1) -- Look back 'period' days
        )
        SELECT
            :target_date as date,
            SUM(wv.{{value_column}} * wv.weight_factor * alpha_val) / SUM(wv.weight_factor * alpha_val) as ewma_value
            -- The denominator SUM(wv.weight_factor * alpha_val) normalizes weights for periods shorter than N (startup)
            -- A more standard EWMA recursive formula is better handled in Python or UDFs for true series.
        FROM WeightedValues wv;

        -- Example usage (conceptual, assumes DailyTotalTRIMP CTE is populated for the user):
        -- WITH DailyTotalTRIMP AS (SELECT date, SUM(trimp_banister) as total_trimp FROM UserActivityTRIMP GROUP BY date)
        -- SELECT ewma.* FROM calculate_ewma(DailyTotalTRIMP, 'total_trimp', 'date', 7, 0.25) ewma; -- For ATL
        -- SELECT ewma.* FROM calculate_ewma(DailyTotalTRIMP, 'total_trimp', 'date', 42, 2.0/43.0) ewma; -- For CTL
        ```
      * Output: `(date DATE, ewma_value DOUBLE)`
      * Perf: This simplified EWMA is okay for one date. For a series, a Python UDF or processing outside SQL is better for true EWMA. Window functions for true recursive EWMA are not standard.
      * *Note on EWMA:* True EWMA is $EWMA\_t = \\alpha \\cdot Y\_t + (1-\\alpha) \\cdot EWMA\_{t-1}$. This requires recursion. The provided SQL is an approximation for a fixed window. For production, a UDF or Python loop over sorted daily TRIMP values is more accurate.

  * **Training Stress Balance (TSB)**

      * Description: CTL - ATL.
      * SQL: Requires ATL and CTL values for the date.
        ```sql
        SELECT (:ctl_value - :atl_value) AS tsb; -- Assuming :ctl_value and :atl_value are inputs for the date
        -- Or join results from ATL and CTL calculations for a date range.
        ```
      * Output: `(tsb DOUBLE)`

  * **Acute:Chronic Workload Ratio (ACWR)**

      * Description: ATL / CTL or (7-day sum load / (28-day sum load / 4)). Using sum-based for simpler SQL.
      * Source: Daily TRIMP values.
      * SQL (Sum-based):
        ```sql
        WITH DailyUserTRIMP AS ( -- Assume this CTE provides date, total_trimp for the user
            SELECT date, SUM(trimp_value) as total_trimp FROM ... WHERE user_id = :user_id GROUP BY date
        ),
        Sum7Day AS (
            SELECT SUM(total_trimp) AS sum_7d
            FROM DailyUserTRIMP
            WHERE date BETWEEN (:target_date - INTERVAL '6 days') AND :target_date
        ),
        Sum28Day AS (
            SELECT SUM(total_trimp) AS sum_28d
            FROM DailyUserTRIMP
            WHERE date BETWEEN (:target_date - INTERVAL '27 days') AND :target_date
        )
        SELECT
            CASE
                WHEN (SELECT sum_28d FROM Sum28Day) > 0 THEN
                    (SELECT sum_7d FROM Sum7Day) / ((SELECT sum_28d FROM Sum28Day) / 4.0)
                ELSE NULL
            END AS acwr
        FROM Sum7Day, Sum28Day; -- Cross join to make values available.
        ```
      * Output: `(acwr DOUBLE)`
      * Perf: Moderate, involves sums over date ranges.

  * **Heart Rate Recovery (HRR - 1 min)**

      * Description: HR at end of exercise - HR 1 min post-exercise.
      * Source: `activities_detailed` (if granular HR available with timestamps post-activity). This is challenging with typical Garmin summary JSON.
      * SQL: *Highly dependent on detailed HR time series data for activities. If `activity_detailed` JSON contains an array of HR samples with timestamps like `[[timestamp, hr], [timestamp, hr], ...]` then it's possible.*
        ```sql
        -- Conceptual query if detailed HR samples are available within activity JSON:
        -- 1. Unnest HR samples for a specific activity.
        -- 2. Find HR at activity end (max timestamp or flagged end point).
        -- 3. Find HR approx 1 minute after that timestamp.
        -- This is typically NOT available in summary activity JSONs.
        -- If Garmin's "Recovery HR" metric is directly available in activity details, use that.
        -- SELECT json_extract_string(act.json_data, '$.recoveryHeartRateAt1Minute') AS hrr_1min ...
        -- LIKELY REQUIRES PYTHON PROCESSING OF DETAILED FIT FILE OR VERY GRANULAR JSON.
        ```
      * Output: `(hrr_1min INTEGER)`
      * Perf: N/A if data unavailable. If available and involves JSON array parsing, can be slow.

#### 4.4 Core Metrics: Long-Term Fitness & Cardiovascular Health

  * **VO₂ Max**

      * Description: VO₂ Max estimate.
      * Source: `daily_summary.vo2Max` or activity-specific.
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        SELECT
            CAST(json_extract_string(json_data, '$.vo2Max') AS DOUBLE) AS vo2_max -- Path from framework.
            -- Or from fitness_age data type if more suitable: json_extract_string(json_data, '$.components.vo2max.value')
        FROM garmin_raw_data
        WHERE user_id = :user_id AND date = :target_date AND data_type = 'daily_summary'; -- Or 'fitness_age'
        ```
      * Output: `(vo2_max DOUBLE)`
      * Perf: Fast.

  * **RHR Long-Term Trend (30/90-day rolling average)**

      * Description: Rolling average of daily RHR.
      * Input: `user_id`, `target_date`
      * SQL (for 30-day, adapt for 90):
        ```sql
        WITH DailyRHR AS (
            SELECT
                date,
                COALESCE(
                    CAST(json_extract_string(s.json_data, '$.dailySleepDTO.restingHeartRateInBeatsPerMinute') AS INTEGER),
                    CAST(json_extract_string(ds.json_data, '$.restingHeartRate') AS INTEGER)
                ) AS rhr
            FROM garmin_raw_data s
            LEFT JOIN garmin_raw_data ds ON s.user_id = ds.user_id AND s.date = ds.date AND ds.data_type = 'daily_summary'
            WHERE s.user_id = :user_id AND s.data_type = 'sleep'
              AND COALESCE(...) IS NOT NULL
              AND s.date BETWEEN (:target_date - INTERVAL '29 days') AND :target_date -- For 30 day avg up to target_date
        )
        SELECT AVG(rhr) AS rhr_30d_avg FROM DailyRHR;
        -- For series: AVG(rhr) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
        ```
      * Output: `(rhr_30d_avg DOUBLE)`
      * Perf: Moderate.

  * **HRV Long-Term Trend (Baseline HRV - 30/60-day rolling average)**

      * Similar to RHR trend, replace RHR with nightly HRV.
      * Input: `user_id`, `target_date`
      * SQL (for 60-day):
        ```sql
        WITH DailyHRV AS (
            SELECT
                date,
                CAST(json_extract_string(json_data, '$.hrvSummary.lastNightAvg') AS DOUBLE) AS hrv_value
            FROM garmin_raw_data
            WHERE user_id = :user_id AND data_type = 'hrv'
              AND json_extract_string(json_data, '$.hrvSummary.lastNightAvg') IS NOT NULL
              AND date BETWEEN (:target_date - INTERVAL '59 days') AND :target_date
        )
        SELECT AVG(hrv_value) AS hrv_60d_avg FROM DailyHRV;
        ```
      * Output: `(hrv_60d_avg DOUBLE)`
      * Perf: Moderate.

  * **Resting Respiration Rate**

      * Description: Average respiration rate during sleep.
      * Source: `daily_summary.avgRespirationRate` (during sleep) or `sleep` data (e.g., \`json\_data-\>\>'wellnessEpochRespirationDataDTOList' -\>\> 'avgRespiration')
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        SELECT
            COALESCE(
                CAST(json_extract_string(ds.json_data, '$.avgRespirationRate') AS DOUBLE), -- from daily_summary
                CAST(json_extract_string(s.json_data, '$.avgSleepRespirationValue') AS DOUBLE) -- path from GarminDailyData, likely from respiration data type
            ) AS resting_respiration_rate
        FROM garmin_raw_data ds -- daily_summary
        LEFT JOIN garmin_raw_data s ON ds.user_id = s.user_id AND ds.date = s.date AND s.data_type = 'respiration' -- Or 'sleep' if nested there
        WHERE ds.user_id = :user_id AND ds.date = :target_date AND ds.data_type = 'daily_summary';
        ```
      * Output: `(resting_respiration_rate DOUBLE)`
      * Perf: Fast.

  * **SpO₂ (Average Nightly)**

      * Description: Average SpO₂ during sleep.
      * Source: `daily_summary.spo2Avg` or `sleep` data (e.g. `wellnessSpO2SleepSummaryDTO.averageSPO2`)
      * Input: `user_id`, `target_date`
      * SQL:
        ```sql
        SELECT
            COALESCE(
                CAST(json_extract_string(ds.json_data, '$.spo2Avg') AS DOUBLE), -- From daily_summary (UDS in framework)
                CAST(json_extract_string(s.json_data, '$.wellnessSpO2SleepSummaryDTO.averageSPO2') AS DOUBLE), -- From sleep data, garmin_data_models.py
                CAST(json_extract_string(spo2_data.json_data, '$.averageSpO2') AS DOUBLE) -- From spo2 data type as per reference
            ) AS avg_nightly_spo2
        FROM garmin_raw_data ds -- daily_summary
        LEFT JOIN garmin_raw_data s ON ds.user_id = s.user_id AND ds.date = s.date AND s.data_type = 'sleep'
        LEFT JOIN garmin_raw_data spo2_data ON ds.user_id = spo2_data.user_id AND ds.date = spo2_data.date AND spo2_data.data_type = 'spo2'
        WHERE ds.user_id = :user_id AND ds.date = :target_date AND ds.data_type = 'daily_summary';
        ```
      * Output: `(avg_nightly_spo2 DOUBLE)`
      * Perf: Fast.

#### 4.5 Personalized Baselining and Thresholding Layer Queries

  * **Calculate Rolling Baselines (Mean and SD)**
      * Description: Calculate rolling mean and standard deviation for a metric over a defined window (e.g., 30 days).
      * Input: `user_id`, `metric_cte_name` (CTE providing `date`, `value`), `window_days`, `target_date`
      * SQL (Example for RHR, 30-day baseline):
        ```sql
        WITH MetricValues AS (
            SELECT
                date,
                CAST(json_extract_string(s.json_data, '$.dailySleepDTO.restingHeartRateInBeatsPerMinute') AS DOUBLE) AS value
            FROM garmin_raw_data s
            WHERE s.user_id = :user_id AND s.data_type = 'sleep'
              AND json_extract_string(s.json_data, '$.dailySleepDTO.restingHeartRateInBeatsPerMinute') IS NOT NULL
              AND s.date <= :target_date -- Consider data up to the target date
        )
        SELECT
            AVG(value) OVER (ORDER BY date ROWS BETWEEN (:window_days - 1) PRECEDING AND CURRENT ROW) AS rolling_mean,
            STDDEV_SAMP(value) OVER (ORDER BY date ROWS BETWEEN (:window_days - 1) PRECEDING AND CURRENT ROW) AS rolling_stddev,
            date
        FROM MetricValues
        WHERE date = :target_date; -- Get baseline for the specific target_date
        -- Or remove WHERE date = :target_date to get series of baselines
        ```
      * Output: `(rolling_mean DOUBLE, rolling_stddev DOUBLE, date DATE)`
      * Perf: Moderate, window functions over N rows.

#### 4.6 Exploratory Correlation Analysis Layer Queries

  * **Lagged Cross-Correlation (Simple Pearson Correlation for two metrics, one lagged)**
      * Description: Pearson correlation between metric A today and metric B N days ago/later.
      * Input: `user_id`, `metric1_cte` (date, value1), `metric2_cte` (date, value2), `lag_days INTEGER`
      * SQL (Metric B lagged by `lag_days` relative to Metric A):
        ```sql
        WITH MetricA AS ( -- SELECT date, value as value_a FROM ... WHERE user_id = :user_id
            SELECT date, CAST(json_extract_string(json_data, '$.avgStressLevel') AS DOUBLE) as value_a
            FROM garmin_raw_data WHERE user_id = :user_id AND data_type = 'stress' AND json_extract_string(json_data, '$.avgStressLevel') IS NOT NULL
        ),
        MetricB AS ( -- SELECT date, value as value_b FROM ... WHERE user_id = :user_id
            SELECT date, CAST(json_extract_string(json_data, '$.hrvSummary.lastNightAvg') AS DOUBLE) as value_b
            FROM garmin_raw_data WHERE user_id = :user_id AND data_type = 'hrv' AND json_extract_string(json_data, '$.hrvSummary.lastNightAvg') IS NOT NULL
        )
        SELECT
            CORR(m_a.value_a, m_b_lagged.value_b) AS pearson_correlation
        FROM MetricA m_a
        JOIN MetricB m_b_lagged ON m_a.date = (m_b_lagged.date - MAKE_INTERVAL(days => :lag_days)); -- e.g. lag_days = 1 means m_b is 1 day after m_a
                                                                                                   -- for m_b being 1 day BEFORE m_a: m_a.date = (m_b_lagged.date + MAKE_INTERVAL(days => :lag_days))
        -- Date range filter should be applied to MetricA and MetricB CTEs for performance.
        ```
      * Output: `(pearson_correlation DOUBLE)`
      * Perf: Depends on date range and underlying metric CTEs. `CORR` is an aggregate.

### 5\. Software Engineering Best Practices

  * **SOLID Principles**:
      * **SRP (Single Responsibility Principle)**: Each class/module in the file structure has a specific responsibility (e.g., `BaselineCalculator`, `InsightGenerator`). SQL queries calculate specific metrics.
      * **OCP (Open/Closed Principle)**: Layers are open for extension (new metrics, rules, insights) but closed for modification (interfaces between layers are stable). New rules can be added to the `interpretation/rules/` directory without changing `InterpretationEngine` core logic if it loads them dynamically or uses a registry.
      * **LSP (Liskov Substitution Principle)**: Not directly applicable with this structure but if using inheritance for rules/insights, subtypes must be substitutable.
      * **ISP (Interface Segregation Principle)**: Components interact through well-defined interfaces (function signatures, Pydantic models for data exchange).
      * **DIP (Dependency Inversion Principle)**: High-level modules (e.g., `InterpretationEngine`) depend on abstractions (e.g., generic rule structure), not concrete low-level modules. DuckDB connection is passed, promoting decoupling.
  * **Clean Architecture**:
      * Core business logic (metric calculation, interpretation rules) is independent of frameworks/UI.
      * Dependencies flow inwards: Infrastructure (DuckDB) -\> Application Logic (Python services) -\> Domain Logic (Metrics, Rules).
  * **Separation of Concerns**: Clearly demonstrated by the layered architecture and modular file structure. SQL for data crunching, Python for orchestration, logic, and I/O.
  * **Testability**:
      * Unit tests for Python functions (e.g., rule logic in `InterpretationEngine`, template rendering in `InsightGenerator`). Mock DuckDB connection or use in-memory DuckDB for testing queries with sample data.
      * Integration tests for layer interactions (e.g., full flow from raw data to insight for a scenario).
      * SQL queries can be tested independently with sample `garmin_raw_data`.
  * **Documentation Standards**:
      * Docstrings for all Python classes and functions (e.g., Google Style).
      * Comments in SQL queries explaining logic, especially for complex parts.
      * README files for each major component directory explaining its purpose.
      * Use `docs/` for overall architecture, API reference (if any part is exposed as an API).
      * Pydantic models for data structures also serve as documentation.

### 6\. Interface Definitions Between Components

  * **Data Acquisition -\> DuckDB**:
      * Input: Garmin API data.
      * Output: Rows in `garmin_raw_data` table (`(user_id, date, data_type, json_data, fetch_timestamp)`).
  * **DuckDB -\> Core Metric Calculation**:
      * Input: `user_id`, `date`/`date_range`, other params (`hr_max`, etc.).
      * Output: Pydantic models representing calculated metrics (e.g., `SleepMetricsOutput(tst: float, se: float, ...)`). Each function returns a specific model or a list of them.
  * **Core Metrics -\> Baselining Layer**:
      * Input: `user_id`, `date`, `metric_name`, `current_value` (from Core Metrics).
      * Output: `DeviationStatus` enum, dictionary with `{'mean': float, 'std_dev': float}` for the baseline.
  * **Baselining Layer + Core Metrics -\> Interpretation Engine**:
      * Input: `user_id`, `date`, `daily_metrics_with_status: Dict[str, Dict{'value': Any, 'status': DeviationStatus, ...}]`.
      * Output: `InterpretationOutput(summary_interpretations: List[str], details: Dict)`.
  * **Interpretation Engine -\> Insight Generation Layer**:
      * Input: `InterpretationOutput`, `daily_metrics_with_status` (for context in templates).
      * Output: `List[ActionableInsight(category: str, text: str, priority: int)]`.
  * **DuckDB -\> Correlation Analysis Layer**:
      * Input: `user_id`, metric specifications, lag parameters.
      * Output: Correlation coefficients, data for plotting, or textual findings.

### 7\. Implementation Phases with Priorities

**Phase 1: Foundation & Core Sleep/Recovery Metrics**

1.  **Setup & Data Acquisition**:
      * Solidify `GarminDataAnalysisService` and `garmin_raw_data` table structure.
      * Implement robust data fetching and storage for `sleep`, `hrv`, `daily_summary` (for RHR, stress), `bodyBattery`.
      * Implement `common/db_utils.py` and initial `common/data_models.py`.
2.  **Core Metrics - Sleep & Recovery**:
      * Implement SQL and Python for: TST, SE, WASO (simplified if needed first), Sleep Stage %, Avg. Stress During Sleep.
      * RHR, Nightly HRV.
      * Body Battery Dynamics (Min, Max, Net Change - defer charge rate during sleep if too complex initially).
3.  **Baselining - Basic**:
      * Implement `BaselineCalculator` and `ThresholdEngine` for RHR and HRV.
      * Focus on 30-day rolling averages and SD.
4.  **Interpretation & Insights - Basic Daily Readiness**:
      * `InterpretationEngine`: Basic rules for "Good Recovery" vs. "Potential Stress/Poor Recovery" based on RHR/HRV deviations from baseline and sleep quality.
      * `InsightGenerator`: Simple daily briefing based on the above.
5.  **Testing**: Unit tests for all implemented metrics and logic.

**Phase 2: Training Load & Expanded Insights**

1.  **Core Metrics - Training Load**:
      * Implement data fetching for `activities_detailed` / `activity`.
      * Implement TRIMP (Banister's or Garmin's load initially).
      * Implement ATL, CTL (start with sum-based ACWR, then EWMA approximations or Python for EWMA). TSB, ACWR.
      * HRR (if data allows, else mark as low priority/future).
2.  **Core Metrics - Long-Term Fitness**:
      * VO₂ Max, Resting Respiration, SpO₂.
      * Long-term RHR/HRV trends (can reuse/extend baseline queries).
3.  **Baselining - Expanded**:
      * Add baselining for sleep metrics (TST, SE), Body Battery.
4.  **Interpretation & Insights - Training Focused**:
      * `InterpretationEngine`: Rules for "Accumulating Fatigue/Overtraining", "Poor Adaptation", impact of lifestyle.
      * `InsightGenerator`: Training guidance, sleep hygiene nudges, stress management prompts.
5.  **Testing**: Expand tests.

**Phase 3: Advanced Analysis & Refinements**

1.  **Refine EWMA for ATL/CTL**: Implement robust EWMA (Python UDF or iterative SQL if feasible).
2.  **Refine WASO**: Implement more accurate WASO if Phase 1 was simplified.
3.  **Exploratory Correlation Analysis**:
      * Implement `CorrelationEngine` for lagged cross-correlations (e.g., Stress vs. next-day HRV).
      * Start with a few predefined correlations.
4.  **Interpretation & Insights - Advanced**:
      * Long-term trend observations.
      * Insights from correlation analysis (e.g., "X impacts your Y").
5.  **Full System Integration & UI/Output**:
      * Ensure `main.py` orchestrates all layers.
      * Develop user-facing output format (e.g., daily/weekly report generation).
6.  **Performance Optimization**: Review and optimize DuckDB queries, especially for large datasets.

**Phase 4: Iterative Refinement & ML (Future)**

1.  **User Feedback & Iteration**: Collect feedback and refine metrics, rules, and insights.
2.  **Machine Learning**: Explore ML for more nuanced interpretations or predictive insights (as mentioned in framework).
3.  **Contextualization**: Deeper contextualization of thresholds (e.g., training phase).

This plan provides a detailed roadmap. The AI coding assistant should be able to take sections of this plan, particularly the file structures, class/function definitions, and SQL queries, to generate code. Emphasis should be on implementing the DuckDB queries accurately based on the JSON paths from `garmin_data_reference.md` and framework document.