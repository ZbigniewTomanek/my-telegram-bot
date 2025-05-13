# Garmin Data Reference

This document provides a comprehensive overview of the data exported from the Garmin API used in this project.

## Activity Data

### Activities
- Daily activities with detailed tracking
- Sample data structure:
```json
{
  "activityName": "Terchova Piesze wędrówki",
  "startTimeLocal": "2025-05-01T11:51:16.0",
  "activityType": "hiking",
  "distance": 16926.55078125,
  "duration": 18651.248046875,
  "calories": 2395.0,
  "steps": 22800
}
```
- Includes timestamps, distances, durations, calories, and steps
- Categorized by activity type (hiking, running, etc.)

### Activity Details
- Extended information for specific activity sessions
- Includes:
  - Detailed GPS data
  - Heart rate during activity
  - Pace/speed metrics
  - Elevation data
  - Intensity minutes

### Steps
- Step counts at regular intervals throughout the day
- Tracks progress toward step goals
- Includes timestamps for tracking patterns

### Floors
- Floor climbing data with timestamps
- Structure includes:
  - `endTimestampGMT`
  - `endTimestampLocal`
  - `floorValuesArray`
  - `floorsValueDescriptorDTOList`
  - `startTimestampGMT`
  - `startTimestampLocal`

### Intensity Minutes
- Tracks moderate and vigorous activity duration
- Data includes:
  - Weekly goals and progress
  - Daily breakdown of moderate/vigorous minutes
  - Timestamps for activity intensity periods

## Health Metrics

### Heart Rate
- Heart rate readings throughout the day with timestamps
- Structure includes:
  - Maximum and minimum heart rates
  - Resting heart rate
  - Time-series heart rate data
  - Historical average comparisons

### Resting Heart Rate
- Daily resting heart rate values
- Seven-day averages for trend analysis
- Used as baseline for cardiovascular health assessment

### HRV (Heart Rate Variability)
- HRV readings and summary statistics
- Important indicators of recovery and stress
- Structure includes:
  - `endTimestampGMT`
  - `endTimestampLocal`
  - `hrvReadings`
  - `hrvSummary`
  - Sleep-related timestamps

### Sleep
- Comprehensive sleep data including:
  - Sleep stages (deep, light, REM, awake)
  - Sleep start/end times
  - Sleep quality metrics
  - Respiration during sleep
  - Overnight skin temperature
  - Restless moments tracking
  - HRV during sleep
  - Sleep Body Battery readings

### SpO2 (Blood Oxygen)
- Blood oxygen readings with timestamps
- Structure includes:
  - Average SpO2 values
  - Lowest SpO2 readings
  - Sleep SpO2 measurements
  - Continuous reading data
  - Seven-day average comparisons

### Stress
- Stress levels throughout the day
- Categorization of stress (high, medium, low, rest)
- Duration and percentage of time in each stress category
- Body Battery correlations

### Body Battery
- Energy level metrics throughout day/night
- Components include:
  - Highest/lowest daily values
  - Charged value (recovery)
  - Drained value (expenditure)
  - Readings throughout day with timestamps

### Respiration
- Breathing rate data
- Tracks:
  - Average, highest, and lowest respiration values
  - Overnight respiration patterns
  - Breathing abnormalities

## Physical Measurements

### Hydration
- Fluid intake tracking
- Structure includes:
  - `activityIntakeInML`
  - `calendarDate`
  - `dailyAverageinML`
  - `goalInML`
  - `lastEntryTimestampLocal`
  - `sweatLossInML`
  - `userId`
  - `valueInML`

### Fitness Age
- Calculated fitness age compared to chronological age
- Structure includes:
  - `achievableFitnessAge`
  - `chronologicalAge`
  - `components` (contributing factors)
  - `fitnessAge`
  - `lastUpdated`
  - `previousFitnessAge`

### Personal Records
- Performance benchmarks across activities
- May include records for:
  - Distance achievements
  - Speed records
  - Duration milestones
  - Elevation accomplishments

## Device Data

### Devices
- Detailed information about Garmin devices including:
  - Device capabilities and features
  - Firmware versions
  - Configuration details
  - Registration information
  - Device type and category
  - Sensor capabilities
  - Connectivity options

## Summary Statistics

### Daily Stats
- Comprehensive daily metrics combining:
  - Calories (active, BMR, consumed, remaining)
  - Steps and distance totals
  - Floors climbed
  - Heart rate summaries
  - Stress summaries
  - Sleep duration
  - Body Battery metrics
  - Intensity minutes
  - Overall health indicators

### Weekly and Monthly Trends
- Aggregated statistics showing patterns over time
- Comparison to previous periods
- Progress toward longer-term goals

## Additional Data

### Solar Panel Utilization
- For solar-powered devices
- Tracks energy generation and efficiency

### Training Status
- Metrics related to training effectiveness
- May include:
  - Training load
  - Recovery time
  - VO2 max estimates
  - Performance condition

### Training Readiness
- Readiness metrics based on recovery factors
- Components may include:
  - Sleep quality
  - HRV status
  - Recent training load
  - Recovery indicators

---

All data types typically include timestamps in both GMT and local time where applicable, allowing for precise tracking of metrics throughout the day. This enables detailed analysis of patterns and trends in the user's health and fitness data.