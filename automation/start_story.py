#!/usr/bin/env python3
"""Initialize story execution and start progress tracking."""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.jira_client import JiraClient, save_progress_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def start_story(story_id: str, plan_file: str = None):
    """
    Initialize story execution.

    Args:
        story_id: Jira issue key (e.g., "SCRUM-6")
        plan_file: Path to plan file (optional, auto-detected if not provided)
    """
    logger.info(f"🚀 Starting story: {story_id}")

    # Auto-detect plan file if not provided
    if not plan_file:
        plan_file = find_plan_file(story_id)
        if not plan_file:
            logger.error(f"❌ Plan file not found for {story_id}")
            logger.error("Please provide plan file path or ensure it exists in plans/ folder")
            sys.exit(1)

    logger.info(f"📄 Plan file: {plan_file}")

    # Initialize Jira client
    jira = JiraClient()

    # Transition story to "In Progress"
    logger.info(f"📝 Transitioning {story_id} to 'In Progress'...")
    success = jira.transition_story(story_id, "In Progress")

    if not success:
        logger.warning("⚠️  Failed to transition story in Jira (continuing anyway)")

    # Create progress tracking file
    progress_data = {
        "story_id": story_id,
        "story_title": extract_title_from_plan(plan_file),
        "plan_file": plan_file,
        "status": "in_progress",
        "tasks": [],  # Will be populated as tasks are completed
        "started_at": datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "issues": []
    }

    # Save to .progress/current-story.json
    progress_file = ".progress/current-story.json"
    if save_progress_file(progress_file, progress_data):
        logger.info(f"✅ Progress tracking initialized: {progress_file}")
    else:
        logger.error(f"❌ Failed to create progress file: {progress_file}")
        sys.exit(1)

    # Add comment to Jira
    comment = f"""
🚀 **Story execution started**

📄 **Plan**: `{plan_file}`
⏰ **Started**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
🤖 **Automation**: Claude Code workflow

---
_This story is being executed automatically using the structured development workflow._
    """.strip()

    jira.add_comment(story_id, comment)

    logger.info("=" * 60)
    logger.info("✅ Story initialization complete!")
    logger.info(f"📊 Track progress in: {progress_file}")
    logger.info(f"🎯 Execute plan: {plan_file}")
    logger.info("=" * 60)


def find_plan_file(story_id: str) -> str:
    """
    Auto-detect plan file for a story.

    Args:
        story_id: Jira issue key (e.g., "SCRUM-6")

    Returns:
        Path to plan file, or None if not found
    """
    plans_dir = Path("plans")

    # Search all phase folders
    for phase_dir in plans_dir.glob("phase-*"):
        # Look for files matching pattern: SCRUM-X-*.md
        pattern = f"{story_id}-*.md"
        matches = list(phase_dir.glob(pattern))

        if matches:
            return str(matches[0].relative_to(Path.cwd()))

    return None


def extract_title_from_plan(plan_file: str) -> str:
    """
    Extract story title from plan file.

    Args:
        plan_file: Path to plan markdown file

    Returns:
        Story title, or default if not found
    """
    try:
        with open(plan_file, 'r') as f:
            first_line = f.readline().strip()
            # Expected format: # Story: SCRUM-X - Title
            if " - " in first_line:
                return first_line.split(" - ", 1)[1]
    except Exception as e:
        logger.warning(f"⚠️  Could not extract title from plan: {e}")

    return "Unknown Story Title"


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Start story execution and initialize progress tracking"
    )
    parser.add_argument(
        "story_id",
        help="Jira story ID (e.g., SCRUM-6)"
    )
    parser.add_argument(
        "--plan",
        help="Path to plan file (auto-detected if not provided)"
    )

    args = parser.parse_args()

    start_story(args.story_id, args.plan)


if __name__ == "__main__":
    main()
