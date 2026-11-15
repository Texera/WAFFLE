# One-form, one-hour teammate study

**Revised design, November 15, 2026.** The user requested one Google Form and easier tasks within one hour. This replaces the earlier three-form, 75–90-minute proposal. The form and simplified loop templates are not created yet. Keep the checked computation bodies; build and rehearse the simpler starters before the pilot.

## Before the session

Complete installation, login, import and export checks beforehand. Give each participant a private Texera account/workflow copy on the hosted server, KNIME starters with working local paths, and an assigned ID/tool order/data packs. Setup is not part of the hour. Do not send reference solutions or hidden tests.

Both tools start with working loop templates that run once, with the loop boundaries and body already connected. Clustering/scoring, file parsing and averaging are prepared. Texera keeps its native readers, Aggregate and Sort. Participants configure the repetition and stopping rule; they do not build graphs from scratch, write computation code or search for datasets. Provide a short guide to the relevant fields, equally detailed for both tools. KNIME may use its normal specialized controls, including a compatible conditional loop end from the outset; do not force an avoidable node replacement.

## Sixty-minute schedule

| Part | Minutes |
| --- | ---: |
| Welcome and background | 3 |
| First tool | 22 |
| Break | 2 |
| Second tool | 22 |
| Final comparison | 6 |
| Buffer | 5 |
| Total | 60 |

Each 22-minute tool block has three minutes of guided practice, seven minutes for the sweep, four for adaptation, five for files, and three for recording answers and exporting/uploading work. Practice uses an unrelated small loop and teaches only the controls needed by the tasks. Pilot it before main collection.

| Activity | Short task | Cap |
| --- | --- | ---: |
| Sweep | The supplied loop runs K=2 once. Change it to try K=2,3,4. Return K and score and identify the best K. | 7 min |
| Adapt | Change that workflow to stop when score reaches the given target, keeping the stopping row; otherwise stop after K=4. | 4 min |
| Files | The supplied loop reads the first CSV. Change it to process all three CSVs and return each filename and average price, including when another CSV is added. | 5 min |

Use the existing tiny inputs and two answer-equivalent packs. Preserve the same requirements in both tools. Half start with KNIME and half with Texera; balance packs through KNIME/A→Texera/B, KNIME/B→Texera/A, Texera/A→KNIME/B, Texera/B→KNIME/A. Teammates receive an assignment rather than choosing their order.

## One Google Form, one final submission

The form contains the instructions, starter/reference links, task questions and feedback. Use sections so participants see one task at a time:

1. **Welcome:** prefilled ID/assignment, voluntary participation, prior KNIME/Texera/Python experience and whether the participant helped develop WAFFLE. Include “Both tools are ready” before starting.
2. **First tool practice and three task sections.** Each task section shows the neutral card, its time cap and the small response block below.
3. **Break and second tool practice/three task sections.** Use the other assigned pack.
4. **Final comparison:** which tool was easier for each activity (KNIME / Texera / Same / Cannot judge), plus one optional sentence about why.
5. **Submit once**, including incomplete attempts.

At each task collect only:

- Outcome: Completed / Time limit / Stopped early / Technical problem.
- Elapsed minutes/seconds, or “Not recorded.”
- Ease: 1 = Very difficult, 7 = Very easy.
- Saved workflow export, including unfinished work. Allow an export-failure reason instead.
- For sweep/adaptation, best K and score, or “not obtained.” For adaptation, Own workflow / Supplied fallback.

Collect any outside help, major waiting, interruptions or other problems once per tool, with task numbers. Do not require six written explanations, six screenshots or separate result CSV uploads. The exported workflow is the main evidence. A screenshot is optional when reporting an error.

Save a separate workflow copy after each task and attach it before clicking Next. Do not overwrite the sweep when adapting it. Reveal the adaptation request only on its later section. If the sweep is unfinished, save/attach it first, then use a clearly labeled fallback to try adaptation and mark that attempt assisted. It cannot count as independent create-and-adapt success.

## Simple timing and stopping rule

Start a stopwatch when reading each task; stop at completion or its cap. **Elapsed task time includes execution waits.** Export/upload and form-answer time use the separate three-minute allowance per tool. This replaces the earlier active-time/pausing rule and avoids pause accounting. Record significant waiting separately when it affected the task; these times are not pure interface authoring time.

At a cap, save the current state and move on. At 60 minutes, stop and submit what is available. A server failure is a technical block, not evidence the participant could not use the loop controls. Do not extend the session indefinitely. Missing or estimated times stay flagged. Time is self-reported, not inferred from the form timestamp.

Use the supplied reference and ordinary application help equally in both tools. No outside task solutions, AI assistance or another participant's workflow during timed work; if help occurs, record it and retain the attempt. Do not reveal correctness feedback between tools.

## Forms and analysis details

Keep online draft saving enabled and test it with a signed-in teammate account. Next does not submit a section: the researcher receives the response only when Submit is clicked. Keep later questions optional or offer Not attempted, and provide a “Stop and submit what I have” route so someone can finish early. Do not treat draft autosave as a researcher-visible record. Save workflow exports locally as well.

Use one form in My Drive with file uploads, a private linked response Sheet, no public response summary and no quiz scoring. Test actual .knwf/.json uploads and account access. Google uploads require sign-in. Prefilled assignments and section order are conveniences, not tamper-proof controls. Do not permit edits to the submitted response; record later corrections separately. No custom portal is needed.

Independently check the saved workflows and actual iteration visits on visible/hidden fixtures. The existing harness checks prepared solutions; rehearse grading a changed participant export before calling grading automatic. Preserve incomplete, assisted, blocked and missing responses. Report paired correct independent configure+adapt completion within the **11-minute elapsed task budget**, with files separate, and report correctness regardless of time as a sensitivity summary. Do not mix these timings with the superseded 15-minute active-budget design. This measures basic loop configuration/adaptation on prepared workflows, not full workflow development or general superiority.

Before inviting the team, create the single-iteration loop templates in both tools, update the generated cards to the configure/extend tasks and new time limits, and dry-run them. The current generator still produces the previous add-a-loop starters/cards; do not distribute those as the one-hour version. Then rehearse the form with one teammate in a strict hour, including an unfinished task and a failed upload. If form/export steps exceed their allowance, simplify those steps rather than silently extending the hour. Hosted URL, per-participant paths/copies, matched practice and form creation remain pending. No form or invitation has been sent.

Product sources checked November 15, 2026: [section routing](https://support.google.com/docs/answer/141062?hl=en), [online draft saving](https://support.google.com/docs/answer/10952360?hl=en), [uploads and prefills](https://support.google.com/a/users/answer/13138098?hl=en), [upload sign-in](https://support.google.com/docs/answer/15473134?hl=en).
