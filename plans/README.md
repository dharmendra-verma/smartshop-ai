# 📁 Plans Folder - Execution Plans for SmartShop AI

## 🎯 Purpose

This folder contains **detailed execution plans** for each Jira story in the SmartShop AI project. Each plan breaks down a story into granular, actionable tasks that can be executed by Claude Code in VS Code with minimal manual intervention.

---

## 📂 Folder Structure

```
plans/
├── README.md                          # This file
├── templates/                         # Plan templates
│   └── story-plan-template.md         # Standard template for all plans
├── phase-1/                           # Phase 1: Foundation
│   ├── SCRUM-6-database-schema.md
│   ├── SCRUM-7-data-ingestion.md
│   ├── SCRUM-8-load-catalog.md
│   └── SCRUM-9-fastapi-backend.md
├── phase-2/                           # Phase 2: Core AI Agents
│   ├── SCRUM-10-recommendation-agent.md
│   ├── SCRUM-11-review-agent.md
│   ├── SCRUM-12-streamlit-ui.md
│   └── SCRUM-13-integration.md
├── phase-3/                           # Phase 3: Advanced Features
│   └── [Future plans]
└── phase-4/                           # Phase 4: Optimization
    └── [Future plans]
```

---

## 🔄 Workflow Overview

### **Three-Layer Development Architecture**

```
┌─────────────────────────────────────┐
│   Layer 1: Jira (Project Mgmt)     │
│   Epic → Stories → Status Tracking  │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Layer 2: Plans (This Folder)     │
│   Detailed task breakdowns          │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Layer 3: Execution (Claude Code)  │
│   Automated implementation in VS    │
└─────────────────────────────────────┘
```

---

## 📝 How to Use Plans

### **For Planning (Cowork Mode)**

1. **Review Jira Story**: Understand requirements and acceptance criteria
2. **Generate Plan**: Use template to create detailed execution plan
3. **Save to Appropriate Phase Folder**: Save as `SCRUM-X-[story-name].md`
4. **Review & Approve**: Ensure plan is comprehensive and accurate

### **For Execution (VS Code with Claude Code)**

1. **Open VS Code** in the project folder
2. **Execute Command**: Tell Claude Code:
   ```
   Execute plan /plans/phase-1/SCRUM-6-database-schema.md
   ```
3. **Monitor Progress**: Claude Code will:
   - Read the plan file
   - Create/modify files as specified
   - Run tests automatically
   - Update progress tracking
4. **Review Results**: Verify all acceptance criteria are met

---

## 📋 Plan Template Structure

Every plan follows a standard format:

### **1. Story Overview**
- Epic linkage
- Story points
- Priority
- Dependencies

### **2. Acceptance Criteria**
- Checkboxes for all criteria from Jira

### **3. Implementation Plan**
- **Tasks**: 5-10 granular tasks
- **For Each Task**:
  - Files to create/modify
  - Implementation steps
  - Code snippets/examples
  - Test specifications
  - Validation checklist

### **4. Integration Testing**
- Test scenarios
- Manual testing steps

### **5. Documentation Updates**
- Files to update
- Content to add

### **6. Completion Checklist**
- Code quality checks
- Testing verification
- Documentation updates
- Acceptance criteria validation

### **7. Jira Status Update**
- Transition information
- Completion comment template

---

## ✅ Plan Quality Criteria

A good execution plan should:

1. **Be Specific**: No vague instructions - every step is actionable
2. **Be Complete**: Covers all aspects (code, tests, docs)
3. **Be Traceable**: Links to Jira story and acceptance criteria
4. **Be Testable**: Clear validation steps and test cases
5. **Be Self-Contained**: Claude Code can execute without additional context

---

## 🤖 Automation Features

### **Automatic Progress Tracking**
- Plans update `.progress/current-story.json` during execution
- Real-time status of tasks
- Completion timestamps

### **Automatic Jira Sync**
- Completed plans trigger Jira status updates
- Completion comments auto-generated
- Next story automatically queued

### **Automatic Testing**
- Tests run after each task
- Coverage reports generated
- Failures block progress

---

## 📊 Progress Tracking Integration

During plan execution, the system maintains:

### **`.progress/current-story.json`**
```json
{
  "story_id": "SCRUM-6",
  "plan_file": "plans/phase-1/SCRUM-6-database-schema.md",
  "status": "in_progress",
  "tasks_completed": 3,
  "tasks_total": 8,
  "started_at": "2026-02-15T18:00:00Z",
  "last_updated": "2026-02-15T19:30:00Z"
}
```

### **`.progress/completed-tasks.json`**
```json
[
  {
    "story_id": "SCRUM-6",
    "plan_file": "plans/phase-1/SCRUM-6-database-schema.md",
    "completed_at": "2026-02-15T20:00:00Z",
    "duration_hours": 2.5,
    "tasks_completed": 8,
    "tests_passed": 45
  }
]
```

---

## 🚀 Execution Examples

### **Example 1: Execute Single Plan**
```
User in VS Code: "Execute plan SCRUM-6"
or
User in VS Code: "Execute plans/phase-1/SCRUM-6-database-schema.md"
```

### **Example 2: Execute Multiple Plans Sequentially**
```
User in VS Code: "Execute all Phase 1 plans in order"
```

### **Example 3: Resume Interrupted Plan**
```
User in VS Code: "Resume current plan"
(Reads from .progress/current-story.json)
```

---

## 🎯 Benefits of This Approach

### **For You (Developer)**
✅ **Minimal Effort**: One command per story
✅ **No Context Switching**: Everything is automated
✅ **Clear Visibility**: Real-time progress tracking
✅ **No Manual Jira Updates**: Automatic synchronization

### **For Code Quality**
✅ **Consistent Standards**: Template-driven development
✅ **Complete Testing**: Tests auto-generated and run
✅ **Comprehensive Documentation**: Docs updated automatically
✅ **Traceable Changes**: Every change linked to story

### **For Project Management**
✅ **Real-Time Status**: Jira always up-to-date
✅ **Accurate Estimates**: Time tracking built-in
✅ **Clear Audit Trail**: Complete history of changes
✅ **Predictable Velocity**: Data-driven sprint planning

---

## 📖 Creating a New Plan

### **Step 1: Copy Template**
```bash
cp plans/templates/story-plan-template.md plans/phase-N/SCRUM-X-[story-name].md
```

### **Step 2: Fill in Story Details**
- Story overview from Jira
- Acceptance criteria from Jira
- Dependencies analysis

### **Step 3: Break Down into Tasks**
- 5-10 granular tasks
- Each task should take 15-30 minutes
- Include specific file paths
- Add code examples

### **Step 4: Define Tests**
- Unit tests for each component
- Integration tests for workflows
- Manual testing scenarios

### **Step 5: Define Validation**
- Checklists for each task
- Overall completion checklist
- Jira update template

---

## 🔗 Related Documentation

- **Workflow Proposal**: `DEVELOPMENT_WORKFLOW_PROPOSAL.md` (project root)
- **VS Code Guide**: `docs/VSCODE_EXECUTION_GUIDE.md` (to be created)
- **Automation Scripts**: `automation/` folder
- **Progress Tracking**: `.progress/` folder

---

## ❓ FAQs

### **Q: How detailed should a plan be?**
A: Detailed enough that Claude Code can execute it without ambiguity. Include specific file paths, code structure examples, and clear validation steps.

### **Q: Can I modify a plan during execution?**
A: Yes, but it's better to complete the current execution and create a new plan for modifications. This maintains traceability.

### **Q: What if a plan execution fails?**
A: The system will:
1. Log the failure in `.progress/current-story.json`
2. Stop execution
3. Notify you with error details
4. Allow you to fix issues and resume

### **Q: How long does it take to execute a plan?**
A: Depends on complexity:
- Simple stories (3 SP): 1-2 hours
- Medium stories (5 SP): 2-4 hours
- Complex stories (8 SP): 4-8 hours

### **Q: Can I run multiple plans in parallel?**
A: No, plans execute sequentially to avoid conflicts. However, you can queue multiple plans for sequential execution.

---

## 🎉 Success Metrics

Track your workflow efficiency:

- **Time Saved**: ~75% reduction in manual work per story
- **Quality Improvement**: 100% test coverage, 0% lint errors
- **Traceability**: 100% of changes linked to stories
- **Predictability**: Variance in estimates < 20%

---

**Ready to execute?** Choose a plan from the appropriate phase folder and tell Claude Code to execute it!

**Need help?** Refer to `docs/VSCODE_EXECUTION_GUIDE.md` for detailed execution instructions.
