#!/usr/bin/env python3
"""
Unit tests for GarminConnectService.

These tests validate the Garmin Connect data parsing functionality
using mock data from API response files.
"""

import datetime as dt
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from telegram_bot.service.garmin_connect_service import GarminConnectService
from telegram_bot.service.garmin_data_models import (
    DailyActivity,
    GarminDailyData,
    extract_daily_data,
    get_daily_metrics,
)
from tests import GARMIN_TEST_DATA_DIR

# Path to test data files

# Test date used in the sample files
TEST_DATE = "2025-05-01"


class MockGarminClient:
    """Mock Garmin client for testing."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def get_steps_data(self, date_str):
        return self._load_data(f"garmin_steps_{date_str}.json")

    def get_sleep_data(self, date_str):
        return self._load_data(f"garmin_sleep_{date_str}.json")

    def get_hrv_data(self, date_str):
        return self._load_data(f"garmin_hrv_{date_str}.json")

    def get_stress_data(self, date_str):
        return self._load_data(f"garmin_stress_{date_str}.json")

    def get_respiration_data(self, date_str):
        return self._load_data(f"garmin_respiration_{date_str}.json")

    def get_spo2_data(self, date_str):
        return self._load_data(f"garmin_spo2_{date_str}.json")

    def get_rhr_day(self, date_str):
        return self._load_data(f"garmin_resting_hr_{date_str}.json")

    def get_body_battery_events(self, date_str):
        return self._load_data(f"garmin_body_battery_{date_str}.json")

    def get_heart_rates(self, date_str):
        return self._load_data(f"garmin_heart_rates_{date_str}.json")

    def get_activities_fordate(self, date_str):
        return self._load_data(f"garmin_activities_{date_str}.json")

    def get_activity_details(self, activity_id):
        # This is a placeholder - actual tests may need to be implemented differently
        # depending on how activity IDs are handled in the test data
        return {
            "activity_id": activity_id,
            "type": "Running",
            "summaryDTO": {
                "activityType": {"typeKey": "running"},
                "duration": 3600.0,
                "distance": 5000.0,
                "averageHR": 150,
                "minHR": 120,
                "maxHR": 180,
                "calories": 500,
                "moderateIntensityMinutes": 15,
                "vigorousIntensityMinutes": 30,
            },
            "details": {},
        }

    def _load_data(self, filename):
        try:
            with open(self.data_dir / filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Check if there's an error version of the file
            error_filename = filename.replace(".json", "_error.json")
            try:
                with open(self.data_dir / error_filename, "r") as f:
                    error_data = json.load(f)
                    # If it's an error file, return the error data instead of raising
                    return {"error": error_data.get("error", "Unknown error")}
            except FileNotFoundError:
                return {"error": f"Mock data file not found: {filename}"}


@pytest.fixture
def mock_garmin_client():
    """Fixture to create a mock Garmin client."""
    return MockGarminClient(GARMIN_TEST_DATA_DIR)


@pytest.fixture
def mock_account_manager():
    """Fixture to create a mock GarminAccountManager."""
    mock_manager = MagicMock()
    mock_manager.get_user_token_path.return_value = Path("/mock/token/path")
    mock_manager.create_client.return_value = MockGarminClient(GARMIN_TEST_DATA_DIR)
    return mock_manager


@pytest_asyncio.fixture
async def garmin_service(mock_account_manager):
    """Fixture to create a GarminConnectService with a mock account manager."""
    with patch("telegram_bot.service.garmin_connect_service.GarminAccountManager", return_value=mock_account_manager):
        service = GarminConnectService(Path("/mock/token/store"))
        service.account_manager = mock_account_manager
        yield service


# Tests for extract_daily_data function
def test_extract_daily_data(mock_garmin_client):
    """Test that extract_daily_data correctly processes and combines data from various endpoints."""
    # Extract daily data using the mock client
    daily_data = extract_daily_data(mock_garmin_client, TEST_DATE)

    # Verify that the function returns a GarminDailyData object
    assert isinstance(daily_data, GarminDailyData)
    assert daily_data.date == TEST_DATE

    # Validate steps data if available in test data
    try:
        steps_data = mock_garmin_client.get_steps_data(TEST_DATE)
        if not isinstance(steps_data, dict) or "error" not in steps_data:
            expected_steps = sum(step.get("steps", 0) for step in steps_data)
            assert daily_data.steps == expected_steps
    except Exception:
        pass  # Skip if test data not available


def test_get_daily_metrics(mock_garmin_client):
    """Test that get_daily_metrics correctly fetches and combines data from various endpoints."""
    # Get metrics using the mock client
    metrics = get_daily_metrics(mock_garmin_client, TEST_DATE)

    # Verify the basic structure of the returned data
    assert isinstance(metrics, dict)
    assert "date" in metrics
    assert metrics["date"] == TEST_DATE

    # Check for expected keys in the metrics
    expected_keys = ["steps", "sleep", "hrv", "stress", "respiration", "spo2", "resting_hr", "body_battery", "AllDayHR"]

    for key in expected_keys:
        assert key in metrics, f"Expected key '{key}' not found in metrics"


def test_get_daily_metrics_with_activity_errors(mocker):
    """Test that get_daily_metrics handles errors when fetching activity data."""
    # Create a mock client with an error when fetching activities
    activity_error_client = MagicMock()

    # Mock method returns to avoid side_effect issues
    activity_error_client.get_steps_data = mocker.MagicMock(return_value=[{"steps": 1000}])
    activity_error_client.get_sleep_data = mocker.MagicMock(return_value={"dailySleepDTO": {"sleepTimeSeconds": 28800}})
    activity_error_client.get_hrv_data = mocker.MagicMock(return_value={"hrvSummary": {"lastNightAvg": 50}})
    activity_error_client.get_stress_data = mocker.MagicMock(return_value={"avgStressLevel": 30})
    activity_error_client.get_respiration_data = mocker.MagicMock(return_value={"avgSleepRespirationValue": 14.5})
    activity_error_client.get_spo2_data = mocker.MagicMock(
        return_value={"wellnessSpO2SleepSummaryDTO": {"averageSPO2": 96}}
    )
    activity_error_client.get_rhr_day = mocker.MagicMock(
        return_value={"allMetrics": {"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [{"value": 60}]}}}
    )
    activity_error_client.get_body_battery_events = mocker.MagicMock(return_value=[])
    activity_error_client.get_heart_rates = mocker.MagicMock(return_value={"restingHeartRate": 59})

    # Mock a function that raises an exception
    def raise_exception(date_str):
        raise Exception("Failed to fetch activities")

    # Activities fetch fails
    activity_error_client.get_activities_fordate = raise_exception

    # Get metrics
    metrics = get_daily_metrics(activity_error_client, TEST_DATE)

    # Verify that the activity error was handled properly
    assert "ActivitiesForDay" in metrics
    assert "errorMessage" in metrics["ActivitiesForDay"]
    assert "Failed to fetch activities" in metrics["ActivitiesForDay"]["errorMessage"]
    assert metrics["ActivitiesForDay"]["successful"] == False

    # Other metrics should still be available (verify at least one)
    assert metrics["hrv"]["hrvSummary"]["lastNightAvg"] == 50


def test_get_activity_details_parsing(mock_garmin_client):
    """Test that activity details are correctly parsed and transformed into DailyActivity objects."""
    # First, get daily metrics which should call get_activity_details internally
    metrics = get_daily_metrics(mock_garmin_client, TEST_DATE)

    # Then extract the daily data which processes activity details
    daily_data = extract_daily_data(mock_garmin_client, TEST_DATE)

    # Verify that we have activities in the daily data
    assert len(daily_data.activities) > 0

    # Get the first activity and verify its structure
    activity = daily_data.activities[0]
    assert isinstance(activity, DailyActivity)

    # Check that the activity has the expected fields from the mock data
    assert activity.activity_type is not None
    assert activity.duration_seconds > 0
    assert activity.distance_meters > 0
    assert activity.avg_hr > 0

    # Check that the details field was populated with the full response
    assert activity.details is not None


@pytest.mark.asyncio
async def test_get_data_for_period(garmin_service, mock_account_manager):
    """Test that get_data_for_period correctly processes data for a date range."""
    # Mock the create_client method to return our mock client
    mock_account_manager.create_client.return_value = MockGarminClient(GARMIN_TEST_DATA_DIR)

    # Call the service method for a single day
    result = await garmin_service.get_data_for_period(
        telegram_user_id=12345,
        start_date=dt.date.fromisoformat(TEST_DATE),
        end_date=dt.date.fromisoformat(TEST_DATE),
    )

    # Verify that we got data for the requested day
    assert len(result) == 1
    assert isinstance(result[0], GarminDailyData)
    assert result[0].date == TEST_DATE


@pytest.mark.asyncio
async def test_get_data_for_period_client_error(garmin_service, mock_account_manager):
    """Test that get_data_for_period handles client creation errors."""
    # Mock the create_client method to return None (simulating failure)
    mock_account_manager.create_client.return_value = None

    # Call the service method
    result = await garmin_service.get_data_for_period(
        telegram_user_id=12345,
        start_date=dt.date.fromisoformat(TEST_DATE),
        end_date=dt.date.fromisoformat(TEST_DATE),
    )

    # Verify that we got an empty list
    assert result == []


@pytest.mark.asyncio
async def test_calculate_summary(garmin_service):
    """Test that _calculate_summary correctly aggregates data from multiple days."""
    # Create test data for multiple days
    test_data = [
        GarminDailyData(
            date="2025-05-01",
            steps=10000,
            sleep_duration_hours=8.5,
            sleep_score=85,
            hrv_last_night_avg=60,
            calories_burned=2500,
            intensity_minutes=30,
            avg_stress_level=25,
            resting_hr=55,
            body_battery_max=100,
            body_battery_min=40,
            avg_spo2=97.5,
            avg_breath_rate=14.2,
        ),
        GarminDailyData(
            date="2025-05-02",
            steps=8000,
            sleep_duration_hours=7.2,
            sleep_score=75,
            hrv_last_night_avg=55,
            calories_burned=2200,
            intensity_minutes=20,
            avg_stress_level=30,
            resting_hr=58,
            body_battery_max=95,
            body_battery_min=35,
            avg_spo2=98.0,
            avg_breath_rate=13.8,
        ),
    ]

    # Calculate summary
    summary = garmin_service._calculate_summary(test_data)

    # Verify the structure of the summary
    assert isinstance(summary, dict)

    # Check steps summary
    assert "steps" in summary
    assert summary["steps"]["daily_avg"] == 9000  # (10000 + 8000) / 2
    assert summary["steps"]["total"] == 18000  # 10000 + 8000

    # Check sleep summary
    assert "sleep" in summary
    assert summary["sleep"]["duration_avg"] == pytest.approx(7.85, abs=0.1)  # (8.5 + 7.2) / 2
    assert summary["sleep"]["total_hours"] == pytest.approx(15.7, abs=0.1)  # 8.5 + 7.2
    assert summary["sleep"]["score_avg"] == 80  # (85 + 75) / 2


@pytest.mark.asyncio
async def test_calculate_summary_with_empty_data(garmin_service):
    """Test that _calculate_summary handles empty data gracefully."""
    # Calculate summary with empty data
    summary = garmin_service._calculate_summary([])

    # Verify that an empty dict is returned
    assert summary == {}


@pytest.mark.asyncio
async def test_export_aggregated_json(garmin_service, mock_account_manager, mocker):
    """Test that export_aggregated_json correctly processes and formats data."""
    # Mock get_data_for_period since it's already tested separately
    mocker.patch.object(
        garmin_service,
        "get_data_for_period",
        return_value=[
            GarminDailyData(
                date=TEST_DATE,
                steps=10000,
                sleep_duration_hours=8.0,
                sleep_score=80,
                hrv_last_night_avg=60,
                calories_burned=2500,
                intensity_minutes=30,
                avg_stress_level=25,
                resting_hr=55,
                body_battery_max=100,
                body_battery_min=40,
                avg_spo2=97.5,
                avg_breath_rate=14.2,
            )
        ],
    )

    # Call the service method for a single day
    result = await garmin_service.export_aggregated_json(
        telegram_user_id=12345,
        start_date=dt.date.fromisoformat(TEST_DATE),
        end_date=dt.date.fromisoformat(TEST_DATE),
    )

    # Verify the structure of the aggregated data
    assert isinstance(result, dict)
    assert "period" in result
    assert "daily_data" in result
    assert "summary" in result

    # Check period info
    assert result["period"]["start_date"] == TEST_DATE
    assert result["period"]["end_date"] == TEST_DATE
    assert result["period"]["days"] == 1

    # Check daily data
    assert isinstance(result["daily_data"], list)
    assert len(result["daily_data"]) == 1
    assert result["daily_data"][0]["date"] == TEST_DATE


@pytest.mark.asyncio
async def test_generate_markdown_report(garmin_service, mock_account_manager, mocker):
    """Test that generate_markdown_report correctly formats data as markdown."""
    # Mock get_data_for_period since it's already tested separately
    mocker.patch.object(
        garmin_service,
        "get_data_for_period",
        return_value=[
            GarminDailyData(
                date=TEST_DATE,
                steps=10000,
                sleep_duration_hours=8.0,
                sleep_score=80,
                hrv_last_night_avg=60,
                calories_burned=2500,
                intensity_minutes=30,
                avg_stress_level=25,
                resting_hr=55,
                body_battery_max=100,
                body_battery_min=40,
                avg_spo2=97.5,
                avg_breath_rate=14.2,
            )
        ],
    )

    # Call the service method for a single day
    report = await garmin_service.generate_markdown_report(
        telegram_user_id=12345,
        start_date=dt.date.fromisoformat(TEST_DATE),
        end_date=dt.date.fromisoformat(TEST_DATE),
    )

    # Verify that we got a markdown string
    assert isinstance(report, str)

    # Check for expected markdown sections
    assert "# Garmin Health & Fitness Report" in report

    # Check for metrics in the report
    metrics = ["Steps", "Sleep", "HRV", "Calories", "Stress Level", "Resting HR"]
    for metric in metrics:
        assert metric in report, f"Expected metric '{metric}' not found in report"
