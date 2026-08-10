"""Alex's Alcoa shift roster — calculated from the 4-week rotating cycle.

Roster cycle start: 2026-06-29 (Monday)
Week A: Off, Day, Day, Off, Night, Night, Night
Week B: Off, Off, Off, Day, Day, Off, Off
Week C: Night, Night, Off, Off, Off, Day, Day
Week D: Day, Off, Night, Night, Off, Off, Off

Shift times:
  Day shift:       6:10am–6:10pm   (alarm 4:55am)
  Night (consec.): 6:10pm–6:10am   (alarm 5:00pm)
  First night:     7:00pm–6:15am   (alarm 6:00pm)
  Day off:         no alarm
"""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Australia/Melbourne")
CYCLE_START = date(2026, 6, 29)  # Monday

ROSTER = [
    # Week A (index 0) — Mon, Tue, Wed, Thu, Fri, Sat, Sun
    ["Off", "Day", "Day", "Off", "Night", "Night", "Night"],
    # Week B
    ["Off", "Off", "Off", "Day", "Day", "Off", "Off"],
    # Week C
    ["Night", "Night", "Off", "Off", "Off", "Day", "Day"],
    # Week D
    ["Day", "Off", "Night", "Night", "Off", "Off", "Off"],
]

WEEK_LABELS = ["A", "B", "C", "D"]

SHIFT_NAMES = {
    "Day": "Day Shift",
    "Night": "Night Shift",
    "Off": "Day Off",
}

SHIFT_START = {
    "Day": "6:10am",
    "Night": "6:10pm",
    "Night_first": "7:00pm",
}

SHIFT_END = {
    "Day": "6:10pm",
    "Night": "6:10am",
    "Night_first": "6:15am",
}

ALARM = {
    "Day": "4:55am",
    "Night": "5:00pm",
    "Night_first": "6:00pm",
    "Off": None,
}


def _get_week_info(d: date) -> tuple:
    """Return (week_in_cycle: 0-3, day_of_week: 0=Mon..6=Sun)."""
    delta = d - CYCLE_START
    total_days = delta.days
    if total_days < 0:
        # Before cycle start — clamp to week A
        return 0, d.weekday()
    week_idx = (total_days // 7) % 4
    day_idx = d.weekday()
    return week_idx, day_idx


def _is_first_night(week_idx: int, day_idx: int) -> bool:
    """Check if this is the first night in a night block."""
    yesterday_day = (day_idx - 1) % 7
    # Get yesterday's shift
    prev_shift = ROSTER[week_idx][yesterday_day]
    return prev_shift != "Night"


def _get_shift_for(d: date) -> str:
    """Get shift type ('Off', 'Day', 'Night') for a given date."""
    week_idx, day_idx = _get_week_info(d)
    return ROSTER[week_idx][day_idx]


def _format_shift_detail(shift_type: str, is_first: bool = False) -> str:
    if shift_type == "Off":
        return "Day Off"
    if shift_type == "Night" and is_first:
        return "Night Shift (First)"
    return SHIFT_NAMES[shift_type]


def _format_time(shift_type: str, is_first: bool = False) -> tuple:
    """Return (start_time, end_time, alarm_time)."""
    if shift_type == "Off":
        return (None, None, None)
    if shift_type == "Night" and is_first:
        return (SHIFT_START["Night_first"], SHIFT_END["Night_first"], ALARM["Night_first"])
    return (SHIFT_START[shift_type], SHIFT_END[shift_type], ALARM[shift_type])


def get_today_shift() -> dict:
    """Calculate today's shift info."""
    now = datetime.now(TZ)
    today = now.date()
    week_idx, day_idx = _get_week_info(today)
    shift_type = ROSTER[week_idx][day_idx]
    is_first = shift_type == "Night" and _is_first_night(week_idx, day_idx)
    detail = _format_shift_detail(shift_type, is_first)
    start, end, alarm = _format_time(shift_type, is_first)

    # Next shift
    tomorrow = today + timedelta(days=1)
    next_type = _get_shift_for(tomorrow)
    next_week_idx, next_day_idx = _get_week_info(tomorrow)
    next_is_first = next_type == "Night" and _is_first_night(next_week_idx, next_day_idx)
    next_start, _, _ = _format_time(next_type, next_is_first)
    next_detail = _format_shift_detail(next_type, next_is_first)

    cycle_week_num = week_idx + 1
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return {
        "shift": shift_type,
        "detail": detail,
        "date": today.isoformat(),
        "day_name": day_names[day_idx],
        "week_in_cycle": cycle_week_num,
        "day_in_week": day_idx,
        "cycle_progress": f"Week {WEEK_LABELS[week_idx]}, Day {day_idx + 1}",
        "next_shift": {
            "shift": next_type,
            "detail": next_detail,
            "date": tomorrow.isoformat(),
            "time": next_start,
        },
        "alarm_time": alarm,
        "shift_start": start,
        "shift_end": end,
    }