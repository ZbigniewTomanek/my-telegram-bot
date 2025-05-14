"""
Unit tests for recovery metrics calculation.

These tests verify that the recovery and ANS metrics are calculated correctly using sample Garmin data.
"""

import datetime as dt
import json
from pathlib import Path
from unittest.mock import AsyncMock

import duckdb
import pytest

from telegram_bot.service.garmin_analysis.common.constants import DataTypes
from telegram_bot.service.garmin_analysis.core_metrics.recovery_metrics import RecoveryMetricsCalculator


class TestRecoveryMetrics:
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
        """Populate the database with sample data."""
        # Use May 1st, 2025 data
        date_key = "2025-05-01"
        user_id = 12345  # Test user ID

        if date_key in sample_data["data"]:
            daily_data = sample_data["data"][date_key]
            date_obj = dt.date.fromisoformat(date_key)

            # Store different data types for recovery metrics
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

            # Add data for previous days to test 7-day averages
            for i in range(1, 7):
                prev_date = date_obj - dt.timedelta(days=i)

                # Copy current HRV data for previous days (for testing)
                if "hrv" in daily_data:
                    hrv_data = daily_data["hrv"]
                    db_connection.execute(
                        """
                        INSERT INTO garmin_raw_data
                        (user_id, date, data_type, json_data, fetch_timestamp)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (user_id, prev_date, DataTypes.HRV, json.dumps(hrv_data), dt.datetime.now()),
                    )

        return user_id, date_key

    @pytest.fixture
    def recovery_metrics_calculator(self, db_connection):
        """Create a RecoveryMetricsCalculator instance."""
        return RecoveryMetricsCalculator(db_connection)

    def test_recovery_metrics_calculator_initialization(self, recovery_metrics_calculator):
        """Test that the calculator initializes properly."""
        assert recovery_metrics_calculator is not None
        assert hasattr(recovery_metrics_calculator, "conn")
        assert hasattr(recovery_metrics_calculator, "queries")

    @pytest.mark.asyncio
    async def test_calculate_recovery_metrics(self, recovery_metrics_calculator, populate_db):
        """Test calculation of recovery metrics."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func to always return True
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate recovery metrics
        metrics = await recovery_metrics_calculator.calculate_recovery_metrics(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify the metrics
        assert metrics is not None
        assert metrics.date == date

        # Check specific recovery metrics
        if metrics.resting_heart_rate is not None:
            assert isinstance(metrics.resting_heart_rate, int)
            assert 30 <= metrics.resting_heart_rate <= 100  # Normal resting HR range

        if metrics.hrv_rmssd is not None:
            assert isinstance(metrics.hrv_rmssd, float)
            assert 10 <= metrics.hrv_rmssd <= 150  # Normal HRV range

        if metrics.body_battery_max is not None:
            assert isinstance(metrics.body_battery_max, int)
            assert 0 <= metrics.body_battery_max <= 100  # Body Battery range

        if metrics.avg_stress_level is not None:
            assert isinstance(metrics.avg_stress_level, float)
            assert 0 <= metrics.avg_stress_level <= 100  # Stress level range

    @pytest.mark.asyncio
    async def test_get_resting_heart_rate(self, recovery_metrics_calculator, populate_db):
        """Test getting resting heart rate."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Get resting heart rate
        rhr = await recovery_metrics_calculator.get_resting_heart_rate(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify resting heart rate if available
        if rhr is not None:
            assert isinstance(rhr, int)
            assert 30 <= rhr <= 100  # Normal resting HR range

    @pytest.mark.asyncio
    async def test_get_hrv(self, recovery_metrics_calculator, populate_db):
        """Test getting HRV values."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Get HRV values
        hrv, hrv_7day_avg = await recovery_metrics_calculator.get_hrv(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify HRV values if available
        if hrv is not None:
            assert isinstance(hrv, float)
            assert 10 <= hrv <= 150  # Normal HRV range

        if hrv_7day_avg is not None:
            assert isinstance(hrv_7day_avg, float)
            assert 10 <= hrv_7day_avg <= 150  # Normal HRV range

            # 7-day average should be close to the daily value in our test case
            # since we cloned the same HRV data for previous days
            if hrv is not None:
                assert abs(hrv - hrv_7day_avg) < 10

    @pytest.mark.asyncio
    async def test_get_body_battery(self, recovery_metrics_calculator, populate_db):
        """Test getting Body Battery metrics."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Get Body Battery metrics
        bb_metrics = await recovery_metrics_calculator.get_body_battery(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify Body Battery metrics if available
        if bb_metrics is not None:
            assert isinstance(bb_metrics, dict)

            # Check expected keys
            expected_keys = ["max", "min", "charged", "drained"]
            for key in bb_metrics:
                assert key in expected_keys

            # Check ranges
            for key, value in bb_metrics.items():
                if value is not None:
                    assert 0 <= value <= 100  # Body Battery range is 0-100

            # Check that max >= min
            if (
                "max" in bb_metrics
                and "min" in bb_metrics
                and bb_metrics["max"] is not None
                and bb_metrics["min"] is not None
            ):
                assert bb_metrics["max"] >= bb_metrics["min"]

    @pytest.mark.asyncio
    async def test_get_stress_level(self, recovery_metrics_calculator, populate_db):
        """Test getting stress level."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Get stress level
        stress = await recovery_metrics_calculator.get_stress_level(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify stress level if available
        if stress is not None:
            assert isinstance(stress, float)
            assert 0 <= stress <= 100  # Stress level range

    @pytest.mark.asyncio
    async def test_no_data_available(self, recovery_metrics_calculator, db_connection):
        """Test behavior when no data is available."""
        user_id = 99999  # Non-existent user
        date = dt.date.fromisoformat("2025-05-02")

        # Mock ensure_data_available_func to return False (no data)
        mock_ensure_data = AsyncMock(return_value=False)

        # Calculate recovery metrics with no data
        metrics = await recovery_metrics_calculator.calculate_recovery_metrics(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Should return None when no data is available
        assert metrics is None

    @pytest.mark.asyncio
    async def test_calculate_recovery_metrics_range(self, recovery_metrics_calculator, populate_db):
        """Test calculation of recovery metrics for a date range."""
        user_id, date_str = populate_db
        start_date = dt.date.fromisoformat(date_str)
        end_date = start_date + dt.timedelta(days=1)  # Just one day for test

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate recovery metrics for range
        metrics_range = await recovery_metrics_calculator.calculate_recovery_metrics_range(
            user_id, start_date, end_date, ensure_data_available_func=mock_ensure_data
        )

        # Should return a dictionary with dates as keys
        assert isinstance(metrics_range, dict)

        # Should have at least one date (we populated May 1st)
        assert len(metrics_range) >= 1

        # The key should be a date object and value should be RecoveryMetrics
        for date_key, metrics in metrics_range.items():
            assert isinstance(date_key, dt.date)
            assert hasattr(metrics, "date")
            assert hasattr(metrics, "resting_heart_rate")
