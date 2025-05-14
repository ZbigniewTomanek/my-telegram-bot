"""
Unit tests for the baseline calculator.

These tests verify that the baseline calculations work correctly and can be
compared against current metrics to provide meaningful status.
"""

import datetime as dt
import json
from pathlib import Path
from unittest.mock import AsyncMock

import duckdb
import pytest

from telegram_bot.service.garmin_analysis.baselining.baseline_calculator import BaselineCalculator
from telegram_bot.service.garmin_analysis.common.constants import BaselineThresholds, DataTypes
from telegram_bot.service.garmin_analysis.common.data_models import BaselineData, BaselineStatus, MetricWithBaseline
from telegram_bot.service.garmin_analysis.core_metrics.recovery_metrics import RecoveryMetricsCalculator
from telegram_bot.service.garmin_analysis.core_metrics.sleep_metrics import SleepMetricsCalculator


class TestBaselineCalculator:
    @pytest.fixture
    def sample_data_path(self):
        """Path to sample Garmin data file."""
        return Path(__file__).parent.parent.parent / "data/garmin_data/sample_raw_garmin_data.json"

    @pytest.fixture
    def sample_data(self, sample_data_path):
        """Load sample Garmin data."""
        with open(sample_data_path, "r") as f:
            return json.load(f)

    @pytest.fixture
    def db_connection(self):
        """Create an in-memory DuckDB connection for testing."""
        conn = duckdb.connect(":memory:")

        # Create the raw data table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_raw_data (
                user_id INTEGER,
                date DATE,
                data_type VARCHAR,
                json_data JSON,
                fetch_timestamp TIMESTAMP,
                PRIMARY KEY (user_id, date, data_type)
            )
        """
        )

        # Load JSON extension
        conn.execute("LOAD json")

        yield conn

        # Clean up
        conn.close()

    @pytest.fixture
    def populate_db(self, db_connection, sample_data):
        """Populate the database with sample data including multiple dates."""
        user_id = 12345  # Test user ID

        # Use multiple dates from our sample data if available
        available_dates = []
        for date_key in sample_data["data"].keys():
            try:
                date_obj = dt.date.fromisoformat(date_key)
                available_dates.append(date_key)
            except ValueError:
                continue

        if not available_dates:
            pytest.skip("No valid dates found in sample data")

        # Store data for available dates
        for date_key in available_dates:
            daily_data = sample_data["data"][date_key]
            date_obj = dt.date.fromisoformat(date_key)

            # Store different data types
            data_types_to_store = {
                "sleep": DataTypes.SLEEP,
                "hrv": DataTypes.HRV,
                "stress": DataTypes.STRESS,
                "body_battery": DataTypes.BODY_BATTERY,
                "resting_heart_rate": DataTypes.RESTING_HEART_RATE,
            }

            for key, data_type in data_types_to_store.items():
                if key in daily_data:
                    json_data = json.dumps(daily_data[key])

                    db_connection.execute(
                        """
                        INSERT INTO garmin_raw_data
                        (user_id, date, data_type, json_data, fetch_timestamp)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (user_id, date_obj, data_type, json_data, dt.datetime.now()),
                    )

            # Add historical data for testing baselines
            for i in range(1, 31):  # Add 30 days of historical data
                historical_date = date_obj - dt.timedelta(days=i)

                # Copy current data to historical dates (for testing)
                for key, data_type in data_types_to_store.items():
                    if key in daily_data:
                        json_data = json.dumps(daily_data[key])

                        # Try to insert but ignore conflicts
                        db_connection.execute(
                            """
                            INSERT OR IGNORE INTO garmin_raw_data
                            (user_id, date, data_type, json_data, fetch_timestamp)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (user_id, historical_date, data_type, json_data, dt.datetime.now()),
                        )

        return user_id, available_dates[0]  # Return user_id and first date

    @pytest.fixture
    def sleep_calculator(self, db_connection):
        """Create a SleepMetricsCalculator instance."""
        return SleepMetricsCalculator(db_connection)

    @pytest.fixture
    def recovery_calculator(self, db_connection):
        """Create a RecoveryMetricsCalculator instance."""
        return RecoveryMetricsCalculator(db_connection)

    @pytest.fixture
    def baseline_calculator(self, db_connection, sleep_calculator, recovery_calculator):
        """Create a BaselineCalculator instance."""
        return BaselineCalculator(
            db_connection, sleep_calculator=sleep_calculator, recovery_calculator=recovery_calculator
        )

    @pytest.mark.asyncio
    async def test_baseline_calculator_initialization(self, baseline_calculator):
        """Test that the baseline calculator initializes properly."""
        assert baseline_calculator is not None
        assert hasattr(baseline_calculator, "conn")
        assert hasattr(baseline_calculator, "sleep_calculator")
        assert hasattr(baseline_calculator, "recovery_calculator")
        assert hasattr(baseline_calculator, "default_lookback_days")

    @pytest.mark.asyncio
    async def test_calculate_sleep_baselines(self, baseline_calculator, populate_db):
        """Test calculation of sleep baselines."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate sleep baselines
        baselines = await baseline_calculator.calculate_sleep_baselines(
            user_id, date, lookback_days=30, ensure_data_available_func=mock_ensure_data
        )

        # Verify baselines
        assert isinstance(baselines, dict)

        # Data might not be sufficient for baselines in the test database
        if len(baselines) > 0:
            # Check structure of a baseline
            for metric, baseline in baselines.items():
                assert isinstance(baseline, BaselineData)
                assert hasattr(baseline, "mean")
                assert hasattr(baseline, "std_dev")
                assert hasattr(baseline, "lookback_days")

                # Check validity of statistics
                assert baseline.mean is not None
                assert baseline.std_dev > 0
                assert baseline.lookback_days == 30

    @pytest.mark.asyncio
    async def test_calculate_recovery_baselines(self, baseline_calculator, populate_db):
        """Test calculation of recovery baselines."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate recovery baselines
        baselines = await baseline_calculator.calculate_recovery_baselines(
            user_id, date, lookback_days=30, ensure_data_available_func=mock_ensure_data
        )

        # Verify baselines
        assert isinstance(baselines, dict)

        # Check structure of a baseline
        for metric, baseline in baselines.items():
            assert isinstance(baseline, BaselineData)
            assert hasattr(baseline, "mean")
            assert hasattr(baseline, "std_dev")
            assert hasattr(baseline, "lookback_days")

            # Check validity of statistics
            assert baseline.mean is not None
            assert baseline.std_dev > 0

    def test_calculate_metric_status(self, baseline_calculator):
        """Test calculation of metric status based on baselines."""
        # Create test baseline
        baseline = BaselineData(mean=60, std_dev=5, lookback_days=30)

        # Test lower is better case (e.g., RHR)
        # Optimal case - significantly better than baseline
        z_score, status = baseline_calculator.calculate_metric_status(50, baseline, lower_is_better=True)
        assert z_score < 0  # Lower than mean
        assert status == BaselineStatus.OPTIMAL

        # Normal case - close to baseline
        z_score, status = baseline_calculator.calculate_metric_status(63, baseline, lower_is_better=True)
        assert z_score > 0 and z_score < 1  # Higher than mean but within normal range
        assert status == BaselineStatus.NORMAL

        # Slight deviation case
        z_score, status = baseline_calculator.calculate_metric_status(66, baseline, lower_is_better=True)
        assert z_score > BaselineThresholds.NORMAL_UPPER
        assert z_score < BaselineThresholds.SLIGHT_DEVIATION_UPPER  # Between 0.75 and 1.5
        assert status == BaselineStatus.SLIGHT_DEVIATION

        # Concerning case
        z_score, status = baseline_calculator.calculate_metric_status(75, baseline, lower_is_better=True)
        assert z_score > BaselineThresholds.SLIGHT_DEVIATION_UPPER
        assert status == BaselineStatus.CONCERNING

        # Test higher is better case (e.g., HRV)
        baseline = BaselineData(mean=50, std_dev=10, lookback_days=30)

        # Optimal case - significantly better than baseline
        z_score, status = baseline_calculator.calculate_metric_status(65, baseline, lower_is_better=False)
        assert z_score > 0  # Higher than mean
        assert status == BaselineStatus.OPTIMAL

        # Normal case - close to baseline
        z_score, status = baseline_calculator.calculate_metric_status(45, baseline, lower_is_better=False)
        assert z_score < 0 and z_score > -1  # Lower than mean but within normal range
        assert status == BaselineStatus.NORMAL

        # Slight deviation case
        z_score, status = baseline_calculator.calculate_metric_status(35, baseline, lower_is_better=False)
        assert z_score < BaselineThresholds.NORMAL_LOWER
        assert status == BaselineStatus.SLIGHT_DEVIATION

        # Concerning case
        z_score, status = baseline_calculator.calculate_metric_status(25, baseline, lower_is_better=False)
        assert z_score < BaselineThresholds.SLIGHT_DEVIATION_LOWER
        assert status == BaselineStatus.CONCERNING

    def test_create_metric_with_baseline(self, baseline_calculator):
        """Test creation of MetricWithBaseline object."""
        # Create test baseline
        baseline = BaselineData(mean=100, std_dev=10, lookback_days=30)

        # Test with baseline
        metric = baseline_calculator.create_metric_with_baseline(120, baseline, lower_is_better=False)
        assert isinstance(metric, MetricWithBaseline)
        assert metric.value == 120
        assert metric.baseline_mean == 100
        assert metric.baseline_std_dev == 10
        assert metric.z_score == 2.0  # (120 - 100) / 10
        assert metric.status == BaselineStatus.OPTIMAL  # Higher is better and z_score > 0.75

        # Test without baseline
        metric = baseline_calculator.create_metric_with_baseline(120, None, lower_is_better=False)
        assert isinstance(metric, MetricWithBaseline)
        assert metric.value == 120
        assert metric.baseline_mean is None
        assert metric.baseline_std_dev is None
        assert metric.z_score is None
        assert metric.status == BaselineStatus.NO_BASELINE

        # Test with None value
        metric = baseline_calculator.create_metric_with_baseline(None, baseline, lower_is_better=False)
        assert isinstance(metric, MetricWithBaseline)
        assert metric.value == 0.0  # None converted to 0
        assert metric.status == BaselineStatus.NO_BASELINE

    @pytest.mark.asyncio
    async def test_calculate_sleep_metrics_with_baselines(self, baseline_calculator, populate_db):
        """Test calculation of sleep metrics with baselines."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate sleep metrics with baselines
        metrics_with_baselines = await baseline_calculator.calculate_sleep_metrics_with_baselines(
            user_id, date, lookback_days=30, ensure_data_available_func=mock_ensure_data
        )

        # Verify results
        assert metrics_with_baselines is not None
        assert metrics_with_baselines.date == date

        # Check total sleep time
        assert isinstance(metrics_with_baselines.total_sleep_time, MetricWithBaseline)
        assert metrics_with_baselines.total_sleep_time.value is not None

        # Check sleep efficiency
        assert isinstance(metrics_with_baselines.sleep_efficiency, MetricWithBaseline)
        assert metrics_with_baselines.sleep_efficiency.value is not None

    @pytest.mark.asyncio
    async def test_calculate_recovery_metrics_with_baselines(self, baseline_calculator, populate_db):
        """Test calculation of recovery metrics with baselines."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate recovery metrics with baselines
        metrics_with_baselines = await baseline_calculator.calculate_recovery_metrics_with_baselines(
            user_id, date, lookback_days=30, ensure_data_available_func=mock_ensure_data
        )

        # Verify results
        assert metrics_with_baselines is not None
        assert metrics_with_baselines.date == date

        # Check resting heart rate
        assert isinstance(metrics_with_baselines.resting_heart_rate, MetricWithBaseline)

        # Other metrics might be None depending on the test data
        if metrics_with_baselines.hrv_rmssd is not None:
            assert isinstance(metrics_with_baselines.hrv_rmssd, MetricWithBaseline)

        if metrics_with_baselines.body_battery_max is not None:
            assert isinstance(metrics_with_baselines.body_battery_max, MetricWithBaseline)

        if metrics_with_baselines.avg_stress_level is not None:
            assert isinstance(metrics_with_baselines.avg_stress_level, MetricWithBaseline)

    @pytest.mark.asyncio
    async def test_calculate_baselines_for_date_range(self, baseline_calculator, populate_db):
        """Test calculation of baselines for a date range."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)
        start_date = date - dt.timedelta(days=3)
        end_date = date

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate baselines for date range
        baselines = await baseline_calculator.calculate_baselines_for_date_range(
            user_id,
            start_date,
            end_date,
            lookback_days=30,
            ensure_data_available_func=mock_ensure_data,
            metrics_type="both",
        )

        # Verify results
        assert isinstance(baselines, dict)
        assert "sleep" in baselines
        assert "recovery" in baselines

        # Check sleep baselines for each date
        for date_key, metrics in baselines["sleep"].items():
            assert isinstance(date_key, dt.date)
            assert start_date <= date_key <= end_date

            if metrics:  # If we have baselines for this date
                for metric, baseline in metrics.items():
                    assert isinstance(baseline, BaselineData)

        # Check recovery baselines for each date
        for date_key, metrics in baselines["recovery"].items():
            assert isinstance(date_key, dt.date)
            assert start_date <= date_key <= end_date

            if metrics:  # If we have baselines for this date
                for metric, baseline in metrics.items():
                    assert isinstance(baseline, BaselineData)

    def test_save_and_load_baselines(self, baseline_calculator, tmp_path):
        """Test saving and loading baselines to/from a file."""
        # Create a temporary file path
        file_path = tmp_path / "test_baselines.json"

        # Create test baselines
        baselines = {
            "sleep": {
                dt.date(2025, 5, 1): {
                    "total_sleep_seconds": BaselineData(mean=28800, std_dev=1800, lookback_days=30),
                    "sleep_efficiency_pct": BaselineData(mean=85, std_dev=5, lookback_days=30),
                }
            },
            "recovery": {
                dt.date(2025, 5, 1): {
                    "resting_heart_rate": BaselineData(mean=60, std_dev=5, lookback_days=30),
                    "hrv_rmssd": BaselineData(mean=40, std_dev=10, lookback_days=90),
                }
            },
        }

        # Save baselines to file
        result = baseline_calculator.save_baselines_to_file(baselines, file_path)
        assert result is True
        assert file_path.exists()

        # Load baselines from file
        loaded_baselines = baseline_calculator.load_baselines_from_file(file_path)

        # Verify loaded baselines
        assert isinstance(loaded_baselines, dict)
        assert "sleep" in loaded_baselines
        assert "recovery" in loaded_baselines

        # Check that the structure matches
        assert dt.date(2025, 5, 1) in loaded_baselines["sleep"]
        assert "total_sleep_seconds" in loaded_baselines["sleep"][dt.date(2025, 5, 1)]
        assert "sleep_efficiency_pct" in loaded_baselines["sleep"][dt.date(2025, 5, 1)]

        assert dt.date(2025, 5, 1) in loaded_baselines["recovery"]
        assert "resting_heart_rate" in loaded_baselines["recovery"][dt.date(2025, 5, 1)]
        assert "hrv_rmssd" in loaded_baselines["recovery"][dt.date(2025, 5, 1)]

        # Check that values match
        sleep_baseline = loaded_baselines["sleep"][dt.date(2025, 5, 1)]["total_sleep_seconds"]
        assert sleep_baseline.mean == 28800
        assert sleep_baseline.std_dev == 1800
        assert sleep_baseline.lookback_days == 30

        recovery_baseline = loaded_baselines["recovery"][dt.date(2025, 5, 1)]["hrv_rmssd"]
        assert recovery_baseline.mean == 40
        assert recovery_baseline.std_dev == 10
        assert recovery_baseline.lookback_days == 90
