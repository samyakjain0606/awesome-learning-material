Mark current phase as complete and intelligently handle next steps.

**What this does:**
1. Updates your implementation.md - marks current phase ✅ complete
2. **Checks if all planned phases are complete**
3. If yes: **Asks user for new feature ideas and updates planning docs**
4. If no: Creates next phase implementation file with specific tasks
5. Sets up tracking for the new phase

---

## 🎯 INTELLIGENT PHASE COMPLETION

**Step 1: Read Current State**
- Read implementation.md to understand phase status
- Identify which phase just completed
- Check if this was the last planned phase

**Step 2: Decision Logic**
- **If more phases planned:** Create next phase file automatically
- **If all phases complete:** Engage user for next direction

---

## 🤔 END-OF-PLAN ENGAGEMENT

**When all planned phases are complete, ask the user:**

1. **"All planned phases complete! What would you like to add next?"**

2. **Present feature categories with examples:**
   - 🎨 **Visual Enhancements:** shadows, borders, filters, rounded corners
   - 📐 **Layout & Sizing:** custom canvas, padding controls, positioning
   - ⚡ **Productivity:** batch processing, presets, drag & drop
   - 🎯 **Advanced Features:** radial gradients, patterns, textures
   - 🔧 **Technical:** performance, accessibility, testing

3. **Ask specific questions:**
   - "Which category interests you most?"
   - "Any specific features you have in mind?"
   - "What pain points should we solve next?"

4. **Based on user response:**
   - Update plan.md with new feature roadmap
   - Update implementation.md with new phases
   - Create detailed phase implementation file

---

## 📋 NEXT PHASE FILE TEMPLATE

Creates: `phase-[X]-implementation.md` (only after user input if all phases were complete)

```markdown
# Phase [X]: [Phase Name]

**Goal:** _What specific milestone are you building toward?_

**Duration:** _X days/weeks_

**Success Test:** _How do you know this phase works?_

---

## 🎯 TASKS

**Core Work:**
- [ ] _Main task 1 (based on user input)_
- [ ] _Main task 2 (based on user input)_ 
- [ ] _Main task 3 (based on user input)_

**Testing:**
- [ ] _Test the main functionality_
- [ ] _Test edge cases_
- [ ] _Test integration with previous phases_

**Documentation:**
- [ ] _Update README or docs_
- [ ] _Document any new APIs/interfaces_

---

## ✅ COMPLETION CRITERIA

**This phase is done when:**
- [ ] _Specific working feature/capability_
- [ ] _Tests pass and prove it works_
- [ ] _Can demo the milestone to someone_

**Success Test:** _Specific way to validate this phase works_

---

## 📈 PROGRESS

**Daily Log:**
```
[Date] - [What got done] - [Any blockers]
```

**Blockers:**
- [ ] _Any current issues blocking progress_

---

**When done, run `/complete-phase` again for the next phase**
```

---

## 🔄 DOCUMENT UPDATES

**When creating new phases based on user input:**

1. **Update plan.md:**
   - Add new feature section
   - Update roadmap with user-requested features
   - Add rationale for new direction

2. **Update implementation.md:**
   - Add new phases to phase tracking
   - Update current phase status
   - Add iteration notes about user feedback

---

## 🚀 WORKFLOW EXAMPLES

**Scenario 1: More Phases Planned**
```
Phase 3 Complete → Automatically create Phase 4 file
```

**Scenario 2: All Phases Complete**
```
Phase 4 Complete (last planned) → Ask user:
"All 4 phases complete! What would you like to add next?"
User: "I want shadow effects and batch processing"
→ Update plan.md and implementation.md
→ Create Phase 5: Visual Enhancements  
→ Create Phase 6: Batch Processing
```

**Scenario 3: User Wants to Stop**
```
User: "The current features are sufficient"
→ Update docs to mark project as "Feature Complete"
→ Suggest maintenance/polish tasks if needed
```

---

## 🎯 EXECUTION STRATEGY

1. **Always read implementation.md first**
2. **Parse phase status intelligently**
3. **If last phase completed:** pause and engage user
4. **If user provides input:** update all planning documents before continuing
5. **Keep user in control** of feature direction

**This ensures the project evolves based on actual user needs, not predetermined assumptions.**