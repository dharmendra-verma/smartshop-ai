# 📘 VS Code Execution Guide - SmartShop AI

## 🎯 Overview

This guide explains how to execute SmartShop AI development plans using Claude Code in VS Code. The workflow enables **automated story execution** with minimal manual intervention.

---

## 🏗️ Prerequisites

### **1. Software Requirements**
- **VS Code** installed (latest version recommended)
- **Claude Code CLI** installed and configured
- **Python 3.10+** in your PATH
- **Git** for version control

### **2. Project Setup**
- Project cloned/located at: `C:\Users\to_dh\AppData\Roaming\Claude\Working\smartshop-ai`
- All dependencies installed: `pip install -r requirements.txt`
- `.env` file configured with proper credentials

### **3. Jira Configuration**
- Jira MCP connector configured
- Authenticated with projecttracking.atlassian.net
- Access to SCRUM project

---

## 🔄 Workflow Overview

```
┌──────────────────────────────────────┐
│  1. Open VS Code in Project Folder  │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│  2. Start Claude Code Session        │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│  3. Tell Claude Code to Execute Plan │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│  4. Claude Code Executes Automatically│
│     - Initializes tracking           │
│     - Creates files                  │
│     - Runs tests                     │
│     - Updates progress               │
│     - Finalizes story                │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│  5. Review Results & Jira Updates    │
└──────────────────────────────────────┘
```

---

## 📋 Step-by-Step Execution

### **Step 1: Open Project in VS Code**

#### **Option A: From Command Line**
```bash
cd C:\Users\to_dh\AppData\Roaming\Claude\Working\smartshop-ai
code .
```

#### **Option B: From VS Code**
1. Open VS Code
2. File → Open Folder
3. Navigate to smartshop-ai folder
4. Click "Select Folder"

---

### **Step 2: Start Claude Code**

#### **Option A: Using Command Palette**
1. Press `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
2. Type "Claude Code"
3. Select "Claude Code: Start Session"

#### **Option B: Using Terminal**
1. Open integrated terminal in VS Code: `` Ctrl+` ``
2. Run: `claude-code`

#### **Option C: Using Keyboard Shortcut**
- If configured, use your custom Claude Code shortcut

**Expected Output:**
```
Claude Code v1.x.x
Connected to project: smartshop-ai
Ready for commands.
```

---

### **Step 3: Execute a Plan**

#### **Command Format**
```
Execute plan [path-to-plan-file]
```

or

```
Execute SCRUM-[number]
```

#### **Example Commands**

**Execute by Plan Path:**
```
Execute plan plans/phase-1/SCRUM-6-database-schema.md
```

**Execute by Story ID (auto-detects plan):**
```
Execute SCRUM-6
```

**Execute with Options:**
```
Execute SCRUM-6 --verbose
Execute SCRUM-6 --skip-tests (not recommended)
```

---

### **Step 4: Monitor Execution**

Claude Code will automatically:

#### **Phase 1: Initialization**
```
🚀 Starting story: SCRUM-6
📄 Reading plan: plans/phase-1/SCRUM-6-database-schema.md
📝 Transitioning Jira to 'In Progress'
✅ Progress tracking initialized
```

#### **Phase 2: Task Execution**
```
📋 Task 1/8: Create SQLAlchemy Product Model
   ✅ Created: app/models/product.py
   ✅ Updated: app/models/__init__.py
   ✅ Tests passed: 6/6

📋 Task 2/8: Create SQLAlchemy Review Model
   ✅ Created: app/models/review.py
   ✅ Tests passed: 5/5

[... continues for all tasks ...]
```

#### **Phase 3: Validation**
```
🔍 Running validation checks...
   ✅ All files created
   ✅ Tests passing (94% coverage)
   ✅ No linting errors
   ✅ Acceptance criteria met
```

#### **Phase 4: Completion**
```
🎯 Completing story: SCRUM-6
💬 Adding completion comment to Jira
✅ Transitioning to 'Done'
📊 Duration: 3.2 hours
✅ Story SCRUM-6 completed successfully!
```

---

### **Step 5: Review Results**

#### **Check Local Files**
Review created/modified files in VS Code:
- Open Explorer panel
- Check files mentioned in execution log
- Review test files
- Check `.progress/completed-tasks.json`

#### **Check Jira Updates**
1. Open browser to: https://projecttracking.atlassian.net/browse/SCRUM-6
2. Verify status is "Done"
3. Read completion comment
4. Check all acceptance criteria are met

#### **Check Tests**
```bash
# Run tests manually if needed
pytest tests/ -v --cov=app
```

---

## 🛠️ Common Commands

### **Plan Execution Commands**

```bash
# Execute single story
Execute SCRUM-6

# Execute with verbose logging
Execute SCRUM-6 --verbose

# Execute specific plan file
Execute plan plans/phase-1/SCRUM-6-database-schema.md

# Dry run (show what would be done, don't execute)
Execute SCRUM-6 --dry-run
```

### **Progress Tracking Commands**

```bash
# Check current story status
Check progress

# View completed stories
Show completed stories

# View current story details
Show current story
```

### **Testing Commands**

```bash
# Run all tests
Run tests

# Run tests for specific module
Run tests for models

# Run tests with coverage
Run tests with coverage

# Run specific test file
Run tests/test_models/test_product.py
```

### **Code Quality Commands**

```bash
# Run linter
Lint code

# Format code
Format code with black

# Type check
Run mypy

# Full code quality check
Run code quality checks
```

---

## 📊 Progress Tracking

### **Real-Time Progress Files**

#### **.progress/current-story.json**
Track active story progress:
```json
{
  "story_id": "SCRUM-6",
  "status": "in_progress",
  "tasks": [
    {"name": "Create Product model", "status": "completed"},
    {"name": "Create Review model", "status": "in_progress"}
  ],
  "last_updated": "2026-02-15T18:45:00Z"
}
```

#### **.progress/completed-tasks.json**
History of completed stories:
```json
[
  {
    "story_id": "SCRUM-6",
    "completed_at": "2026-02-15T21:00:00Z",
    "duration_hours": 3.2,
    "tasks_completed": 8
  }
]
```

### **View Progress in VS Code**

**Option 1: Open Progress Files**
- Open `.progress/current-story.json` in VS Code
- Watch file for live updates

**Option 2: Terminal Commands**
```bash
# Watch progress file (Windows PowerShell)
Get-Content .progress\current-story.json -Wait

# Watch progress file (Git Bash)
tail -f .progress/current-story.json
```

---

## 🚨 Troubleshooting

### **Issue: "Plan file not found"**

**Symptoms:**
```
❌ Error: Plan file not found for SCRUM-6
```

**Solutions:**
1. Verify plan exists: `ls plans/phase-1/SCRUM-6-*.md`
2. Specify full path: `Execute plan plans/phase-1/SCRUM-6-database-schema.md`
3. Check naming convention matches: `SCRUM-X-description.md`

---

### **Issue: "Tests failing during execution"**

**Symptoms:**
```
❌ Task 3 failed: Tests did not pass (2/5 failed)
```

**Solutions:**
1. Review test output for error details
2. Check if dependencies are installed
3. Verify database configuration
4. Run tests manually: `pytest tests/test_models/test_product.py -v`
5. Fix issues and run: `Resume execution`

---

### **Issue: "Jira connection failed"**

**Symptoms:**
```
⚠️  Failed to transition story in Jira (continuing anyway)
```

**Solutions:**
1. Check internet connectivity
2. Verify Jira MCP connector is authenticated
3. Check project permissions
4. Execution continues, but manual Jira update needed later

**Manual Jira Update:**
```bash
# After fixing connection:
python automation/complete_story.py SCRUM-6
```

---

### **Issue: "Import errors / Module not found"**

**Symptoms:**
```
❌ ImportError: No module named 'sqlalchemy'
```

**Solutions:**
1. Activate virtual environment:
   ```bash
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Verify Python interpreter in VS Code:
   - `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Choose venv interpreter

---

### **Issue: "Progress file corrupted"**

**Symptoms:**
```
❌ Invalid JSON in .progress/current-story.json
```

**Solutions:**
1. Backup corrupted file:
   ```bash
   copy .progress\current-story.json .progress\current-story.json.backup
   ```
2. Manually fix JSON syntax, or
3. Delete and restart:
   ```bash
   del .progress\current-story.json
   python automation/start_story.py SCRUM-6
   ```

---

## 🎯 Best Practices

### **1. One Story at a Time**
- ✅ Complete current story before starting next
- ❌ Don't run multiple stories in parallel
- ❌ Don't interrupt execution midway

### **2. Review Before Executing**
- ✅ Read the plan file first
- ✅ Understand acceptance criteria
- ✅ Check for dependencies
- ✅ Ensure all prerequisites met

### **3. Monitor Execution**
- ✅ Watch Claude Code output
- ✅ Check progress files periodically
- ✅ Review test results as they appear
- ✅ Note any warnings or issues

### **4. Verify Completion**
- ✅ Check all files created
- ✅ Run tests manually if needed
- ✅ Verify Jira updated
- ✅ Review acceptance criteria

### **5. Keep Plans Updated**
- ✅ Update plans if implementation differs
- ✅ Note learnings for future stories
- ✅ Track technical debt discovered
- ✅ Document optimization opportunities

---

## 📚 Example Session

Here's a complete example of executing SCRUM-6:

### **Session Start**
```
> cd C:\Users\to_dh\AppData\Roaming\Claude\Working\smartshop-ai
> code .
[VS Code opens]
> [Ctrl+Shift+P] → "Claude Code: Start Session"

Claude Code v1.5.0
Connected to: smartshop-ai
Ready for commands.
```

### **Execute Plan**
```
> Execute SCRUM-6

🚀 Starting story: SCRUM-6
📄 Reading plan: plans/phase-1/SCRUM-6-database-schema.md
📝 Transitioning Jira to 'In Progress'
✅ Progress tracking initialized

📋 Task 1/8: Create SQLAlchemy Product Model
   Creating app/models/product.py...
   ✅ File created (152 lines)
   Updating app/models/__init__.py...
   ✅ File updated
   Creating tests/test_models/test_product.py...
   ✅ Test file created
   Running tests...
   ✅ Tests passed: 6/6

[... continues for all 8 tasks ...]

🔍 Running validation checks...
   ✅ All files created (10 files)
   ✅ Tests passing (94% coverage)
   ✅ No linting errors
   ✅ Acceptance criteria met

🎯 Completing story: SCRUM-6
💬 Adding completion comment to Jira
✅ Transitioning to 'Done'

✅ Story SCRUM-6 completed successfully!
📊 Duration: 3.2 hours
✅ Tasks completed: 8/8
📝 Jira status: Done
```

### **Verify Results**
```
> Check Jira status

📊 SCRUM-6 Status:
   Status: Done ✅
   Assignee: Dharmendra Verma
   Last Updated: 2 minutes ago
   Comment: "Story completed successfully! ..."

> Run tests

pytest tests/ -v --cov=app

======================== test session starts =========================
collected 42 items

tests/test_models/test_product.py ......                      [ 14%]
tests/test_models/test_review.py .....                        [ 26%]
tests/test_models/test_policy.py .....                        [ 38%]
[... more tests ...]

========================= 42 passed in 2.34s =========================
Coverage: 94%
```

---

## 🔮 Advanced Usage

### **Custom Execution Options**

#### **Skip Specific Tasks**
```
Execute SCRUM-6 --skip-tasks 3,4
```

#### **Execute Only Specific Tasks**
```
Execute SCRUM-6 --only-tasks 1,2,3
```

#### **Verbose Logging**
```
Execute SCRUM-6 --verbose --log-file execution.log
```

#### **Debug Mode**
```
Execute SCRUM-6 --debug
```

### **Resume Interrupted Execution**
```
# If execution was interrupted:
Resume execution

# Or specify story:
Resume execution SCRUM-6
```

### **Rollback Changes**
```
# If something goes wrong:
Rollback SCRUM-6

# Rollback specific tasks:
Rollback SCRUM-6 --tasks 5,6,7
```

---

## 📖 Related Documentation

- **Workflow Proposal**: `DEVELOPMENT_WORKFLOW_PROPOSAL.md` (project root)
- **Plan Template**: `plans/templates/story-plan-template.md`
- **Plans Folder**: `plans/README.md`
- **Automation Scripts**: `automation/README.md`

---

## ✅ Checklist for First Execution

Before executing your first story, ensure:

- [ ] VS Code installed and configured
- [ ] Claude Code CLI installed
- [ ] Project opened in VS Code
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured
- [ ] Jira MCP connector authenticated
- [ ] Plan file exists for story
- [ ] Database running (if needed for story)
- [ ] Tests runnable manually

---

## 🎉 Success Criteria

You know execution was successful when:

- ✅ All tasks in plan completed
- ✅ All tests passing
- ✅ No linting errors
- ✅ Jira status updated to "Done"
- ✅ Completion comment added to Jira
- ✅ Files created/modified as expected
- ✅ Progress archived to completed-tasks.json

---

**Ready to start?** Open VS Code, start Claude Code, and execute your first plan!

For questions or issues, refer to the troubleshooting section or the workflow proposal document.
