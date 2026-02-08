"""Time expression configuration for parsing natural language time references."""

from typing import Dict, List, Optional, Pattern
import re
from dataclasses import dataclass


@dataclass
class TimeExpression:
    """Parsed time expression result."""
    days: Optional[int] = None
    type: Optional[str] = None
    number: Optional[int] = None


# Chinese number mapping
CHINESE_NUMBERS = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '兩': 2, '两': 2,
}

# Chinese weekday mapping
CHINESE_WEEKDAYS = {
    '一': 0,  # Monday
    '二': 1,  # Tuesday
    '三': 2,  # Wednesday
    '四': 3,  # Thursday
    '五': 4,  # Friday
    '六': 5,  # Saturday
    '日': 6,  # Sunday
    '天': 6,  # Sunday (alternative)
}

# English weekday mapping
ENGLISH_WEEKDAYS = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
}


@dataclass
class PatternRule:
    """Pattern rule for matching time expressions."""
    regex: Pattern[str]
    type: str


TIME_EXPRESSIONS: Dict[str, Dict[str, Dict]] = {
    'zh-CN': {
        'hardcoded': {
            # 基础时间词
            '今天': TimeExpression(days=0),
            '昨天': TimeExpression(days=1),
            '前天': TimeExpression(days=2),
            '大前天': TimeExpression(days=3),

            # 模糊时间词
            '之前': TimeExpression(days=3),  # "之前"通常指代不久前，暂定3天
            '最近': TimeExpression(days=5),
            '前几天': TimeExpression(days=5),
            '前一阵子': TimeExpression(days=15),
            '近期': TimeExpression(days=7),

            # 周/月相关
            '上周': TimeExpression(type='lastWeek'),
            '上个月': TimeExpression(type='lastMonth'),
            '本周': TimeExpression(type='thisWeek'),
            '这周': TimeExpression(type='thisWeek'),
            '本月': TimeExpression(type='thisMonth'),
            '这个月': TimeExpression(type='thisMonth'),
            '月初': TimeExpression(type='thisMonthStart'),  # 例如本月初
            '上个月初': TimeExpression(type='lastMonthStart'),
            '上个月中': TimeExpression(type='lastMonthMid'),
            '上个月末': TimeExpression(type='lastMonthEnd'),
        },
        'patterns': [
            PatternRule(
                regex=re.compile(r'(\d+|[一二三四五六七八九十]+)天前'),
                type='daysAgo'
            ),
            PatternRule(
                regex=re.compile(r'上周([一二三四五六日天])'),
                type='lastWeekday'
            ),
            PatternRule(
                regex=re.compile(r'(\d+|[一二三四五六七八九十]+)周前'),
                type='weeksAgo'
            ),
            PatternRule(
                regex=re.compile(r'(\d+|[一二三四五六七八九十]+)个月前'),
                type='monthsAgo'
            ),
        ]
    },
    'en-US': {
        'hardcoded': {
            'today': TimeExpression(days=0),
            'yesterday': TimeExpression(days=1),
            'recently': TimeExpression(days=5),
            'lately': TimeExpression(days=7),
            'a while ago': TimeExpression(days=15),
            'last week': TimeExpression(type='lastWeek'),
            'last month': TimeExpression(type='lastMonth'),
            'this week': TimeExpression(type='thisWeek'),
            'this month': TimeExpression(type='thisMonth'),
        },
        'patterns': [
            PatternRule(
                regex=re.compile(r'(\d+) days?\s+ago', re.IGNORECASE),
                type='daysAgo'
            ),
            PatternRule(
                regex=re.compile(r'last (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', re.IGNORECASE),
                type='lastWeekday'
            ),
            PatternRule(
                regex=re.compile(r'(\d+) weeks?\s+ago', re.IGNORECASE),
                type='weeksAgo'
            ),
            PatternRule(
                regex=re.compile(r'(\d+) months?\s+ago', re.IGNORECASE),
                type='monthsAgo'
            ),
        ]
    }
}


def parse_chinese_number(text: str) -> Optional[int]:
    """Parse Chinese number characters to integer."""
    if text.isdigit():
        return int(text)

    # Handle simple Chinese numbers
    if text in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[text]

    # Handle compound numbers like "十一", "二十三"
    if '十' in text:
        if text == '十':
            return 10
        elif text.startswith('十'):
            # "十一" -> 11, "十二" -> 12
            rest = text[1:]
            return 10 + CHINESE_NUMBERS.get(rest, 0)
        elif text.endswith('十'):
            # "二十" -> 20, "三十" -> 30
            prefix = text[0]
            return CHINESE_NUMBERS.get(prefix, 0) * 10
        else:
            # "二十三" -> 23
            prefix = text[0]
            rest = text[2:]  # after '十'
            return CHINESE_NUMBERS.get(prefix, 0) * 10 + CHINESE_NUMBERS.get(rest, 0)

    return None


def get_time_expressions(locale: str = 'zh-CN') -> Dict:
    """
    Get time expressions configuration for a specific locale.

    Args:
        locale: Locale string (e.g., 'zh-CN', 'en-US')

    Returns:
        Dictionary with 'hardcoded' and 'patterns' keys
    """
    return TIME_EXPRESSIONS.get(locale, TIME_EXPRESSIONS['zh-CN'])
