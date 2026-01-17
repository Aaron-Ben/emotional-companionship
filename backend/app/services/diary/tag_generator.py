"""AI-driven diary tag generation service."""

import logging
from typing import List
from app.services.llms.base import LLMBase

logger = logging.getLogger(__name__)


class DiaryTagGenerator:
    """AI驱动的日记标签生成器 (TagMaster模式)

    参考VCPToolBox项目，使用AI生成高密度、精确的标签。
    """

    def generate_tags(self, diary_content: str, category: str, llm: LLMBase) -> List[str]:
        """
        使用AI生成精确标签

        Args:
            diary_content: 日记内容
            category: 日记分类 (knowledge/topic/emotional/milestone)
            llm: LLM服务实例

        Returns:
            生成的标签列表 (3-5个标签)

        Prompt要求：
        - 输出格式：[[Tag: 标签1, 标签2, 标签3]]
        - 标签要求：高密度、具体、避免泛泛而谈
        - 例如：不是"技术"而是"Python异步编程"
        """
        prompt = self._build_tag_prompt(diary_content, category)

        try:
            response = llm.generate_response([
                {"role": "system", "content": prompt},
                {"role": "user", "content": "生成标签"}
            ])

            # 解析标签
            tags = self._parse_tags(response)
            logger.info(f"Generated tags: {tags}")
            return tags

        except Exception as e:
            logger.error(f"Failed to generate tags: {e}")
            # 降级到简单标签
            return [category]

    def _build_tag_prompt(self, diary_content: str, category: str) -> str:
        """构建标签生成提示词

        Args:
            diary_content: 日记内容
            category: 日记分类

        Returns:
            标签生成提示词
        """
        return f"""你是标签生成专家，负责为日记生成高密度、精确的标签。

## 日记内容

{diary_content}

## 日记分类

{category}

## 标签生成要求

### 核心原则
1. **高密度信息**：每个标签应包含尽可能多的具体信息
2. **避免泛泛而谈**：不要使用过于宽泛的标签
3. **多维度组合**：从不同角度提取标签

### 标签质量对比

**不好的标签（太泛）**：
- 技术、学习、工作、开心、难过

**好的标签（具体）**：
- Python异步编程、FastAPI依赖注入、职场压力管理、升职庆祝

### 不同分类的标签策略

**knowledge类**：
- 优先提取：具体技术/概念
- 示例：不是"编程"而是"Python装饰器模式"

**topic类**：
- 优先提取：核心话题+角度
- 示例：不是"工作"而是"职业规划思考"

**emotional类**：
- 优先提取：情绪触发源+情绪类型
- 示例：不是"开心"而是"涨工资带来的喜悦"

**milestone类**：
- 优先提取：事件类型+意义
- 示例：不是"成就"而是"项目完成里程碑"

### 输出格式

严格按照以下格式输出标签（3-5个）：

[[Tag: 标签1, 标签2, 标签3]]

示例：
[[Tag: Python异步编程, FastAPI依赖注入, 装饰器模式]]

## 开始生成标签

根据上述日记内容和分类，生成精确的标签："""

    def _parse_tags(self, response: str) -> List[str]:
        """解析LLM返回的标签

        Args:
            response: LLM响应文本

        Returns:
            解析出的标签列表
        """
        # 尝试解析 [[Tag: ...]] 格式
        import re
        pattern = r'\[\[Tag:\s*(.*?)\]\]'
        match = re.search(pattern, response, re.DOTALL)

        if match:
            tags_str = match.group(1)
            # 分割并清理标签
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            return tags[:5]  # 最多5个标签

        # 降级：按行提取
        lines = response.strip().split('\n')
        tags = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('[') and len(line) < 50:
                tags.append(line)
                if len(tags) >= 5:
                    break

        return tags if tags else [response[:30]]
