"""Skills loader - loads and manages skills from SKILL.md files."""

import shutil
from pathlib import Path
from typing import Optional
import logging

import yaml

logger = logging.getLogger(__name__)

# Default builtin skills directory
BUILTIN_SKILLS_DIR = Path(__file__).parent / "builtin"


class SkillMetadata:
    """Represents parsed skill metadata from frontmatter."""

    def __init__(self, name: str, description: str, homepage: str = "", metadata: dict = None):
        self.name = name
        self.description = description
        self.homepage = homepage
        self.metadata = metadata or {}
        self.nanobot = self.metadata.get("nanobot", {})

        # Extract nanobot-specific fields
        self.emoji = self.nanobot.get("emoji", "")
        self.requires = self.nanobot.get("requires", {})
        self.bins = self.requires.get("bins", [])
        self.env = self.requires.get("env", [])
        self.always = self.nanobot.get("always", False)
        self.install = self.nanobot.get("install", "")


class SkillsLoader:
    """Loads and manages skills from SKILL.md files.

    Supports two sources:
    - Builtin skills: package's built-in skills directory
    - Workspace skills: user's workspace/skills directory (not implemented yet)
    """

    def __init__(self, builtin_skills_dir: Optional[Path] = None):
        """
        Initialize SkillsLoader.

        Args:
            builtin_skills_dir: Path to builtin skills directory. Defaults to package builtin.
        """
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR
        logger.info(f"[Skills] Builtin skills directory: {self.builtin_skills}")

    def list_skills(self) -> list[dict]:
        """
        List all available skills with their metadata.

        Returns:
            List of skill info dicts: name, description, available, location, requires
        """
        skills = []
        if not self.builtin_skills.exists():
            logger.warning(f"[Skills] Builtin skills directory not found: {self.builtin_skills}")
            return skills

        for skill_dir in self.builtin_skills.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            metadata = self.get_skill_metadata(skill_file)
            if not metadata:
                continue

            available = self._check_requirements(metadata)
            skills.append({
                "name": metadata.name,
                "description": metadata.description,
                "available": available,
                "location": str(skill_file),
                "requires": self._format_requires(metadata),
            })

        return skills

    def load_skill(self, name: str) -> Optional[str]:
        """
        Load the full content of a skill by name.

        Args:
            name: Skill name (directory name)

        Returns:
            Full SKILL.md content or None if not found
        """
        skill_file = self.builtin_skills / name / "SKILL.md"
        if not skill_file.exists():
            logger.warning(f"[Skills] Skill not found: {name}")
            return None

        try:
            return skill_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"[Skills] Failed to read skill {name}: {e}")
            return None

    def get_always_skills(self) -> list[str]:
        """
        Get list of skill names that have always=true.

        Returns:
            List of skill names to always load
        """
        always = []
        for skill_info in self.list_skills():
            metadata = self.get_skill_metadata(Path(skill_info["location"]))
            if metadata and metadata.always:
                always.append(metadata.name)
        return always

    def load_skills_for_context(self, skill_names: Optional[list[str]] = None) -> str:
        """
        Load full content of specified skills for context injection.

        Args:
            skill_names: List of skill names to load. If None, loads always skills.

        Returns:
            Combined skill content formatted for system prompt
        """
        if skill_names is None:
            skill_names = self.get_always_skills()

        if not skill_names:
            return ""

        parts = []
        for name in skill_names:
            content = self.load_skill(name)
            if content:
                # Remove frontmatter from displayed content
                content = self._strip_frontmatter(content)
                parts.append(f"## Skill: {name}\n\n{content}")

        return "\n\n".join(parts)

    def build_skills_summary(self) -> str:
        """
        Build XML-formatted summary of all available skills.

        Returns:
            XML string with skill summaries
        """
        skills = self.list_skills()
        if not skills:
            return ""

        lines = ['<skills>']
        for skill in skills:
            available_str = "true" if skill["available"] else "false"
            lines.append(f'  <skill available="{available_str}">')
            lines.append(f'    <name>{skill["name"]}</name>')
            lines.append(f'    <description>{skill["description"]}</description>')
            lines.append(f'    <location>{skill["location"]}</location>')
            if skill["requires"]:
                lines.append(f'    <requires>{skill["requires"]}</requires>')
            lines.append('  </skill>')
        lines.append('</skills>')

        return "\n".join(lines)

    def get_skill_metadata(self, skill_file: Path) -> Optional[SkillMetadata]:
        """
        Parse metadata from SKILL.md frontmatter.

        Args:
            skill_file: Path to SKILL.md file

        Returns:
            SkillMetadata object or None if parsing fails
        """
        if not skill_file.exists():
            return None

        try:
            content = skill_file.read_text(encoding="utf-8")
            return self._parse_frontmatter(content)
        except Exception as e:
            logger.error(f"[Skills] Failed to parse {skill_file}: {e}")
            return None

    def _parse_frontmatter(self, content: str) -> Optional[SkillMetadata]:
        """Parse YAML frontmatter from skill content."""
        lines = content.split("\n")
        if not lines or lines[0].strip() != "---":
            return None

        # Find closing ---
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx is None:
            return None

        # Parse YAML
        yaml_str = "\n".join(lines[1:end_idx])
        try:
            data = yaml.safe_load(yaml_str)
            return SkillMetadata(
                name=data.get("name", ""),
                description=data.get("description", ""),
                homepage=data.get("homepage", ""),
                metadata=data.get("metadata", {})
            )
        except yaml.YAMLError:
            logger.warning(f"[Skills] Invalid YAML frontmatter")
            return None

    def _strip_frontmatter(self, content: str) -> str:
        """Remove frontmatter from skill content for display."""
        lines = content.split("\n")
        if not lines or lines[0].strip() != "---":
            return content

        # Find closing ---
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])

        return content

    def _check_requirements(self, metadata: SkillMetadata) -> bool:
        """Check if skill requirements are met (bins/env)."""
        # Check binary dependencies
        for bin_name in metadata.bins:
            if not shutil.which(bin_name):
                logger.warning(f"[Skills] Missing required binary: {bin_name}")
                return False

        # Check environment variables
        import os
        for env_var in metadata.env:
            if not os.getenv(env_var):
                logger.warning(f"[Skills] Missing required env var: {env_var}")
                return False

        return True

    def _format_requires(self, metadata: SkillMetadata) -> str:
        """Format requirements for display."""
        parts = []
        if metadata.bins:
            parts.append(f"CLI: {', '.join(metadata.bins)}")
        if metadata.env:
            parts.append(f"Env: {', '.join(metadata.env)}")
        return " | ".join(parts) if parts else ""


# Singleton instance
_skills_loader: Optional[SkillsLoader] = None


def get_skills_loader() -> SkillsLoader:
    """Get the global SkillsLoader instance."""
    global _skills_loader
    if _skills_loader is None:
        _skills_loader = SkillsLoader()
    return _skills_loader