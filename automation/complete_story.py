#!/usr/bin/env python3
"""Complete story execution and update Jira."""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.jira_client import JiraClient, load_progress_file, save_progress_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def complete_story(story_id: str, force: bool = False):
    """
    Complete story execution and update Jira.

    Args:
        story_id: Jira issue key (e.g., "SCRUM-6")
        force: If True, complete even if validation fails
    """
    logger.info(f"🎯 Completing story: {story_id}")

    # Load current progress
    progress_file = ".progress/current-story.json"
    progress_data = load_progress_file(progress_file)

    if not progress_data:
        logger.error(f"❌ No progress file found: {progress_file}")
        logger.error("Run start_story.py first to initialize tracking")
        sys.exit(1)

    if progress_data["story_id"] != story_id:
        logger.error(f"❌ Progress file is for {progress_data['story_id']}, not {story_id}")
        sys.exit(1)

    # Validate completion
    if not force and not validate_completion(progress_data):
        logger.error("❌ Story validation failed")
        logger.error("Fix issues or use --force to complete anyway")
        sys.exit(1)

    # Calculate duration
    started_at = datetime.fromisoformat(progress_data["started_at"].replace("Z", ""))
    completed_at = datetime.utcnow()
    duration_hours = (completed_at - started_at).total_seconds() / 3600

    # Initialize Jira client
    jira = JiraClient()

    # Generate completion comment
    comment = generate_completion_comment(progress_data, duration_hours)

    # Add comment to Jira
    logger.info(f"💬 Adding completion comment to {story_id}...")
    jira.add_comment(story_id, comment)

    # Transition story to "Done"
    logger.info(f"✅ Transitioning {story_id} to 'Done'...")
    success = jira.transition_story(story_id, "Done")

    if not success:
        logger.warning("⚠️  Failed to transition story in Jira (continuing anyway)")

    # Archive to completed tasks
    completed_data = {
        "story_id": story_id,
        "story_title": progress_data["story_title"],
        "plan_file": progress_data["plan_file"],
        "completed_at": completed_at.isoformat() + "Z",
        "duration_hours": round(duration_hours, 2),
        "tasks_completed": len(progress_data.get("tasks", [])),
        "issues_encountered": len(progress_data.get("issues", []))
    }

    # Append to completed tasks history
    completed_file = ".progress/completed-tasks.json"
    completed_list = load_progress_file(completed_file) or []
    completed_list.append(completed_data)
    save_progress_file(completed_file, completed_list)

    # Remove current progress file
    Path(progress_file).unlink(missing_ok=True)

    logger.info("=" * 60)
    logger.info("✅ Story completed successfully!")
    logger.info(f"📊 Duration: {duration_hours:.1f} hours")
    logger.info(f"✅ Tasks completed: {completed_data['tasks_completed']}")
    logger.info(f"📝 Jira status: Done")
    logger.info("=" * 60)


def validate_completion(progress_data: dict) -> bool:
    """
    Validate that story is ready for completion.

    Args:
        progress_data: Current progress data

    Returns:
        True if validation passes, False otherwise
    """
    logger.info("🔍 Validating story completion...")

    issues = []

    # Check if any critical issues were logged
    if progress_data.get("issues"):
        critical_issues = [i for i in progress_data["issues"] if i.get("critical")]
        if critical_issues:
            issues.append(f"{len(critical_issues)} critical issue(s) unresolved")

    # Check if tasks were completed
    tasks = progress_data.get("tasks", [])
    if not tasks:
        logger.warning("⚠️  No tasks recorded in progress file")

    incomplete_tasks = [t for t in tasks if t.get("status") != "completed"]
    if incomplete_tasks:
        issues.append(f"{len(incomplete_tasks)} task(s) not marked as completed")

    # Report validation results
    if issues:
        logger.error("❌ Validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False

    logger.info("✅ Validation passed!")
    return True


def generate_completion_comment(progress_data: dict, duration_hours: float) -> str:
    """
    Generate Jira completion comment.

    Args:
        progress_data: Progress data
        duration_hours: Duration in hours

    Returns:
        Formatted completion comment
    """
    tasks_completed = len(progress_data.get("tasks", []))
    issues_count = len(progress_data.get("issues", []))

    # Basic completion message
    comment = f"""
✅ **Story completed successfully!**

## Summary
- ⏱️ **Duration**: {duration_hours:.1f} hours
- ✅ **Tasks Completed**: {tasks_completed}
- 📝 **Plan**: `{progress_data['plan_file']}`

## Completion Details
Story executed using automated Claude Code workflow.

"""

    # Add tasks if available
    if progress_data.get("tasks"):
        comment += "## Tasks Completed\n"
        for i, task in enumerate(progress_data["tasks"], 1):
            status_emoji = "✅" if task.get("status") == "completed" else "⏳"
            comment += f"{i}. {status_emoji} {task.get('name', 'Unknown task')}\n"
        comment += "\n"

    # Add issues if any
    if issues_count > 0:
        comment += f"## Issues Encountered\n"
        comment += f"- {issues_count} issue(s) logged during execution\n"
        comment += "- See `.progress/completed-tasks.json` for details\n\n"

    comment += """
---
🤖 *Automated by SmartShop AI development workflow*
    """.strip()

    return comment


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Complete story execution and update Jira"
    )
    parser.add_argument(
        "story_id",
        help="Jira story ID (e.g., SCRUM-6)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Complete story even if validation fails"
    )

    args = parser.parse_args()

    complete_story(args.story_id, args.force)


if __name__ == "__main__":
    main()
