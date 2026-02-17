# 🤖 Automation Scripts - SmartShop AI

## 📋 Overview

This folder contains automation scripts for the SmartShop AI development workflow. These scripts handle Jira synchronization, progress tracking, and workflow automation.

---

## 📂 Scripts

### **jira_client.py**
Core Jira API client and utilities for interacting with Jira Cloud.

**Functions:**
- `JiraClient.get_story()` - Fetch story details
- `JiraClient.transition_story()` - Change story status
- `JiraClient.add_comment()` - Add comments to stories
- `JiraClient.update_story_fields()` - Update custom fields
- `load_progress_file()` - Load progress JSON
- `save_progress_file()` - Save progress JSON

**Usage:**
```python
from automation.jira_client import JiraClient

jira = JiraClient()
jira.transition_story("SCRUM-6", "In Progress")
jira.add_comment("SCRUM-6", "Work started!")
```

---

### **start_story.py**
Initialize story execution and create progress tracking.

**What it does:**
1. Transitions Jira story to "In Progress"
2. Creates `.progress/current-story.json`
3. Adds start comment to Jira
4. Auto-detects plan file if not provided

**Usage:**
```bash
# Auto-detect plan file
python automation/start_story.py SCRUM-6

# Specify plan file explicitly
python automation/start_story.py SCRUM-6 --plan plans/phase-1/SCRUM-6-database-schema.md
```

**Output:**
- Creates `.progress/current-story.json`
- Updates Jira status and adds comment
- Logs initialization details

---

### **complete_story.py**
Finalize story execution and update Jira.

**What it does:**
1. Validates story completion
2. Generates completion summary
3. Adds completion comment to Jira
4. Transitions story to "Done"
5. Archives to `.progress/completed-tasks.json`
6. Removes `.progress/current-story.json`

**Usage:**
```bash
# Complete story (with validation)
python automation/complete_story.py SCRUM-6

# Force complete (skip validation)
python automation/complete_story.py SCRUM-6 --force
```

**Validation Checks:**
- No critical issues unresolved
- All tasks marked as completed
- Progress file exists and is valid

---

## 🔄 Workflow Integration

### **For Claude Code in VS Code**

Claude Code should integrate these scripts during plan execution:

#### **1. Before Starting Plan Execution**
```python
# In Claude Code execution logic:
!python automation/start_story.py SCRUM-6
```

This initializes tracking and updates Jira to "In Progress".

#### **2. During Plan Execution**
Update progress as tasks complete:

```python
import json

# Load current progress
with open('.progress/current-story.json', 'r') as f:
    progress = json.load(f)

# Add completed task
progress['tasks'].append({
    'name': 'Create Product model',
    'status': 'completed',
    'completed_at': datetime.utcnow().isoformat() + 'Z'
})
progress['last_updated'] = datetime.utcnow().isoformat() + 'Z'

# Save updated progress
with open('.progress/current-story.json', 'w') as f:
    json.dump(progress, f, indent=2)
```

#### **3. After Plan Execution Completes**
```python
# In Claude Code execution logic:
!python automation/complete_story.py SCRUM-6
```

This finalizes the story and updates Jira to "Done".

---

## 📊 Progress Tracking Files

### **.progress/current-story.json**
Active story being worked on.

**Structure:**
```json
{
  "story_id": "SCRUM-6",
  "story_title": "Design and implement PostgreSQL database schema",
  "plan_file": "plans/phase-1/SCRUM-6-database-schema.md",
  "status": "in_progress",
  "tasks": [
    {
      "name": "Create Product model",
      "status": "completed",
      "completed_at": "2026-02-15T18:30:00Z"
    },
    {
      "name": "Create Review model",
      "status": "in_progress",
      "completed_at": null
    }
  ],
  "started_at": "2026-02-15T18:00:00Z",
  "last_updated": "2026-02-15T18:35:00Z",
  "issues": []
}
```

### **.progress/completed-tasks.json**
History of all completed stories.

**Structure:**
```json
[
  {
    "story_id": "SCRUM-6",
    "story_title": "Design and implement PostgreSQL database schema",
    "plan_file": "plans/phase-1/SCRUM-6-database-schema.md",
    "completed_at": "2026-02-15T21:00:00Z",
    "duration_hours": 3.5,
    "tasks_completed": 8,
    "issues_encountered": 0
  },
  {
    "story_id": "SCRUM-7",
    "...": "..."
  }
]
```

---

## 🔧 Configuration

### **Environment Variables**

Set these in `.env` or system environment:

```bash
# Jira Configuration
JIRA_CLOUD_ID=ba95f5fc-5994-47bc-81e4-161f6a62e829
JIRA_PROJECT_KEY=SCRUM
```

### **Jira Authentication**

The scripts use the Jira MCP connector for authentication. Ensure:
1. Jira MCP connector is installed
2. User is authenticated with Jira Cloud
3. Proper permissions for the SCRUM project

---

## 🐛 Troubleshooting

### **Issue: "No progress file found"**
**Solution:**
- Run `start_story.py` before executing the plan
- Check that `.progress/` folder exists

### **Issue: "Plan file not found"**
**Solution:**
- Ensure plan file exists in `plans/phase-X/` folder
- Use correct naming: `SCRUM-X-description.md`
- Or specify plan path with `--plan` flag

### **Issue: "Failed to transition story in Jira"**
**Solution:**
- Verify Jira credentials are configured
- Check network connectivity
- Ensure user has permission to transition stories
- Story may already be in target status (this is OK)

### **Issue: "Validation failed"**
**Solution:**
- Review validation errors in output
- Fix critical issues
- Or use `--force` flag to complete anyway

---

## 📝 Manual Jira Updates

If automation fails, you can manually update Jira:

### **Transition Story Status:**
1. Go to https://projecttracking.atlassian.net
2. Open story (e.g., SCRUM-6)
3. Click status dropdown → Select "In Progress" or "Done"

### **Add Comment:**
1. Open story in Jira
2. Click "Comment" button
3. Paste completion summary
4. Click "Save"

---

## 🎯 Best Practices

### **1. Always Start Stories Properly**
- Run `start_story.py` before beginning work
- Don't manually create progress files

### **2. Update Progress Regularly**
- Log task completions as you go
- Record any issues encountered
- Keep `last_updated` timestamp current

### **3. Validate Before Completing**
- Let validation run (don't use `--force` unless necessary)
- Fix issues before marking complete
- Ensure all acceptance criteria met

### **4. Review Completion Comments**
- Check Jira comments match actual work done
- Update manually if automation missed something
- Use comments to communicate with team

---

## 🔮 Future Enhancements

Potential improvements for this automation:

1. **Real-time Jira Sync** - Sync after each task, not just start/end
2. **Slack Notifications** - Alert team when stories complete
3. **Time Estimation** - Predict story duration based on historical data
4. **Dependency Checking** - Verify dependencies before starting stories
5. **Test Result Integration** - Include test coverage in completion comments
6. **Code Review Triggers** - Automatically request reviews when stories complete

---

## 📚 Related Documentation

- **Workflow Proposal**: `DEVELOPMENT_WORKFLOW_PROPOSAL.md`
- **Plans Folder**: `plans/README.md`
- **VS Code Guide**: `docs/VSCODE_EXECUTION_GUIDE.md`

---

## ❓ Questions?

If you encounter issues:
1. Check the troubleshooting section above
2. Review log output for error details
3. Verify Jira credentials and permissions
4. Manually verify Jira status if automation fails

For workflow questions, refer to `DEVELOPMENT_WORKFLOW_PROPOSAL.md`.
