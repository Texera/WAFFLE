# One form, 35-minute study

The user approved this shorter protocol on November 15, 2026. It supersedes the one-hour and three-form proposals. One person uses both tools, completes two tasks per tool, and submits one Google Form. The file-processing task is omitted.

## Schedule

| Part | Minutes |
| --- | ---: |
| Welcome and background | 2 |
| First tool | 12 |
| Second tool | 12 |
| Final comparison | 4 |
| Buffer | 5 |
| Total | 35 |

Each tool block includes two minutes to run the unchanged connected-loop starter and find its controls, four minutes to configure the sweep, four to adapt the stopping rule, and two for answers and exports. Install/login/import checks happen beforehand. A teammate pilot must establish whether these caps are practical; author execution checks are not participant timing evidence.

## Tasks

1. The supplied loop runs K=2 once. Change it to try K=2,3,4, return every K and score, and identify the best K.
2. Adapt that saved workflow to stop when the score first reaches the supplied target, including that row; otherwise finish after K=4. Return every K and score actually tried.

The two packs use the same task and different coordinates/targets. Assign KNIME/A→Texera/B, KNIME/B→Texera/A, Texera/A→KNIME/B, Texera/B→KNIME/A evenly. Do not let participants choose their order. Both tools start with connected loop controls and prepared computation. KNIME uses Counting Loop Start and Variable Condition Loop End from the outset. Texera uses CSV File Scan, Loop Start, the prepared clustering body, Loop End and Sort. There is no native K-means descriptor in the tested Texera version. See SHORT_REFERENCE.md for matched field guides.

## Single Google Form

The organizer owns the form in the user's UCI Google account. Seven sections: welcome, first-tool configuration, first-tool adaptation, first-tool saving, second-tool configuration, second-tool adaptation/saving, final feedback. All response items are optional so an interrupted participant can skip ahead and submit. Next is navigation, not submission. Submit once at the end. Do not treat an online saved draft as a researcher-visible response.

Collect participant ID, assigned sequence, prior KNIME/Texera/Python experience and involvement in WAFFLE development. For each task collect outcome (completed/time limit/stopped/technical problem/not attempted), elapsed seconds or not recorded, the requested result, and ease from 1 (very difficult) to 7 (very easy). For adaptation also record own workflow versus supplied fallback. Save the sweep before editing it; do not overwrite it. In KNIME, press Ctrl+S before every Export so it contains the latest controls. Upload both exports per tool, including incomplete work; an upload failure can be described instead. Collect outside help, waits and interruptions once per tool. Final questions compare ease for the two activities, with Same and Cannot judge options, and an optional reason.

Participation is voluntary. Google upload questions require sign-in and associate the uploading account with the files; do not promise anonymous collection. Keep raw responses and exports private; report aggregate results. Do not publish responses or invite teammates automatically. Setup links and participant-specific copies must be supplied before starting.

## Timing and interpretation

Start a stopwatch on reading each task and stop at completion or four minutes, including execution waits. Answering/export time uses the separate allowance. Stop the session at 35 minutes and submit what is available. A technical block is not a usability failure. Preserve estimated or missing times as such.

If configuration fails, save it before taking the supplied correct sweep fallback. Record fallback assistance and exclude it from independent combined success, while reporting its adaptation outcome separately. Use only the supplied help; record any additional assistance. Do not reveal correctness feedback between platforms.

Primary outcome: correct independent configure-and-adapt completion within eight elapsed task minutes per tool. Report paired counts (both, Texera only, KNIME only, neither), failures, timeouts and technical exclusions explicitly. Compare paired times among independently correct pairs with their denominator; show correctness regardless of time too. Report ease/preferences including ties. These prepared tasks measure basic loop configuration/adaptation, not full workflow development, expressiveness, or general superiority.

## Readiness

Generate with `study.py prepare <fresh-folder> --short`. The native check set contains 24 runs: two platforms, two packs, and six cases (single-iteration scaffold; visible/changed-input sweep; visible/immediate-stop/unreached-target adaptation). Historical 36-run captures remain the old three-task design. GUI rehearsal and a teammate timing pilot are separate checks. Repeat setup/import/run/export on the hosted Texera server before recruiting; a localhost check does not validate that deployment.
