"""Time normalizer for converting Chinese relative time expressions to absolute dates."""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from .models import TimeExpressionType


class TimeNormalizer:
    """
    Normalizes Chinese time expressions to absolute dates.

    Supports:
    - 明天, 后天, 大后天
    - 下周, 上周
    - 下个月
    - 3天后, 一周后
    - 1月25日, 2月14日
    """

    # Today's date (can be overridden for testing)
    _today: Optional[datetime] = None

    # Patterns for Chinese time expressions
    PATTERNS = {
        # Relative days
        'tomorrow': re.compile(r'明天'),
        'day_after_tomorrow': re.compile(r'后天'),
        'three_days_later': re.compile(r'(?:大后天|三天后)'),
        'n_days_later': re.compile(r'(\d+)天后?'),
        'today': re.compile(r'(?:今天|今日|今晚|今早|明早)'),
        'morning': re.compile(r'(?:早上|上午|清晨|早间)'),
        'afternoon': re.compile(r'(?:下午|午后|中午)'),
        'evening': re.compile(r'(?:晚上|傍晚|夜间|今晚|今夜)'),
        'later': re.compile(r'(?:一会|一会儿|待会|稍后|回头|改天|改日)'),
        'future': re.compile(r'(?:以后|之后|未来|往后)'),

        # Weeks
        'next_week': re.compile(r'下周'),
        'week_after_next': re.compile(r'下下周|再下周'),
        'n_weeks_later': re.compile(r'(\d+)周后?'),

        # Months
        'next_month': re.compile(r'下个月|下月'),
        'next_year': re.compile(r'明年'),

        # Specific dates
        'month_day': re.compile(r'(\d{1,2})月(\d{1,2})日?'),
        'month_day_with_year': re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日?'),
    }

    # Weekday names in Chinese
    WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

    @classmethod
    def set_today(cls, date: datetime):
        """Set today's date (useful for testing)."""
        cls._today = date

    @classmethod
    def get_today(cls) -> datetime:
        """Get today's date."""
        if cls._today:
            return cls._today
        return datetime.now()

    @classmethod
    def normalize(cls, expression: str) -> Tuple[Optional[str], TimeExpressionType, float]:
        """
        Normalize a Chinese time expression to absolute date.

        Args:
            expression: The time expression to normalize (e.g., "明天下午3点")

        Returns:
            Tuple of (normalized_date, expression_type, confidence)
            - normalized_date: YYYY-MM-DD format, or None if cannot normalize
            - expression_type: Type of the expression
            - confidence: Confidence score (0-1)
        """
        expression = expression.strip()

        # Check for fuzzy time expressions (no specific date)
        for pattern_name, pattern in [
            ('later', cls.PATTERNS['later']),
            ('future', cls.PATTERNS['future']),
        ]:
            if pattern.search(expression):
                return None, TimeExpressionType.FUZZY_TIME, 0.6

        # Check for specific dates with year
        match = cls.PATTERNS['month_day_with_year'].search(expression)
        if match:
            year, month, day = match.groups()
            try:
                date = datetime(int(year), int(month), int(day))
                if date < cls.get_today():
                    return None, TimeExpressionType.SPECIFIC_DATE, 0.3
                return (
                    date.strftime('%Y-%m-%d'),
                    TimeExpressionType.SPECIFIC_DATE,
                    0.95
                )
            except ValueError:
                pass

        # Check for specific dates (month-day, assume current year)
        match = cls.PATTERNS['month_day'].search(expression)
        if match:
            month, day = match.groups()
            try:
                today = cls.get_today()
                date = datetime(today.year, int(month), int(day))

                # If date has passed this year, try next year
                if date < cls.get_today():
                    date = datetime(today.year + 1, int(month), int(day))

                return (
                    date.strftime('%Y-%m-%d'),
                    TimeExpressionType.SPECIFIC_DATE,
                    0.9
                )
            except ValueError:
                pass

        # Check for "n days later"
        match = cls.PATTERNS['n_days_later'].search(expression)
        if match:
            days = int(match.group(1))
            if days > 0 and days <= 365:
                date = cls.get_today() + timedelta(days=days)
                return (
                    date.strftime('%Y-%m-%d'),
                    TimeExpressionType.RELATIVE_DAY,
                    0.85
                )

        # Check for "three days later"
        if cls.PATTERNS['three_days_later'].search(expression):
            date = cls.get_today() + timedelta(days=3)
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_DAY,
                0.9
            )

        # Check for "day after tomorrow"
        if cls.PATTERNS['day_after_tomorrow'].search(expression):
            date = cls.get_today() + timedelta(days=2)
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_DAY,
                0.95
            )

        # Check for "tomorrow"
        if cls.PATTERNS['tomorrow'].search(expression):
            date = cls.get_today() + timedelta(days=1)
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_DAY,
                0.95
            )

        # Check for "today"
        if cls.PATTERNS['today'].search(expression):
            date = cls.get_today()
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_DAY,
                0.95
            )

        # Check for "n weeks later"
        match = cls.PATTERNS['n_weeks_later'].search(expression)
        if match:
            weeks = int(match.group(1))
            if weeks > 0 and weeks <= 52:
                date = cls.get_today() + timedelta(weeks=weeks)
                return (
                    date.strftime('%Y-%m-%d'),
                    TimeExpressionType.RELATIVE_WEEK,
                    0.8
                )

        # Check for "week after next"
        if cls.PATTERNS['week_after_next'].search(expression):
            # Find next Monday, then add 7 more days
            today = cls.get_today()
            days_ahead = 0 - today.weekday() + 7  # Next Monday
            if days_ahead <= 0:
                days_ahead += 7
            date = today + timedelta(days=days_ahead + 7)
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_WEEK,
                0.85
            )

        # Check for "next week" (next Monday)
        if cls.PATTERNS['next_week'].search(expression):
            today = cls.get_today()
            days_ahead = 0 - today.weekday() + 7  # Next Monday
            if days_ahead <= 0:
                days_ahead += 7
            date = today + timedelta(days=days_ahead)
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_WEEK,
                0.85
            )

        # Check for "next month"
        if cls.PATTERNS['next_month'].search(expression):
            today = cls.get_today()
            if today.month == 12:
                date = datetime(today.year + 1, 1, 1)
            else:
                date = datetime(today.year, today.month + 1, 1)
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_MONTH,
                0.8
            )

        # Check for "next year"
        if cls.PATTERNS['next_year'].search(expression):
            today = cls.get_today()
            date = datetime(today.year + 1, 1, 1)
            return (
                date.strftime('%Y-%m-%d'),
                TimeExpressionType.RELATIVE_MONTH,
                0.8
            )

        # Cannot normalize
        return None, TimeExpressionType.FUZZY_TIME, 0.0

    @classmethod
    def format_display_date(cls, date_str: str) -> str:
        """
        Format a date string for display.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Formatted date like "1月26日 周一"
        """
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            month = date.month
            day = date.day
            weekday = cls.WEEKDAYS[date.weekday()]
            return f"{month}月{day}日 {weekday}"
        except ValueError:
            return date_str

    @classmethod
    def is_future_date(cls, date_str: str) -> bool:
        """
        Check if a date is in the future.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            True if date is in the future, False otherwise
        """
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            return date > cls.get_today()
        except ValueError:
            return False
