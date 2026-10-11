# BlackSwan demo video plan

Status: format and fresh-investigation choice confirmed by Mirza; shot order is the proposed edit for discussion.
Decision: DEC-038. This replaces the older 25-second storyboard; product code remains frozen.

## Creative direction

Target 45 seconds, acceptable 40–50. Landscape 16:9, export 1920×1080. Short Turkish captions, no voiceover and
no music. Make the rhythm upbeat through purposeful clicks, concise cuts, readable holds and subtle sound effects.
Use the actual dark-theme website on `http://127.0.0.1:3070` throughout. No standalone fabricated intro/end cards.
The BlackSwan brand already present in the website supplies the branding.

About 31 seconds focus on the agent team. THF establishes the reason for the work, and human review closes the story.

## Proposed 45-second sequence

| Time | Actual website footage and interaction | Short caption |
|---|---|---|
| 0–6 s | `/funds/THF`: show THF, the 12 September 2026 analysis date and the real triggered finding. Scroll slightly to its explanation/source context. | `Bir bulgu, incelemeyi başlatır.` |
| 6–10 s | Click the swan; show the expanded five-role graph, including the parallel Hipotezci/Şüpheci branch. | `Ajanlar birlikte çalışır.` |
| 10–16 s | On Raportör, type `Bu fonu ekibe yeniden incelet.` and press Enter. Show the actual acknowledgement of the queued request. | `Raportöre bir istek.` |
| 16–21 s | Click Nöbetçi's card. Show its real workspace, inputs and recent scan/case activity, with one small scroll. | `Nöbetçi'nin çalışma alanı` |
| 21–26 s | Click Sıra. Focus on the real THF request and its actual queued/running stages. | `İstek, ekibin sırasına girer.` |
| 26–27 s | Cut between real footage before and after the omitted processing wait. Keep the caption readable across the adjacent shots for about 2–3 seconds. | `Bekleme süresi kısaltıldı.` |
| 27–37 s | Show the newly completed case/report, then one readable Raportör explanation or code-test finding. If a second question is needed, record it after completion; the edit can omit that typing and show its genuine answer. | `Bulgular, kaynaklarıyla açıklanır.` |
| 37–45 s | Navigate to `/review`; bring the new THF proposal into view, expand its rationale/evidence and hold on the human-review controls. Do not submit a review. | `Son söz insanda.` |

The Nöbetçi shot demonstrates actual scanning work. It must not imply that Nöbetçi initiated this user-requested
re-review. The new request, queue item, completed case and review proposal must be linked by actual runtime records.
The analysis date and the real time of the new investigation are different; preserve both when the site shows them.

## Recording and editing

- Record a longer real session, potentially several minutes, then edit it down. The 45 seconds is the video length,
  not a promise about model or pipeline latency.
- One browser operator owns the recording and paid requests. Audio/caption preparation and export checks can run
  in parallel. Avoid concurrent browser operators or duplicate investigations.
- Prefer a 1600×900 or 1920×1080 browser viewport. Use ordinary browser zoom if necessary and modest crops/zooms
  of real footage for projector readability. Preserve the actual page content and causality.
- Aim for 3–4 seconds of readable hold on the main finding, completed explanation and human-review rationale.
  Do not try to show a full report, a second typing sequence and a detailed case timeline all in one short shot.
- Use the actual response. Never script, replace or retype a model answer for the recording. Never replay an old
  case as a newly running one, and never animate fake states or fake streaming.
- Prefer cuts over accelerated footage. If any interval is sped up, label that interval `Hızlandırılmış kayıt`.
- The closing shot remains the real review page. No extra stock/results tour is proposed within this short edit.

## Sound effects

Use roughly 5–7 quiet cues, aligned to actual events: a soft click when opening the team, a brief typing/Enter cue,
soft tab clicks, one restrained transition whoosh, and optionally a small completion tick only when the real
completed state is visible. No alarm, dramatic failure sound, soundtrack or constant keyboard noise.
Use original/generated or appropriately licensed effects, with no clipping or intrusive volume.

## Production checks and handoff

Before capture, verify the real product, historical date, unpaused team, THF's current case/review state, and remaining
user-request/chat budget. Existing recorded output is a source reference, not a substitute for the chosen fresh run.
The UI and API may take time to finish the new review; do not increase budgets, rewrite human decisions or reset data
to manufacture a recording. A failed/unavailable fresh run must be reported before choosing another approach.

Keep raw takes, final MP4, audio and edit metadata outside Git, in a new folder under
`C:/Users/mirza/Desktop/Hackathon/recordings/`. Preserve previous recordings. Save no credentials/session tokens in the
deliverable. Claude's detailed execution prompt is `plans/2026-10-11-claude-demo-video-prompt.md`.
