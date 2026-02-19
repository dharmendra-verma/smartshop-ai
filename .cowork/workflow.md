# Jira to Development Workflow
 You have to task to do. Based on user query either of task 1 or 2 need to be done by you.

## Task 1. When User ask to work on "In Progress" user story:
1. Fetch the user story details from Jira
3. Check Jira for any story that's in progress
4. If no story is in progress then notify the user and stop working. You are not allowed to make story move to in progress state
4. Create an implementation plan in `plans/plan/STORY-ID.md`
5. Break down into tasks in `plans/plan/STORY-ID.md`
6. Include:
   - Acceptance criteria
   - Technical approach
   - File structure needed
   - Testing requirements
5. Follow this Plan Format:
   - Use markdown
   - Include story ID and title
   - List dependencies
   - Estimate complexity


## Task 2. When user ask to work on completed story in the project:
1. Read the completion report from `.progress/STORY-ID.md` for `plans/inprogress/STORY-ID.md` todo
2. If you stasified then move `plans/inprogress/STORY-ID.md` to `plans/completed/STORY-ID.md`
3. Update Jira story STORY-ID:
   - Move to "Code Review" or "Done" status
   - Add comment with implementation summary
   - Link the files modified
   - Update estimated vs actual time (if tracked)
4. Notify me of completion

