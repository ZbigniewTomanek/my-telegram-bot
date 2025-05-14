"""
Unit tests for sleep metrics calculation.

These tests verify that the sleep metrics are calculated correctly using sample Garmin data.
"""

import datetime as dt
import json
from pathlib import Path
from unittest.mock import AsyncMock

import duckdb
import pytest

from telegram_bot.service.garmin_analysis.common.constants import DataTypes
from telegram_bot.service.garmin_analysis.core_metrics.sleep_metrics import SleepMetricsCalculator


class TestSleepMetrics:
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
        # Get sleep data for May 1st, 2025
        date_key = "2025-05-01"
        user_id = 12345  # Test user ID

        if date_key in sample_data["data"]:
            daily_data = sample_data["data"][date_key]

            # Store sleep data if available
            if "sleep" in daily_data:
                sleep_data = daily_data["sleep"]
                json_data = json.dumps(sleep_data)

                db_connection.execute(
                    """
                    INSERT INTO garmin_raw_data
                    (user_id, date, data_type, json_data, fetch_timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, dt.date.fromisoformat(date_key), DataTypes.SLEEP, json_data, dt.datetime.now()),
                )

        return user_id, date_key

    @pytest.fixture
    def sleep_metrics_calculator(self, db_connection):
        """Create a SleepMetricsCalculator instance."""
        return SleepMetricsCalculator(db_connection)

    def test_sleep_metrics_calculator_initialization(self, sleep_metrics_calculator):
        """Test that the calculator initializes properly."""
        assert sleep_metrics_calculator is not None
        assert hasattr(sleep_metrics_calculator, "conn")
        assert hasattr(sleep_metrics_calculator, "queries")

    @pytest.mark.asyncio
    async def test_calculate_sleep_metrics(self, sleep_metrics_calculator, populate_db):
        """Test calculation of sleep metrics."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func to always return True
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate sleep metrics
        metrics = await sleep_metrics_calculator.calculate_sleep_metrics(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify the metrics
        assert metrics is not None
        assert metrics.date == date

        # Check specific sleep metrics
        assert metrics.total_sleep_seconds is not None
        assert metrics.total_sleep_seconds > 0
        assert isinstance(metrics.total_sleep_seconds, int)

        # Check sleep efficiency
        assert metrics.sleep_efficiency_pct is not None
        assert 0 <= metrics.sleep_efficiency_pct <= 100

        # Check sleep stages
        assert metrics.deep_sleep_seconds is not None
        assert metrics.light_sleep_seconds is not None
        assert metrics.rem_sleep_seconds is not None

        # Verify sleep stage percentages
        assert metrics.deep_sleep_pct is not None
        assert metrics.light_sleep_pct is not None
        assert metrics.rem_sleep_pct is not None

        # Verify sum of percentages is approximately 100%
        sum_pct = metrics.deep_sleep_pct + metrics.light_sleep_pct + metrics.rem_sleep_pct
        assert 99.5 <= sum_pct <= 100.5, f"Sum of sleep stage percentages should be ~100%, got {sum_pct}"

        # Bedtime and wake time should be timestamps
        assert metrics.bedtime_timestamp is not None
        assert metrics.waketime_timestamp is not None
        assert metrics.waketime_timestamp > metrics.bedtime_timestamp

    @pytest.mark.asyncio
    async def test_get_total_sleep_time(self, sleep_metrics_calculator, populate_db):
        """Test getting total sleep time."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Get total sleep time
        tst = await sleep_metrics_calculator.get_total_sleep_time(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify total sleep time
        assert tst is not None
        assert tst > 0
        assert isinstance(tst, int)

        # Expected range for normal sleep (4-10 hours in seconds)
        assert 4 * 3600 <= tst <= 10 * 3600, f"Sleep time should be between 4-10 hours, got {tst/3600:.1f} hours"

    @pytest.mark.asyncio
    async def test_get_sleep_efficiency(self, sleep_metrics_calculator, populate_db):
        """Test getting sleep efficiency."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Get sleep efficiency
        efficiency = await sleep_metrics_calculator.get_sleep_efficiency(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify sleep efficiency
        assert efficiency is not None
        assert 0 <= efficiency <= 100

        # Expected range for normal sleep efficiency
        assert 50 <= efficiency <= 100, f"Sleep efficiency should be between 50-100%, got {efficiency:.1f}%"

    @pytest.mark.asyncio
    async def test_get_sleep_stage_percentages(self, sleep_metrics_calculator, populate_db):
        """Test getting sleep stage percentages."""
        user_id, date_str = populate_db
        date = dt.date.fromisoformat(date_str)

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Get sleep stage percentages
        stages = await sleep_metrics_calculator.get_sleep_stage_percentages(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Verify sleep stage percentages
        assert stages is not None
        assert "deep" in stages
        assert "light" in stages
        assert "rem" in stages

        # Verify percentages are in expected ranges
        assert 0 <= stages["deep"] <= 40, f"Deep sleep % should be between 0-40%, got {stages['deep']:.1f}%"
        assert 40 <= stages["light"] <= 90, f"Light sleep % should be between 40-90%, got {stages['light']:.1f}%"
        assert 0 <= stages["rem"] <= 35, f"REM sleep % should be between 0-35%, got {stages['rem']:.1f}%"

        # Verify sum of percentages is approximately 100%
        sum_pct = stages["deep"] + stages["light"] + stages["rem"]
        assert 99.5 <= sum_pct <= 100.5, f"Sum of sleep stage percentages should be ~100%, got {sum_pct}"

    @pytest.mark.asyncio
    async def test_no_data_available(self, sleep_metrics_calculator, db_connection):
        """Test behavior when no data is available."""
        user_id = 99999  # Non-existent user
        date = dt.date.fromisoformat("2025-05-02")

        # Mock ensure_data_available_func to return False (no data)
        mock_ensure_data = AsyncMock(return_value=False)

        # Calculate sleep metrics with no data
        metrics = await sleep_metrics_calculator.calculate_sleep_metrics(
            user_id, date, ensure_data_available_func=mock_ensure_data
        )

        # Should return None when no data is available
        assert metrics is None

    @pytest.mark.asyncio
    async def test_calculate_sleep_metrics_range(self, sleep_metrics_calculator, populate_db):
        """Test calculation of sleep metrics for a date range."""
        user_id, date_str = populate_db
        start_date = dt.date.fromisoformat(date_str)
        end_date = start_date + dt.timedelta(days=1)  # Just one day for test

        # Mock ensure_data_available_func
        mock_ensure_data = AsyncMock(return_value=True)

        # Calculate sleep metrics for range
        metrics_range = await sleep_metrics_calculator.calculate_sleep_metrics_range(
            user_id, start_date, end_date, ensure_data_available_func=mock_ensure_data
        )

        # Should return a dictionary with dates as keys
        assert isinstance(metrics_range, dict)

        # Should have at least one date (we populated May 1st)
        assert len(metrics_range) >= 1

        # The key should be a date object
        for date_key, metrics in metrics_range.items():
            assert isinstance(date_key, dt.date)
            # May 1st should have data
            if date_key == start_date:
                assert isinstance(metrics.total_sleep_seconds, int)
                assert metrics.total_sleep_seconds > 0
            # For other dates, we just check the object exists
            else:
                assert metrics is not None
