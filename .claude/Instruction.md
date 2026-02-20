# Development Instructions

You are expert developer in doing implemntation of the given todo under `plans/plan/STORY-ID.md`
Plan and start working in below sequence and with given instruciton
1. Pick the first `STORY-ID.md` Move it under `plans/inprogress/STORY-ID.md` folder
2. Analyze the `plans/inprogress/STORY-ID.md` and if needed create task as well within this todo 
3. Kepp on tracking the time spent by you on this implementation 
4. Do Implemention in app/ following our project structure
5. Create/update tests in tests/
6. Run test suite
7. Run the applicaiton to check if everything is ok
8. Generate completion report in `.progress/STORY-ID.md` along with the total time spent on the implementaiton
9. Notify user that task has been completed and ask if you can commit and push the changes in git
10. Once user notify commit and push the changes with STORY-ID.md

Project conventions:
#- Use Python 3.11
#- Follow PEP 8
- Write unit tests for all functions
- Document all public APIs

```
This way, next time you can just say:
claude-code Execute plans as per /claude/Instruction.md
```
