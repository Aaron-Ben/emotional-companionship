"""Diary assessment service for evaluating if conversations are worth recording."""

from typing import Dict, Any


class DiaryAssessmentService:
    """Service for diary assessment - independent from chat system"""

    def get_diary_assessment_tool(self) -> Dict[str, Any]:
        """
        Get the function calling tool definition for diary assessment.

        This tool allows the AI to assess whether a conversation is worth recording
        while generating the chat response, all in one LLM call.

        Returns:
            Function calling tool definition for diary assessment
        """
        return {
            "type": "function",
            "function": {
                "name": "assess_diary_worthiness",
                "description": "评估本次对话是否值得写进日记",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "should_record": {
                            "type": "boolean",
                            "description": "是否应该记录到日记"
                        },
                        "reason": {
                            "type": "string",
                            "description": "判断的具体原因"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["knowledge", "topic", "emotional", "milestone", "none"],
                            "description": "对话分类"
                        },
                        "key_points": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "需要记录的关键点"
                        }
                    },
                    "required": ["should_record", "category"]
                }
            }
        }

    def build_assessment_prompt(self) -> str:
        """
        Build the assessment prompt to add to the chat system prompt.

        This provides guidance to the AI on how to judge whether a conversation
        is worth recording in the diary. This is separate from the character's
        personality prompt to avoid interference.

        Returns:
            String containing the diary assessment instructions
        """
        return """

## 日记系统


### 日记的核心价值

日记的主要功能是**学习和反思**，不要盲目写日记。仅当以下情况发生时才记录：

1. **学到新知识**（knowledge）
   - 用户分享了新的技能、技术、概念
   - 例如：学习了编程技巧、了解了一个新领域、掌握了某个工具

2. **有价值的话题讨论**（topic）
   - 关于生活、工作、感情的深入探讨
   - 例如：职业规划思考、人生方向讨论、重要决策分析

3. **重要情绪时刻**（emotional）
   - 强烈的情绪表达或情感交流
   - 例如：极度开心、难过、焦虑、兴奋的时刻

4. **重要里程碑事件**（milestone）
   - 人生节点和成就
   - 例如：升职加薪、项目完成、生日纪念

### 不值得记录的情况

- 简单打招呼（"你好"、"在吗"）
- 日常寒暄无实质内容（"好的"、"嗯"、"知道了"）
- 重复性对话
- 琐碎小事

### 判断原则

**注重质量而非数量**，不是每次对话都要写日记。当判断值得记录时，调用 `assess_diary_worthiness` 工具提供：
- `should_record`: true/false
- `reason`: 简短说明为什么值得记录
- `category`: 选择最合适的分类（knowledge/topic/emotional/milestone/none）
- `key_points`: 2-4个必须记录的关键点或关键词

如果不值得记录，仍然调用工具，但设置 `should_record: false`。
"""
