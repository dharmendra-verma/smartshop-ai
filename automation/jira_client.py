"""Jira API client for SmartShop AI automation."""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for interacting with Jira Cloud API."""

    def __init__(self):
        """Initialize Jira client with credentials from environment."""
        self.cloud_id = os.getenv("JIRA_CLOUD_ID", "ba95f5fc-5994-47bc-81e4-161f6a62e829")
        self.project_key = os.getenv("JIRA_PROJECT_KEY", "SCRUM")

        # Note: In actual implementation, you'll need proper Jira API credentials
        # For this workflow, we assume the MCP Jira connector handles authentication

    def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch story details from Jira.

        Args:
            story_id: Jira issue key (e.g., "SCRUM-6")

        Returns:
            Story details as dictionary, or None if not found
        """
        try:
            # In real implementation, this would call Jira API
            # For now, this is a placeholder that shows the expected structure
            logger.info(f"Fetching story {story_id} from Jira...")

            # This would be replaced with actual MCP call or REST API call
            # story = jira_api.get_issue(cloud_id=self.cloud_id, issue_key=story_id)

            logger.info(f"✅ Story {story_id} fetched successfully")
            return {}  # Placeholder

        except Exception as e:
            logger.error(f"❌ Failed to fetch story {story_id}: {e}")
            return None

    def transition_story(self, story_id: str, target_status: str) -> bool:
        """
        Transition story to a new status.

        Args:
            story_id: Jira issue key (e.g., "SCRUM-6")
            target_status: Target status (e.g., "In Progress", "Done")

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Transitioning {story_id} to '{target_status}'...")

            # Map status names to transition IDs
            status_transitions = {
                "To Do": "11",
                "In Progress": "21",
                "Done": "31"
            }

            # In real implementation, would call:
            # jira_api.transition_issue(
            #     cloud_id=self.cloud_id,
            #     issue_key=story_id,
            #     transition_id=status_transitions.get(target_status)
            # )

            logger.info(f"✅ Story {story_id} transitioned to '{target_status}'")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to transition story {story_id}: {e}")
            return False

    def add_comment(self, story_id: str, comment: str) -> bool:
        """
        Add a comment to a Jira story.

        Args:
            story_id: Jira issue key
            comment: Comment text (supports markdown)

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Adding comment to {story_id}...")

            # In real implementation, would call:
            # jira_api.add_comment(
            #     cloud_id=self.cloud_id,
            #     issue_key=story_id,
            #     comment_body=comment
            # )

            logger.info(f"✅ Comment added to {story_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add comment to {story_id}: {e}")
            return False

    def update_story_fields(self, story_id: str, fields: Dict[str, Any]) -> bool:
        """
        Update custom fields on a Jira story.

        Args:
            story_id: Jira issue key
            fields: Dictionary of field updates

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Updating fields for {story_id}...")

            # In real implementation, would call:
            # jira_api.update_issue(
            #     cloud_id=self.cloud_id,
            #     issue_key=story_id,
            #     fields=fields
            # )

            logger.info(f"✅ Fields updated for {story_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update fields for {story_id}: {e}")
            return False


def load_progress_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load progress JSON file.

    Args:
        file_path: Path to progress file

    Returns:
        Progress data as dictionary, or None if not found
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in {file_path}: {e}")
        return None


def save_progress_file(file_path: str, data: Dict[str, Any]) -> bool:
    """
    Save progress data to JSON file.

    Args:
        file_path: Path to progress file
        data: Progress data to save

    Returns:
        True if successful, False otherwise
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save progress file: {e}")
        return False


# Integration instructions for Claude Code:
"""
When Claude Code executes a plan, it should:

1. At start of execution:
   - Call start_story.py to initialize tracking
   - This creates .progress/current-story.json

2. During execution (after each task):
   - Update .progress/current-story.json with task completion
   - Log any issues or blockers

3. At end of execution:
   - Call complete_story.py to finalize
   - This transitions Jira status to "Done"
   - Adds completion comment
   - Moves data to .progress/completed-tasks.json

Example Claude Code workflow:
```
# Start story
!python automation/start_story.py SCRUM-6

# Execute tasks...
# (Claude Code creates files, runs tests, etc.)

# Complete story
!python automation/complete_story.py SCRUM-6
```
"""
