# Asynchronous teammate pilot

**Design proposal, November 15, 2026.** Forms have not been created. This keeps the three activities, native Texera operators, balanced assignment and outcomes of the [main protocol](README.md). Pilot the delivery before freezing the main study.

## Use three forms and an assigned checklist

1. **Welcome form**, once: background and setup readiness.
2. **Task form**, six submissions: one after each activity in each tool.
3. **Final comparison**, once: preferences and reasons.

Link responses to a private Google Sheet. Each participant receives an ID and one instruction document with links in the assigned order. Separate task submissions preserve unfinished work if someone stops halfway. No custom application or screen recording is needed for this pilot.

Use the neutral title **Workflow loop study** and introduction: “We are comparing two ways to build and change workflow loops. We are testing the tools and instructions, not your ability. Unfinished tasks and difficulties are useful results.”

## What each teammate does

Before timing anything, install KNIME, open the hosted Texera server, and verify import, single-input execution and export in both tools. Resolve setup problems asynchronously first. Give separate workflow copies and data/trace paths to each participant.

| Step | Action |
| --- | --- |
| Welcome | Complete the background form and readiness check. |
| First tool | Short tutorial and five-minute practice on an unrelated loop. |
| Activity 1 | Create the K=2,3,4 sweep; save and submit. Up to 10 active minutes. |
| Activity 2 | Open the change request after submitting Activity 1; adapt its saved workflow; submit a new copy. Up to 5 active minutes. |
| Activity 3 | Use the separate file starter to process all CSVs; save and submit. Up to 10 active minutes. |
| Break | Rest, or do the second tool in another sitting. |
| Second tool | Repeat the same process with the other data pack. |
| Finish | Compare the tools and describe the main difficulty. |

Allow about 75–90 minutes plus setup and unusual waits. Keep Activities 1 and 2 together. Tell participants that a change request will follow, without revealing its exact condition early. Send task cards as separate links, not one document containing all answers or facilitator material.

Assign across four sequences: KNIME/A then Texera/B; KNIME/B then Texera/A; Texera/A then KNIME/B; Texera/B then KNIME/A. Randomize within balanced groups and spread prior experience across orders. Participants do not choose their order.

## Timing and help

Use the same stopwatch method in both tools. Start when opening the task card; reading, planning, configuring, debugging and interpreting results count. Pause only while completely blocked waiting for the application or for an unrelated interruption, and record these pauses separately. Keep timing if useful work continues during execution. Stop at completion, giving up or the time cap. Save and freeze the current workflow; export/upload and questionnaire time are excluded in both tools.

If the timer was forgotten, report missing or estimated time. Do not infer active time from form submission timestamps. Times and cap compliance are self-reported; workflow correctness is checked independently. Keep completion as the primary outcome under the main protocol, explicitly qualify the self-reported time budget, and report correctness regardless of time as a sensitivity summary. Missing timing must not silently become a within-budget success.

Use only the supplied reference and ordinary application help during tasks. Give equally complete materials to both platforms. Ask participants not to use AI solutions, other participants or online task solutions; record outside help if it occurs. Keep assisted attempts visible. Do not reveal hidden-test results between tools.

An infrastructure failure means “Blocked,” not an authoring failure. Save the attempt and pause the study for asynchronous support. Preserve the original attempt if it is later resumed or rerun. Normal workflow mistakes remain part of the task. Match the tutorials and unrelated practice before inviting the pilot; these are still preparation work.

## Exact form contents

### Welcome

- Participant ID, prefilled.
- Agreement to participate voluntarily after reading the explanation; declining ends the process.
- Experience with KNIME, Texera and Python: Never / Tried briefly / Several projects / Regular use.
- WAFFLE involvement: None / Discussed or reviewed / Helped implement or test.
- Operating system, for setup support.
- “I can open, run and export the starter in both tools”: Yes / Need help. Setup help comes before timed work.

Keep the ID/contact mapping private. Explain who can inspect submissions; do not promise anonymity when the organizer can identify participants.

### Task submission, reused six times

- Prefilled participant ID, tool, pack and activity.
- Outcome: Completed / Time limit reached / Stopped early / Technical problem.
- Upload the saved `.knwf` or `.json`, including incomplete work. If export is impossible, allow a reason instead.
- Output screenshot or CSV, if available. For sweep/adaptation, also enter best K and score, or “not obtained.”
- Active minutes/seconds; timing source: Stopwatch / Estimated / Not recorded.
- Approximate blocked-wait time and unrelated interruption time, separately.
- Activity 2 starting point: My Activity 1 / Supplied fallback.
- Help used: Supplied reference/application help only / Setup support / Outside task help or AI, with a short explanation.
- “Overall, how difficult or easy was this activity?” 1 = Very difficult, 7 = Very easy.
- Optional: main difficulty; early task viewing, wrong pack/order or other procedure problem.

Name exports `ID_tool_pack_activity_attempt`. Preserve Activity 1 before changing it. If Activity 1 is unfinished, submit it first, then use a correct fallback provided in a separate, clearly labeled step. Mark the adaptation as assisted; it cannot count as independent create-and-adapt completion. If a participant continues from an incorrect self-reported success, judge the saved workflow later rather than assuming the baseline was correct.

### Final comparison

- Which tool was easier for each of creating the sweep, changing the stopping rule and processing files? KNIME / Texera / About the same / Cannot judge.
- What made the biggest difference?
- Which would you choose for a similar task, and why? KNIME / Texera / Depends / Cannot judge.
- What should change in the instructions or setup?
- If you stopped early, where and why? Allow final feedback without completing both tools.

## Form settings and verification

Use file-upload forms in the organizer's My Drive, not a Shared Drive. Uploads require a Google account. Test actual KNIME and JSON uploads with a teammate account and suitable file settings. If account policy blocks uploads, arrange a private submission folder and collect its link instead. Do not require public workflow sharing.

Leave “Limit to 1 response” off for the reusable task form. Disable response editing, response summaries and quiz scoring. Corrections get new rows identified as corrections; retain the original timed attempt. Prefilled IDs are editable conveniences, so match them against the assignment list. Plain Forms/document links do not enforce stage order; ask participants to follow the checklist and report deviations.

Check exported workflows offline on the visible and hidden fixtures, including actual visited K values, the stopping row and an added file. Screenshots and self-reported success are supplementary. Existing runners test prepared reference graphs, not arbitrary participant uploads: rehearse a modified submission and a deliberately incorrect submission before claiming automatic grading. Preserve original exports and document path-only rebasing; do not repair loop logic while grading.

Regenerate KNIME paths for each participant's machine and Texera paths for the hosted worker. Use isolated workflow copies and trace directories. Do not send the whole generated facilitator package, hidden fixtures or solutions. Test hosted access, concurrency and export before recruitment; localhost correctness does not prove those work.

## Next implementation step

Create the three forms, participant checklists, matched practice materials and private starter packages once the hosted Texera address is available. Have one teammate follow the whole process without spoken help, including an unfinished task and an upload failure. Check that all six submissions retain the correct ID/tool/pack and frozen workflows. Fix the procedure before collecting main-study data. No forms or invitations have been created or sent by writing this proposal.

Google product details checked November 15, 2026: [uploads and prefilled fields](https://support.google.com/a/users/answer/13138098?hl=en), [upload sign-in](https://support.google.com/docs/answer/15473134?hl=en), [response settings](https://support.google.com/docs/answer/2839588?hl=en), [linking to Sheets](https://support.google.com/docs/answer/139706?hl=en).
