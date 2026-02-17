# Jira to Development Workflow

## When I move a Jira story to "In Progress":

1. Fetch the user story details from Jira
2. Create an implementation plan in `plans/epic-ID/STORY-ID.md`
3. Break down into tasks in `plans/epic-ID/STORY-ID.md`
4. Include:
   - Acceptance criteria
   - Technical approach
   - File structure needed
   - Testing requirements

## Plan Format:

- Use markdown
- Include story ID and title
- List dependencies
- Estimate complexity

## After Claude Code Completes Implementation:
1. Read the completion report from docs/completion/STORY-ID.md
2. Update Jira story STORY-ID:
   - Move to "Code Review" or "Done" status
   - Add comment with implementation summary
   - Link the files modified
   - Update estimated vs actual time (if tracked)
3. Notify me of completion

```
## Practical Workflow (Step-by-Step)

**Here's what you actually do:**

1. **In Jira:** Move story "PROJ-123" to "In Progress"

2. **Open Cowork and prompt it:**
```
   "Check Jira for any story that's in progress. 
   Create an implementation plan in plans folder
   following the workflow in .cowork/workflow.md"