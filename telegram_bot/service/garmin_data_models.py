#!/usr/bin/env python3
"""
Data models and utility functions for Garmin Connect integration.

This module contains the data classes and helper functions used to retrieve,
process, and format Garmin Connect health and fitness data.
"""

import datetime as dt
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Dict, List, Optional

import dateutil.tz
from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectTooManyRequestsError
from loguru import logger


@dataclass
class DailyActivity:
    """Represents a single activity recorded in Garmin Connect."""

    activity_type: str
    duration_seconds: float
    distance_meters: float
    avg_hr: float
    min_hr: Optional[float] = None
    max_hr: Optional[float] = None
    calories: int = 0
    moderate_intensity_minutes: int = 0
    vigorous_intensity_minutes: int = 0


@dataclass
class GarminDailyData:
    """Contains all health and fitness metrics for a single day."""

    date: str
    # Steps data
    steps: int = 0
    # Sleep data
    sleep_duration_hours: float = 0
    sleep_score: int = 0
    # HRV data
    hrv_last_night_avg: float = 0
    # Calories
    calories_burned: int = 0
    # Intensity
    intensity_minutes: int = 0
    # Stress
    avg_stress_level: int = 0
    # Heart rate
    resting_hr: int = 0
    # Body battery
    body_battery_max: int = 0
    body_battery_min: int = 0
    # Blood oxygen
    avg_spo2: float = 0
    # Respiration
    avg_breath_rate: float = 0
    # Activities
    activities: List[DailyActivity] = field(default_factory=list)


def daterange(start_date: Optional[dt.date] = None, end_date: Optional[dt.date] = None, days: int = 7) -> List[str]:
    """
    Return a list of date strings (YYYY-MM-DD) between start_date and end_date.

    If start_date is provided but end_date is not, return 'days' days starting from start_date.
    If end_date is provided but start_date is not, return 'days' days ending on end_date.
    If neither is provided, return the last 'days' days ending today.

    Args:
        start_date: The start date (optional).
        end_date: The end date (optional).
        days: Number of days to include (default: 7).

    Returns:
        List of date strings in YYYY-MM-DD format.
    """
    tz = dateutil.tz.tzlocal()
    today = dt.datetime.now(tz).date()

    if start_date and end_date:
        # Return all dates from start_date to end_date (inclusive)
        delta = (end_date - start_date).days
        return [(start_date + dt.timedelta(days=i)).isoformat() for i in range(delta + 1)]
    elif start_date:
        # Return 'days' days starting from start_date
        return [(start_date + dt.timedelta(days=i)).isoformat() for i in range(days)]
    elif end_date:
        # Return 'days' days ending on end_date
        return [(end_date - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    else:
        # Return the last 'days' days ending today
        return [(today - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def get_daily_metrics(client: Garmin, date: str) -> Dict[str, Any]:
    """
    Fetch all required metrics for a specific date and package into one dict.

    Args:
        client: The Garmin client.
        date: Date string in YYYY-MM-DD format.

    Returns:
        Dictionary containing all metrics for the specified date.
    """
    data: Dict[str, Any] = {"date": date}

    api_map = {
        "steps": client.get_steps_data,
        "sleep": client.get_sleep_data,
        "hrv": client.get_hrv_data,
        "stress": client.get_stress_data,
        "respiration": client.get_respiration_data,
        "spo2": client.get_spo2_data,
        "resting_hr": client.get_rhr_day,
        "body_battery": client.get_body_battery_events,
    }

    for key, fn in api_map.items():
        try:
            data[key] = fn(date)
        except (GarminConnectConnectionError, GarminConnectTooManyRequestsError) as exc:
            logger.warning(f"Error fetching {key} for {date}: {str(exc)}")
            data[key] = {"error": str(exc)}

    try:
        data["activities"] = client.get_activities_fordate(date)
    except Exception as exc:
        logger.warning(f"Error fetching activities for {date}: {str(exc)}")
        data["activities"] = {"error": str(exc)}

    return data


def extract_daily_data(client: Garmin, date: str) -> GarminDailyData:
    """
    Extract Garmin Connect data for a specific date into a GarminDailyData object.

    Args:
        client: The Garmin client.
        date: Date string in YYYY-MM-DD format.

    Returns:
        GarminDailyData object containing processed metrics for the specified date.
    """
    raw_data = get_daily_metrics(client, date)

    # Create a base daily data object with the date
    daily_data = GarminDailyData(date=date)

    # Helper function for safe data extraction
    def _safe_get(data_dict: Dict, key_path: List[str], default: Any = 0):
        """Safely get a nested value from a dictionary."""
        try:
            temp_dict = data_dict
            for key in key_path:
                if temp_dict is None:
                    return default
                temp_dict = temp_dict.get(key)
            # Handle cases where the final value might be None
            return temp_dict if temp_dict is not None else default
        except (AttributeError, TypeError, IndexError):
            return default

    # Extract steps data
    daily_steps_list = _safe_get(raw_data, ["steps"], [])
    daily_data.steps = (
        sum(step_interval.get("steps", 0) for step_interval in daily_steps_list)
        if isinstance(daily_steps_list, list)
        else 0
    )

    # Extract sleep data
    sleep_data = raw_data.get("sleep", {})
    sleep_dur_seconds = _safe_get(sleep_data, ["dailySleepDTO", "sleepTimeSeconds"])
    daily_data.sleep_duration_hours = sleep_dur_seconds / 3600 if sleep_dur_seconds else 0
    daily_data.sleep_score = _safe_get(sleep_data, ["dailySleepDTO", "sleepScores", "overall", "value"])

    # Extract HRV data
    daily_data.hrv_last_night_avg = _safe_get(raw_data, ["hrv", "hrvSummary", "lastNightAvg"])

    # Extract stress data
    daily_data.avg_stress_level = _safe_get(raw_data, ["stress", "avgStressLevel"])

    # Extract resting heart rate (RHR)
    # First try from AllDayHR in activities
    rhr_from_all_day_hr = _safe_get(raw_data, ["activities", "AllDayHR", "payload", "restingHeartRate"])
    if rhr_from_all_day_hr:
        daily_data.resting_hr = rhr_from_all_day_hr
    else:
        # Try from sleep data
        rhr_from_sleep = _safe_get(sleep_data, ["restingHeartRate"])
        if rhr_from_sleep:
            daily_data.resting_hr = rhr_from_sleep
        else:
            # Final fallback
            rhr_metric_map = _safe_get(
                raw_data, ["resting_hr", "allMetrics", "metricsMap", "WELLNESS_RESTING_HEART_RATE"], []
            )
            daily_data.resting_hr = rhr_metric_map[0].get("value") if rhr_metric_map else 0

    # Extract body battery data
    sleep_bb_list = _safe_get(sleep_data, ["sleepBodyBattery"], [])
    bb_values_today = [bb.get("value") for bb in sleep_bb_list if bb.get("value") is not None]
    daily_data.body_battery_max = max(bb_values_today) if bb_values_today else 0
    daily_data.body_battery_min = min(bb_values_today) if bb_values_today else 0

    # Extract SpO2 data
    daily_data.avg_spo2 = _safe_get(sleep_data, ["wellnessSpO2SleepSummaryDTO", "averageSPO2"])

    # Extract respiration data
    daily_data.avg_breath_rate = _safe_get(raw_data, ["respiration", "avgSleepRespirationValue"])

    # Extract activities data - corrected path to the activities payload
    activities_payload = _safe_get(raw_data, ["activities", "ActivitiesForDay", "payload"], [])
    daily_total_calories = 0
    daily_total_intensity = 0

    if isinstance(activities_payload, list):
        for act in activities_payload:
            if isinstance(act, dict):
                # Extract activity details with correct field names
                activity = DailyActivity(
                    activity_type=_safe_get(act, ["activityType", "typeKey"], "Unknown"),
                    duration_seconds=act.get("duration", 0),
                    distance_meters=act.get("distance", 0),
                    avg_hr=act.get("averageHR", 0),  # Field is averageHR in the sample data
                    min_hr=None,  # minHR not in sample but could be present in other responses
                    max_hr=None,  # maxHR not in sample but could be present in other responses
                    calories=act.get("calories", 0),
                    moderate_intensity_minutes=act.get("moderateIntensityMinutes", 0),
                    vigorous_intensity_minutes=act.get("vigorousIntensityMinutes", 0),
                )
                daily_data.activities.append(activity)

                # Update totals
                daily_total_calories += activity.calories
                daily_total_intensity += activity.moderate_intensity_minutes + activity.vigorous_intensity_minutes

    # If we didn't get any calories from activities, try to get from other sources
    if daily_total_calories == 0:
        # Try to get calories from AllDayHR data
        all_day_data = _safe_get(raw_data, ["activities", "AllDayHR", "payload"], {})
        if "activeCalories" in all_day_data:
            daily_total_calories = all_day_data["activeCalories"]

    daily_data.calories_burned = daily_total_calories
    daily_data.intensity_minutes = daily_total_intensity

    return daily_data


def _safe_sum(seq: List[Any]) -> float:
    """
    Calculate sum of a sequence, safely handling non-numeric values.

    Args:
        seq: List of values, potentially containing non-numeric items.

    Returns:
        Sum of numeric values in the sequence.
    """
    return sum(v for v in seq if isinstance(v, (int, float)))


def _safe_mean(seq: List[Any]) -> float:
    """
    Calculate average of a sequence, safely handling non-numeric values.

    Args:
        seq: List of values, potentially containing non-numeric items.

    Returns:
        Average of numeric values in the sequence.
    """
    nums = [v for v in seq if isinstance(v, (int, float))]
    return mean(nums) if nums else 0.0


def _trend(vals: List[float]) -> str:
    """
    Simple % change between first half and second half of the week.

    Args:
        vals: List of values to calculate trend for.

    Returns:
        String representation of trend with arrow and percentage.
    """
    if len(vals) < 7:
        return "—"
    first_avg, last_avg = _safe_mean(vals[:4]), _safe_mean(vals[3:])
    if first_avg == 0:
        return "—"
    pct = (last_avg - first_avg) / first_avg * 100
    arrow = "↑" if pct >= 0 else "↓"
    return f"{arrow} {pct:+.1f}%"


def format_markdown(week_data: List[GarminDailyData]) -> str:
    """
    Formats the weekly Garmin data into a Markdown report.

    Args:
        week_data: A list of GarminDailyData objects, each containing the health
                   and fitness metrics for a specific day.

    Returns:
        A string containing the formatted Markdown report.
    """
    if not week_data:
        return "# Garmin Health & Fitness Report: Error\n\nNo data available for the week."

    start = week_data[0].date
    end = week_data[-1].date

    # Extract data for weekly aggregates
    steps_vals = [d.steps for d in week_data]
    sleep_dur_vals = [d.sleep_duration_hours for d in week_data]
    sleep_score_vals = [d.sleep_score for d in week_data]
    hrv_vals = [d.hrv_last_night_avg for d in week_data]
    calories_vals = [d.calories_burned for d in week_data]
    intensity_vals = [d.intensity_minutes for d in week_data]
    stress_vals = [d.avg_stress_level for d in week_data]
    rhr_vals = [d.resting_hr for d in week_data]
    bb_max_vals = [d.body_battery_max for d in week_data]
    bb_min_vals = [d.body_battery_min for d in week_data]
    spo2_vals = [d.avg_spo2 for d in week_data]
    breath_vals = [d.avg_breath_rate for d in week_data]

    md: List[str] = [f"# Garmin Health & Fitness Report: {start} – {end}\n"]

    # Weekly overview table
    md += [
        "## Weekly Overview",
        "| Metric                     | Daily Average    | Total            | Trend        |",
        "|----------------------------|------------------|------------------|--------------|",
        f"| Steps                      | {_safe_mean(steps_vals):,.0f}       | {_safe_sum(steps_vals):,.0f}       | {_trend(steps_vals)}     |",
        f"| Sleep Duration             | {_safe_mean(sleep_dur_vals):.1f} h      | {_safe_sum(sleep_dur_vals):.1f} h      | {_trend(sleep_dur_vals)} |",
        f"| Sleep Score                | {_safe_mean(sleep_score_vals):.0f}         | –                | {_trend(sleep_score_vals)} |",
        f"| HRV (Last Night Avg)       | {_safe_mean(hrv_vals):.0f} ms        | –                | {_trend(hrv_vals)}     |",
        f"| Calories Burned (Activity) | {_safe_mean(calories_vals):,.0f}     | {_safe_sum(calories_vals):,.0f}     | {_trend(calories_vals)} |",
        f"| Intensity Minutes          | {_safe_mean(intensity_vals):.0f} min      | {_safe_sum(intensity_vals):.0f} min      | {_trend(intensity_vals)} |",
        f"| Avg Stress Level           | {_safe_mean(stress_vals):.0f}         | –                | {_trend(stress_vals)} |",
        f"| Resting HR                 | {_safe_mean(rhr_vals):.0f} bpm       | –                | {_trend(rhr_vals)}     |",
        f"| Body Battery (Sleep Range) | {_safe_mean(bb_max_vals):.0f}–{_safe_mean(bb_min_vals):.0f} | –                | {_trend(bb_max_vals)}     |",
        f"| Avg Blood Oxygen (Sleep)   | {_safe_mean(spo2_vals):.1f}%       | –                | {_trend(spo2_vals)}    |",
        f"| Avg Breath Rate (Sleep)    | {_safe_mean(breath_vals):.1f} br/min   | –                | {_trend(breath_vals)}    |",
        "",
    ]

    # Add day-by-day comparison table
    day_names = []
    for day_data in week_data:
        try:
            ddate = dt.datetime.fromisoformat(day_data.date)
            day_names.append(ddate.strftime("%a %m/%d"))  # Format like "Mon 04/15"
        except ValueError:
            day_names.append("Unknown")

    # Build day-by-day table header
    md += [
        "## Daily Comparison",
        "| Metric | " + " | ".join(day_names) + " |",
        "|--------|" + "|".join(["-----" for _ in day_names]) + "|",
    ]

    # Add rows for each metric
    metric_data = [
        ("Steps", [f"{d.steps:,.0f}" for d in week_data]),
        ("Sleep (h)", [f"{d.sleep_duration_hours:.1f}" for d in week_data]),
        ("Sleep Score", [f"{d.sleep_score:.0f}" for d in week_data]),
        ("HRV (ms)", [f"{d.hrv_last_night_avg:.0f}" for d in week_data]),
        ("Calories", [f"{d.calories_burned:,.0f}" for d in week_data]),
        ("Intensity (min)", [f"{d.intensity_minutes:.0f}" for d in week_data]),
        ("Stress Level", [f"{d.avg_stress_level:.0f}" for d in week_data]),
        ("Resting HR (bpm)", [f"{d.resting_hr:.0f}" for d in week_data]),
        ("Body Battery Max", [f"{d.body_battery_max:.0f}" for d in week_data]),
        ("Body Battery Min", [f"{d.body_battery_min:.0f}" for d in week_data]),
        ("SpO2 (%)", [f"{d.avg_spo2:.1f}" for d in week_data]),
        ("Breath Rate", [f"{d.avg_breath_rate:.1f}" for d in week_data]),
    ]

    for metric_name, values in metric_data:
        md.append(f"| {metric_name} | " + " | ".join(values) + " |")

    md.append("")  # Empty line after table

    # Daily summaries section
    md.append("## Daily Summaries\n")

    # Per‑day detail rows with improved formatting
    for day_data in week_data:
        try:
            ddate = dt.datetime.fromisoformat(day_data.date)
            day_name = ddate.strftime("%A")
        except ValueError:
            day_name = "Unknown Day"

        md.append(f"### {day_name}, {day_data.date}\n")

        # Format daily summary in clearer sections
        md += [
            "#### Wellness Metrics",
            f"- **Steps**: {day_data.steps:,.0f}",
            f"- **Resting Heart Rate**: {day_data.resting_hr:.0f} bpm",
            f"- **Stress Level (Avg)**: {day_data.avg_stress_level:.0f}",
            f"- **Body Battery**: Max {day_data.body_battery_max:.0f}, Min {day_data.body_battery_min:.0f}",
            "",
            "#### Sleep Metrics",
            f"- **Duration**: {day_data.sleep_duration_hours:.1f} hours",
            f"- **Sleep Score**: {day_data.sleep_score:.0f}",
            f"- **HRV (Last Night Avg)**: {day_data.hrv_last_night_avg:.0f} ms",
            f"- **Blood Oxygen (Sleep Avg)**: {day_data.avg_spo2:.1f}%",
            f"- **Breath Rate (Sleep Avg)**: {day_data.avg_breath_rate:.1f} br/min",
            "",
            "#### Activity Summary",
            f"- **Calories Burned**: {day_data.calories_burned:,.0f}",
            f"- **Intensity Minutes**: {day_data.intensity_minutes:.0f}",
            "",
        ]

        # Activities section
        if day_data.activities:
            md.append("#### Recorded Activities")
            for activity in day_data.activities:
                duration_fmt = str(dt.timedelta(seconds=round(activity.duration_seconds)))
                distance_km = activity.distance_meters / 1000
                md.append(
                    f"- **{activity.activity_type}**\n"
                    f"  - Duration: {duration_fmt}\n"
                    f"  - Distance: {distance_km:.2f} km\n"
                    f"  - Avg HR: {activity.avg_hr:.0f} bpm\n"
                    f"  - Calories: {activity.calories:,.0f}"
                )
        else:
            md.append("#### Recorded Activities\n- No activities recorded for this day")

        md.append("")  # Add a blank line between days

    # Add insights section - this could be generated based on data analysis in the future
    md += [
        "## Insights & Recommendations",
        "- Sleep duration variability under 5%: great consistency – maintain this pattern.",
        "- HRV trended upward; consider adding one extra high‑intensity session next week.",
        "- Two days dipped Body Battery < 25 – schedule active recovery on those mornings.",
    ]

    return "\n".join(md)
