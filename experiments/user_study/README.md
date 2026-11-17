# User study: configuring and adapting workflow loops

**Status: 35-minute connected-loop revision, November 15, 2026. No participant results.** Both platforms pass 12 native checks each on the two-task protocol. Task A also passes GUI import, initial run, sweep edit/run, adaptation edit/run and separate exports in both tools. Six relocated KNIME archives pass native checks. See the [rehearsal record](results/2026-11-15-35min/README.md). Texera uses native CSV File Scan and Sort with prepared clustering. The historical [36-run record](results/2026-11-15-native-operators/README.md) covers the older three-task design. A teammate timing pilot remains necessary. This is the facilitator's protocol; give participants only their starter, neutral task cards and platform field guide.

## Question and hypothesis

Does WAFFLE's common loop interface help workflow users configure repetition for different inputs and adapt a loop when its stopping rule changes?

The hypothesis is that WAFFLE reduces the effort of adapting the stopping rule while retaining the computation and loop structure. Keep basic authoring in the comparison too: KNIME's specialized nodes may be convenient for these tasks. This study can support a claim about the tested authoring activities and participants, not general superiority over KNIME or greater expressiveness.

## Two short activities in each tool

Each participant uses local KNIME and browser-based Texera hosted on the study server. For the 35-minute design, both tools receive equivalent working single-iteration loop templates, input tables, output viewers and help sheets. Participants configure repetition and its stopping rule; they do not build the graph or implement clustering, scoring, file parsing or aggregation. Generate the connected-loop templates with `--short`; the legacy three-task mode remains available for reproducing older captures.

| Activity | Neutral participant card | What it measures |
| --- | --- | --- |
| 1. Configure a K-means sweep | The supplied loop runs K=2 once. Change it to run K = 2, 3 and 4. Return each K and its score, and identify the best K. | Basic loop configuration |
| 2. Change the stopping rule | Now stop when the score first reaches the supplied target. Include that result. If the target is never reached, finish the supplied K values. Return the scores and best K among the values actually tried. | Adapting a loop to a result-dependent rule |

Activity 2 starts from the participant's saved Activity 1 workflow. The prepared scoring body makes the current score available to loop control in both tools from the start. The participant saves Activity 1 before reading the adaptation section and uploads the two separate copies after that tool block. Give identical information in both platforms.

If Activity 1 fails, record that outcome and provide a correct fallback before Activity 2. Mark the adaptation as fallback-assisted, even if no further help is needed. It cannot count as an independently completed create-and-adapt task. Keep its result visible and report it separately.

## Baseline and preparation

- Prefer ordinary Texera operators: native CSV File Scan and Sort are used in the current starter. Keep clustering in a prepared UDF because the tested revision has no built-in K-means operator. The KNIME reference uses a convenient loop construction with an equally prepared calculation; this is not a comparison of ML libraries or runtime speed.
- Use the normal convenient KNIME solution. Allow specialized loop nodes, general loops, flow variables and equivalent expressions. A participant may choose a conditional loop from the outset. Do not force a node replacement or a deliberately long construction.
- KNIME supports result-dependent stopping through Variable Condition Loop End. Its [official loop reference](https://docs.knime.com/build/loops/reference) describes the available starts and ends. Confirm the exact node compatibility and behavior in the installed study version during rehearsal; do not infer them from the paper's taxonomy alone.
- Have someone familiar with KNIME review and run the reference solution before freezing the tasks. Apply the same review to WAFFLE. Keep valid shorter solutions accepted in either system.
- Use the same numerical computation, seeds and scoring definition in both prepared bodies. Confirm matching answers before recruiting. Give both tools equally complete references covering all controls needed by the tasks, including conditional termination. No task-specific answer is given in either reference.
- Prepare equivalent tasks A and B with different numerical answers. Choose a unique best K and a target reached before the last K in the visible adaptation task. Show the target as a concrete number on the card. Input sizes stay small so authoring dominates the session.
- Score saved workflows with independent reference answers. Test the sweep with different points while retaining K = 2, 3 and 4. For adaptation, check the actual visited K values and returned rows, including an input that does not reach the target. Extra iterations followed by filtering do not satisfy early stopping. Keep these checks outside the participant's timed editing period and do not reveal their results between tools.
- The older batch-inspection pilot package is a different task. Its author-run checks do not establish that these K-means and file starters are ready or that either system is easier to use.

## Assignment and session

Use the [single-form, 35-minute asynchronous design](ASYNC.md). One Google Form contains the instructions, four timed tasks and final comparison, with one submission at the end. Setup happens beforehand. Hosted delivery and teammate timing need a pilot.

Pilot with one teammate. Then aim for 16 participants if feasible, with four participants per sequence: KNIME/A then Texera/B; KNIME/B then Texera/A; Texera/A then KNIME/B; Texera/B then KNIME/A. Randomize within balanced blocks and spread prior KNIME/Texera experience across orders. Record Python experience and involvement in WAFFLE. Authors and implementers rehearse the materials; report recruitment from the team and any direct contributors included in the main study.

Use the same process for everyone:

1. Welcome and background: two minutes.
2. First tool: two-minute practice, four-minute sweep, four-minute adaptation, and two minutes for answers and exports/uploads (12 minutes total).
3. Repeat the same 12-minute block in the second tool with the other task.
4. Final comparison: four minutes, plus a five-minute buffer. Submit the single form once, including unfinished work, and stop by 35 minutes.

Setup is completed beforehand. Task timing is self-reported elapsed time, including execution waits; export/upload and questionnaire time have a separate allowance. Record major waits and technical blocks rather than treating them as inability to use the tool. At each cap, save the current state and move on. Keep help policy and reference detail equal. This 35-minute procedure supersedes the earlier one-hour and 75-minute proposals; see ASYNC.md for form fields, early exit and offline grading.

## Outcomes fixed before main-study collection

The primary comparison is **correct independent completion of the combined configure-and-adapt task within its eight-minute elapsed task budget**. Its denominator includes every valid paired session, including failures and timeouts. Report four paired counts: both tools, WAFFLE only, KNIME only, neither. Show sweep configuration separately so the adaptation result does not hide a cost elsewhere. This narrower task does not measure creating a workflow from scratch.

For participants who independently complete both stages in both tools, compare self-reported total elapsed task time as paired observations and report the median paired difference and the number of pairs. These times include execution waits and are not pure editing time. Missing timing remains unknown; also report correctness regardless of time. Show adaptation time separately for the subset with independent successful base workflows in both tools, stating the denominator. Keep fallback-assisted results, failures and timeouts visible rather than treating the time of successful attempts as the whole result.

Report ease ratings, preference counts including ties, and reasons given by participants. Record edits to expressions, node replacements and reconnections as descriptive evidence about where effort went; fewer edits alone do not prove greater usability. Inspect whether the second tool tends to be faster regardless of platform. The fixed activity order does not isolate a general learning-rate advantage.

Freeze task wording, accepted solutions, caps, training and analysis after the pilot and before collecting the main data. Pilot results stay separate if the procedure changes. Do not change the primary outcome or discard a task after seeing which tool wins.

## Claim supported by the result

If the measured advantage is confined to adaptation, say that participants adapted the stopping rule more successfully or faster under these conditions. If KNIME is faster for the basic sweep, report that alongside the adaptation result. If outcomes are similar, report a tie rather than claiming WAFFLE is easier. A failure to finish in the allotted time does not establish that a framework cannot express the task.

The next step is to have a KNIME-experienced teammate check the baseline and pilot the timing and wording before recruiting. Repeat the GUI rehearsal after moving Texera to the study server.

## Build and check the materials

Use `--short` for the current two-task protocol. Without it, the generator reproduces the legacy three-task package. Native author-run checks validate computation and stopping, not ease of use or the 35-minute participant timing.

Install the root `requirements.txt`. The recorded checks use KNIME 5.5.3 with Java Snippet and the Texera prototype at `a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`. The native runners below target Windows; they require the installed KNIME runtime or the prototype's normal build and Python dependencies. `StudyWorkflowSpec.scala` is added only to the sbt session, without editing Texera source or build files.

```text
python experiments/user_study/study.py prepare C:/study/pilot-01 --short
python experiments/user_study/run_knime.py --runtime C:/tools/knime --package C:/study/pilot-01
python experiments/user_study/run_waffle.py --repo C:/src/texera-prototype --package C:/study/pilot-01 --python C:/venv/Scripts/python.exe --java C:/jdk17/bin/java.exe --sbt-launch C:/tools/sbt-launch.jar
python experiments/user_study/study.py check C:/study/pilot-01
```

The generator refuses an existing destination. Prepare a fresh package for each participant or rehearsal. `participants/<task-letter>/<tool>/` contains one connected-loop starter: the K-means sweep. Activity 2 deliberately starts from the saved Activity 1 submission, so it has no separate participant starter. `cards/<task-letter>/` has the two task cards. Give only the relevant platform section of [SHORT_REFERENCE.md](SHORT_REFERENCE.md), not its facilitator notes. Keep `facilitator/`, hidden input variants, and the manifest out of the participant's materials.

Import each KNIME `.knwf` separately into Local space. The short participant KNIME archives embed the tiny input fixture and write audit files under a unique JVM temporary directory, so they can move between machines. Texera JSON files and native facilitator workflows use the configured runtime paths; regenerate those when moving the runtime. Reference solutions are in `facilitator/runs/<tool>-<task-letter>-<activity>-visible/`. Run the sweep and adaptation solutions and inspect their result tables. The native checker independently verifies both output and actual body visits on visible and hidden inputs; it also rejects changed source inputs.

For asynchronous delivery, supply the fallback for the assigned tool and task from `facilitator/fallbacks/<task-letter>/<tool>/` separately as “Open only after an unfinished sweep.” The KNIME fallback is portable too. The participant saves the unfinished attempt before using it and records fallback assistance. Do not distribute other solutions, hidden inputs or the manifest. Each participant needs a private Texera copy and writable trace paths; use a separate generated package per participant. The form draft and assignment links are kept privately by the organizer.

To exercise the portable packaging on both tasks, run `python experiments/user_study/check_portable.py --package <fresh-package> --runtime <knime-runtime>`. This relocates and executes six archives and records exact outputs. It creates `facilitator/portable-rehearsal/` and refuses to overwrite an existing rehearsal.

Native runs and GUI copies of the same generated workflow share trace destinations. Do not run them concurrently. Save validation evidence before GUI editing, and use a separate fresh package for participant submissions. The supplied native runner tests reference workflows, not an arbitrary participant submission: score the saved submission separately with the same fixtures and exact-visit requirements.

For a hosted Texera server, generate with `--waffle-runtime-root /srv/waffle-study/pilot-01` and place the package's data and trace directories at that server path, writable by the execution worker. This mapping affects only WAFFLE; KNIME still reads its local copy. Retrieve the server's traces for checking. Rehearse on the actual study server before recruitment. The preparation does not deploy or configure a server.

To recheck the published author evidence without either application:

```text
python -m unittest discover -s experiments/user_study -v
python experiments/user_study/verify_recorded.py
python experiments/user_study/verify_recorded.py 2026-11-15-native-operators
python experiments/user_study/verify_recorded.py 2026-11-15-35min
```

These commands recompute expected answers from the synthetic fixtures and inspect captured native outputs. They do not rerun either engine and are not usability measurements.
