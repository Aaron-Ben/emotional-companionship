"""AI-driven diary tag generation service.

Simplified from tag_generator.py with external prompt file.
"""

import logging
import re
from pathlib import Path
from typing import List

from app.services.llms.base import LLMBase

logger = logging.getLogger(__name__)


class DiaryTagService:
    """AI-powered tag generator using TagMaster pattern.

    Generates high-density, specific tags (3-5 per diary).
    """

    def __init__(self):
        """Initialize the tag service."""
        self.prompts_dir = Path(__file__).parent / "prompts"

    def _load_prompt(self) -> str:
        """Load tag generation prompt from file.

        Returns:
            Prompt content as string
        """
        prompt_path = self.prompts_dir / "tag_generation.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise

    def generate_tags(self, diary_content: str, category: str, llm: LLMBase) -> List[str]:
        """Generate AI-powered tags for diary.

        Args:
            diary_content: Diary content
            category: Diary category (knowledge/topic/emotional/milestone)
            llm: LLM service instance

        Returns:
            List of generated tags (3-5 tags)
        """
        prompt_template = self._load_prompt()
        prompt = prompt_template.format(
            diary_content=diary_content,
            category=category
        )

        try:
            response = llm.generate_response([
                {"role": "system", "content": prompt},
                {"role": "user", "content": "生成标签"}
            ])

            tags = self._parse_tags(response)
            logger.info(f"Generated tags: {tags}")
            return tags

        except Exception as e:
            logger.error(f"Failed to generate tags: {e}")
            return [category]

    def _parse_tags(self, response: str) -> List[str]:
        """Parse tags from LLM response.

        Args:
            response: LLM response text

        Returns:
            List of parsed tags
        """
        # Try to parse [[Tag: ...]] format
        pattern = r'\[\[Tag:\s*(.*?)\]\]'
        match = re.search(pattern, response, re.DOTALL)

        if match:
            tags_str = match.group(1)
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            return tags[:5]  # Max 5 tags

        # Fallback: extract by line
        lines = response.strip().split('\n')
        tags = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('[') and len(line) < 50:
                tags.append(line)
                if len(tags) >= 5:
                    break

        return tags if tags else [response[:30]]
