# Claude production prompt — BlackSwan real website demo

You are producing a finished BlackSwan product demo video for Mirza's pitch. This is a recording/editing task.
The product is frozen: do not add features, restyle the site, change detectors, manually edit data or rebuild/redeploy it.
Normal records created by the authorized chat and fresh investigation are expected; preserve prior evidence and reviews.

Read `AGENTS.md`, `CLAUDE.md`, the newest `docs/notes/current-state.md`, DEC-038 and
`plans/2026-10-11-demo-video-plan.md`. Treat the original 25-second storyboard as superseded.
Work from `C:/Users/mirza/Desktop/Hackathon/project-50k-app` on `product/build` for repository reads.
Put video work in a new directory under `C:/Users/mirza/Desktop/Hackathon/recordings/`; preserve old recordings.

## Confirmed requirements

- Final duration 40–50 seconds; target 45. Landscape 16:9, 1920×1080, H.264 MP4 with broadly compatible pixel format,
  AAC sound-effects track and fast-start metadata. Use a consistent frame rate supported by the captured footage.
- Upbeat editing with **short Turkish captions, no voiceover and no music**. Subtle sound effects only.
- All product imagery must be recorded from the actual website at `http://127.0.0.1:3070`.
  No Figma recreation, synthetic UI, screenshots invented in code, replaced HTML, altered data, mock AI, fabricated
  task states, retyped model answers or fake letter-by-letter streaming. Captions/crops/zoom/cursor emphasis may
  support the real recording but must not fabricate product content or hide an unfavorable state.
- The main subject is AI agent orchestration. Show the actual expanded workflow, Nöbetçi workspace, Sıra queue,
  and Raportör. Also show THF's real anomaly findings and `/review`.
- The video must contain real clicks, scrolling and typing. A slideshow of static images is insufficient.
- Mirza explicitly chose a **fresh THF investigation followed by its actual completed result**. Record the real
  processing time and shorten it transparently in editing. Do not imply that the complete pipeline ran in 45 seconds.

## Preflight, without changing the product

1. Confirm real 3070/8770 are healthy and the analysis date is 12 September 2026. Never use synthetic 3071/8771 footage.
   Do not touch fallback 3060/8767/8768, switch the main branch, stop Docker services, run `down -v`, or run a host
   production build. Do not edit `raw/`, frozen protocols/detectors, registered sealed files or the frozen handoff.
2. Use an existing authorized browser session or the already authorized QA login helper. Never inspect/print secrets,
   ask for the OpenAI key, record a login/password, expose account menus, or save session credentials with deliverables.
   The existing screenshot helper may be inspected as code and reused, but never open its credential file in agent tools.
   Helper location: `C:/Users/mirza/AppData/Local/Temp/claude/c--Users-mirza-Desktop-Hackathon-project-50k/fcb59ff2-d20e-4984-b01d-14d47f0bf736/scratchpad/shots/snap.mjs`.
3. Verify THF's current case, whether a human has reviewed it, team pause state and available chat/user-request budget.
   The team has a protected user reserve; do not silently raise caps or reset counters. If a human-reviewed case cannot
   be reopened, preserve that decision and report the blocker instead of modifying the database.
4. Inspect real available controls and choose a readable browser zoom/viewport. Do not modify app CSS or its DOM content
   for the recording. Keep the real date, findings, statuses and source context visible.
5. Check installed capture/edit tools (Playwright/Chromium and ffmpeg are available in the working environment).
   Prefer using these existing tools. Media tooling can live in the separate recording folder; do not alter application
   dependencies. Keep raw recordings and audio outside Git. Avoid Playwright's default output cleanup on other QA files:
   always set a dedicated output directory for this video.

## Capture the real causal chain

Use one browser operator. In parallel, other workers may prepare the caption timing, original/licensed subtle effects
and export checks. They must not manipulate the browser or launch additional investigations.

1. Establish THF at `/funds/THF`, including the selected date and the real anomaly/finding explanation.
2. Click the swan to reveal the expanded agent workflow. Its parallel Hipotezci/Şüpheci branch should be readable.
3. In Raportör, use a new conversation if needed to keep the recorded story clear. Type exactly:
   **`Bu fonu ekibe yeniden incelet.`** Press Enter and record the genuine acknowledgement.
4. Verify that this actually queues a fresh investigation; record the new case reference privately for linkage checks,
   never as an on-screen label. Do not confuse an old report, a repeated request or a model's acknowledgement with a
   completed investigation. Require a new case ID, an opening timestamp after this submission, and an actual tool
   outcome `opened` or `reopened`. `raised` only prioritizes an existing case and `unchanged` can be a deduplicated
   request; neither establishes the fresh run chosen for this video. If the chat does not queue fresh work, inspect
   the real outcome; do not fabricate success or manually reset the old case.
5. Click Nöbetçi's work tab and scroll its actual task/input/activity view. Show real scanning history or current work.
   Do not imply that Nöbetçi initiated the user-requested re-review. No manufactured activity animations.
6. Click Sıra and show the actual THF request/stages at their real priority/state. Capture genuine task progress.
7. Allow the new case to finish. Preserve the raw continuous material and its real chronology. Verify that the completed
   case and valid report belong to the recorded request. No replacing old messages or resetting timestamps.
8. Capture the new completed case/report and one readable explanation. If a plain Raportör summary helps, AFTER completion
   ask **`Yeni incelemenin en önemli bulgusu ne, neden insan incelemesi gerekiyor?`** and record the actual response.
   The final edit need not show this second typing sequence; show a readable genuine passage instead of rushing it.
9. Navigate to `/review`, locate the new THF proposal, and verify it is from the new investigation. Expand its real rationale
   or evidence. Match the case's new decision to the displayed proposal; ticker alone is insufficient. End with the
   human-review controls visible. **Do not submit ACCEPT/OVERRIDE/REJECT**: Mirza has authorized
   demonstrating the workflow, not making a human decision on his behalf.

The actual output determines the footage. Do not rerun repeatedly to obtain a preferred conclusion. If the fresh run
fails, cannot complete within existing authorization/budget, or produces no usable verified report, preserve the take
and tell Mirza the concrete blocker. Never silently substitute an earlier report as fresh work.

## Proposed edit: 45 seconds

| Time | Scene | Caption |
|---|---|---|
| 0–6 | THF,date,finding; small real scroll | Bir bulgu, incelemeyi başlatır. |
| 6–10 | Swan click, expanded agent graph | Ajanlar birlikte çalışır. |
| 10–16 | Fresh Raportör request, Enter, real acknowledgement | Raportöre bir istek. |
| 16–21 | Nöbetçi workspace, recent work/input scroll | Nöbetçi'nin çalışma alanı |
| 21–26 | Sıra, actual THF request and stages | İstek, ekibin sırasına girer. |
| 26–27 | Cut over actual waiting, on real website footage | Bekleme süresi kısaltıldı. |
| 27–37 | New completed report and one readable finding/answer | Bulgular, kaynaklarıyla açıklanır. |
| 37–45 | Review page,new THF proposal,expanded rationale,human controls | Son söz insanda. |

Keep the waiting-cut caption visible across the adjacent shots for2–3seconds. If any footage is accelerated, label it
`Hızlandırılmış kayıt` while accelerated. Avoid inventing a loading sequence or masking actual errors/state changes.
If trimming is needed, shorten the establishing/graph shot before sacrificing the completed result and human review.

## Style and audio

- Real dark website throughout, clean browser capture, purposeful cursor moves, restrained crops/zooms and crisp cuts.
  No invented title card, marketing end card, decorative fake dashboards or extra stock/results tour.
- One short caption at a time, readable on a projector and clear of findings, dates, controls and source citations.
- Hold important actual text for3–4seconds. Do not pack a full timeline, full report and second typed question into
  the same short shot. Keep the report explanation truthful; no investment advice, wrongdoing or validated prediction claim.
- Use approximately5–7 quiet sound cues: opening/tab clicks, brief actual typing/Enter, one soft transition whoosh,
  optionally a small tick when real completion is visibly established. No music, voiceover, alarm or constant typing noise.
- Generate simple original effects or use licensed ones and record their source/license. Mix conservatively, avoid
  clipping, and listen to the entire output. Do not imply a false product completion through sound.

## Deliver and verify

Deliver `BlackSwan-demo-final.mp4` in the new recording folder, plus caption/edit timing and a short production note.
Retain the original raw takes and audio. Keep credentials/session state out of the deliverable and all real footage out of Git.

Check the actual exported file, not just the edit preview:
-40–50seconds,16:9/1080p, stable frame rate, compatible H.264/AAC, no black/blank frames or clipped audio;
- all required screens and real click/scroll/type interactions are visible;
-Nöbetçi and Sıra are both shown; the fresh request links to the new completed report and review proposal;
- captions do not cover evidence; one passage of the real response and the human controls are readable;
- omitted waits/acceleration are disclosed; no old activity is presented as newly live;
- no login/secrets, synthetic-stack data, invented response, unapproved human review or fabricated success claim;
- the running product remains healthy, its code is unchanged, and only normal authorized chat/investigation activity
  was recorded; prior evidence, decisions and human reviews remain preserved.

Report the final duration, resolution, output path, what real investigation was captured, how time was condensed,
and any limits. Do not claim the video exists or passed checks before it has been rendered and inspected.
