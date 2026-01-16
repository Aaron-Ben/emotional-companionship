"""Diary trigger mechanisms for detecting when to generate diary entries."""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.diary import DiaryTriggerType
from app.schemas.message import EmotionState


class EventDetector:
    """重要事件检测器"""

    IMPORTANT_KEYWORDS = {
        "career": ["升职", "涨工资", "换工作", "辞职", "面试", "项目", "加班"],
        "life": ["搬家", "买房", "买车", "结婚", "分手", "旅行"],
        "health": ["生病", "手术", "康复", "体检", "医院"],
        "achievement": ["成功", "完成", "获奖", "通过", "及格"],
        "family": ["家人", "父母", "生日", "节日", "纪念日"],
        "study": ["考试", "毕业", "论文", "成绩"]
    }

    @classmethod
    def detect_important_event(cls, message: str, emotion: Optional[EmotionState] = None) -> bool:
        """
        检测是否为重要事件

        Args:
            message: 用户消息
            emotion: 检测到的情绪（可选）

        Returns:
            bool: 是否为重要事件
        """
        # 高强度情绪
        if emotion and hasattr(emotion, 'intensity') and emotion.intensity > 0.8:
            return True

        # 关键词匹配
        message_lower = message.lower()
        for category, keywords in cls.IMPORTANT_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return True

        return False

    @classmethod
    def extract_event_type(cls, message: str) -> str:
        """从消息中提取事件类型"""
        message_lower = message.lower()
        for category, keywords in cls.IMPORTANT_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return category
        return "general"


class EmotionFluctuationDetector:
    """情绪波动检测器"""

    def __init__(self, window_size: int = 5):
        """
        初始化检测器

        Args:
            window_size: 检测窗口大小（最近几次对话）
        """
        self.window_size = window_size
        self.emotion_history: List[Optional[EmotionState]] = []

    def add_emotion(self, emotion: Optional[EmotionState]):
        """添加情绪记录"""
        if emotion is not None:
            self.emotion_history.append(emotion)
            # 保持窗口大小
            if len(self.emotion_history) > self.window_size:
                self.emotion_history.pop(0)

    def detect_fluctuation(self) -> bool:
        """
        检测是否有显著情绪波动

        Returns:
            bool: 是否有明显波动
        """
        if len(self.emotion_history) < 3:
            return False

        # 计算情绪强度的方差
        intensities = []
        for e in self.emotion_history:
            if hasattr(e, 'intensity'):
                intensities.append(e.intensity)

        if not intensities:
            return False

        avg_intensity = sum(intensities) / len(intensities)

        # 如果有情绪强度超过平均值 0.3 的波动
        for intensity in intensities:
            if abs(intensity - avg_intensity) > 0.3:
                return True

        # 检查情绪类型变化
        emotions = []
        for e in self.emotion_history:
            if hasattr(e, 'primary_emotion'):
                emotions.append(e.primary_emotion)

        unique_emotions = set(emotions)

        # 如果最近3次对话中出现了3种不同情绪
        if len(unique_emotions) >= 3:
            return True

        return False

    def should_trigger_diary(self) -> bool:
        """
        判断是否应该触发日记记录

        Returns:
            bool: 是否应该记录
        """
        return self.detect_fluctuation()

    def reset(self):
        """重置历史记录"""
        self.emotion_history = []


class DailySummaryChecker:
    """定期总结检查器"""

    def __init__(self):
        """初始化检查器"""
        self.conversation_count = 0
        self.last_summary_date = None

    def add_conversation(self):
        """记录一次对话"""
        self.conversation_count += 1

    def should_generate_summary(self) -> bool:
        """
        判断是否应该生成每日总结

        触发条件：
        1. 对话次数 >= 5次
        2. 或者晚上10点后且有对话
        3. 或者今天还没有总结且满足条件

        Returns:
            bool: 是否应该生成总结
        """
        # 检查对话次数
        if self.conversation_count >= 5:
            return True

        # 检查时间
        current_hour = datetime.now().hour
        if current_hour >= 22 and self.conversation_count > 0:
            return True

        return False

    def reset_daily_count(self):
        """重置每日计数"""
        self.conversation_count = 0
        self.last_summary_date = datetime.now().strftime("%Y-%m-%d")


class DiaryTriggerManager:
    """日记触发管理器：整合所有触发机制"""

    def __init__(self):
        """初始化触发管理器"""
        self.event_detector = EventDetector()
        self.emotion_detector = EmotionFluctuationDetector()
        self.summary_checker = DailySummaryChecker()

    async def check_triggers(
        self,
        message: str,
        emotion: Optional[EmotionState] = None
    ) -> List[DiaryTriggerType]:
        """
        检查所有触发条件

        Args:
            message: 当前消息
            emotion: 当前情绪（可选）

        Returns:
            触发的触发类型列表
        """
        triggers = []

        # 检查重要事件
        if self.event_detector.detect_important_event(message, emotion):
            triggers.append(DiaryTriggerType.IMPORTANT_EVENT)

        # 检查情绪波动
        self.emotion_detector.add_emotion(emotion)
        if self.emotion_detector.should_trigger_diary():
            triggers.append(DiaryTriggerType.EMOTIONAL_FLUCTUATION)

        # 检查定期总结
        self.summary_checker.add_conversation()
        if self.summary_checker.should_generate_summary():
            triggers.append(DiaryTriggerType.DAILY_SUMMARY)

        return triggers

    def reset_daily(self):
        """重置每日计数器"""
        self.summary_checker.reset_daily_count()

    def reset_emotion_history(self):
        """重置情绪历史"""
        self.emotion_detector.reset()
