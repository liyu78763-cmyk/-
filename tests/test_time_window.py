from __future__ import annotations

from datetime import timedelta

from crossborder_daily.time_utils import chinese_headline_date, in_window, window_start


def test_date_range_uses_beijing_time() -> None:
    from tests.conftest import bjt

    now = bjt()
    since = window_start(now, 24)

    assert in_window(now - timedelta(hours=23, minutes=59), since, now)
    assert not in_window(now - timedelta(hours=24, minutes=1), since, now)
    assert chinese_headline_date(now) == "6.26 星期五 核心要闻速览"
