from datetime import date, datetime

from detective.timeparse import find_times, time_span

D = date(2026, 3, 12)


def test_twelve_hour_clock_times():
    assert time_span("I left the office at 6 PM", D).start == datetime(2026, 3, 12, 18, 0)
    assert time_span("At 6:15 PM I locked it", D).start == datetime(2026, 3, 12, 18, 15)
    assert time_span("at 12 AM", D).start == datetime(2026, 3, 12, 0, 0)
    assert time_span("no times here, badge 2207", D) is None


def test_hedged_range_is_approximate_with_end_time():
    span = time_span("dinner with a client from 7:00 PM until about 9:30 PM.", D)
    assert span.start == datetime(2026, 3, 12, 19, 0)
    assert span.end == datetime(2026, 3, 12, 21, 30)
    assert span.approximate
    exact = time_span("From 7 PM to 8 PM I was on a video call", D)
    assert exact.end == datetime(2026, 3, 12, 20, 0) and not exact.approximate


def test_relative_days_shift_the_date():
    assert time_span("When I arrived at 8:45 the next morning", D).start == datetime(2026, 3, 13, 8, 45)
    assert time_span("for the 10 AM demo tomorrow", D).start == datetime(2026, 3, 13, 10, 0)
    # 2026-03-11 is a Wednesday, so "on Friday" is 2026-03-13.
    assert time_span("cleared out on Friday at 5 PM", date(2026, 3, 11)).start == datetime(2026, 3, 13, 17, 0)


def test_full_timestamps_override_document_date():
    times = find_times("2026-03-13 08:40 | Daniel Okafor | Main Entrance | ENTRY", D)
    assert len(times) == 1
    assert times[0].time == datetime(2026, 3, 13, 8, 40) and times[0].explicit_date


def test_midnight_ends_the_day():
    span = time_span("I was at Celia's flat from 8 PM until midnight.", date(2026, 9, 18))
    assert span.start == datetime(2026, 9, 18, 20, 0) and span.end == datetime(2026, 9, 19, 0, 0)
