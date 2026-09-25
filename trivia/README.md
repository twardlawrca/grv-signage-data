# GRV Trivia round (`trivia/bank.json`)

The boards play a **timed trivia round** from the campaign overlay (v1.31+): an intro card, then `count`
multiple-choice questions (a gold timer drains for `questionSec`, then the correct card lights up for
`revealSec` with an optional "Did you know?" line), then a closing card that names the next round.
The campaign is `cmp-grv-trivia` in `campaigns.json` (exported from the portal); the questions live here.

## How a round is chosen
- One seeded permutation of the whole bank per day (seed = the date + `version` + the bank size), so
  **every board shows the same round at the same time** and a question does not come back the same day
  until the bank is used up. The next day is a fresh shuffle.
- Round *k* of the day takes the next `count` questions; the four options are shuffled per question with
  the same seed, so the correct letter varies and still matches across boards.
- Cadence and hours come from the campaign, not from this file: `schedule.everyMin` (e.g. 45),
  `schedule.dailyFrom` / `dailyTo` (HH:MM, facility time). Change them in the portal and re-export, or
  edit `campaigns.json` directly; boards re-read the feed within 10 minutes and this bank within 30.

## Adding or editing questions
Each item:
```json
{"id": "space-031", "cat": "Space", "q": "Which planet is closest to the Sun?",
 "options": ["Mercury", "Venus", "Earth", "Mars"], "answer": 0, "fact": "optional, under 130 characters"}
```
- `answer` is the index of the correct option (the boards shuffle the four).
- Question under 118 characters, options under 40, so nothing wraps off the card at 1080p.
- General knowledge only, family-friendly, verifiable. Nothing about alcohol or other substances, gambling,
  violence, medical advice, politics or religion. The fleet screening list (`screen.json`) is enforced.
- Run the lint before pushing; it fails on any problem:
```bash
cd ~/grv-signage-data && python3 trivia/lint.py && git add trivia/bank.json && git commit -m "trivia: ..." && git push
```
- Bump `version` (any string; the date is fine) when you add questions so the day's shuffle re-seeds.

This is separate from the root `trivia.json`, which feeds the 1.x **Brain Break** wellness panel.
