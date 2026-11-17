# GRV TV games (`games/`)

Two puzzle banks for the campaign overlay's **game rounds** (overlay v1.35+). They share the trivia slot: the
`cmp-grv-trivia` campaign's slide carries `props.rotate = ["trivia", "scramble", "riddle"]`, so each timed slot
(`schedule.everyMin`, 45 min, 7:00 AM to 9:00 PM) plays the next type in turn. No extra interruptions to the boards.

| File | Round | Per round |
|---|---|---|
| `scramble.json` | **Word Scramble**: clue + shuffled letter tiles, gold bar, tiles slide into order, a short fact | `count` 8, `wordSec` 15, `revealSec` 6 |
| `riddles.json` | **Riddles & Brain Teasers**: riddle, gold bar, the answer in a gold plate + one-line why | `count` 6, `riddleSec` 20, `revealSec` 7 |

Options live on the trivia slide: `props.scramble = {count, wordSec, revealSec}`, `props.riddle = {count, riddleSec, revealSec}`.

## How a round is chosen
Same as trivia: one seeded permutation of each bank per day (seed = date + type + `version` + bank size), so every board
plays the same round at the same time and an item does not repeat the same day. A board that has not read a bank yet
plays trivia in that slot instead (never a blank round). Boards re-read the banks every 30 minutes.

## Editing
- scramble item: `{"id", "cat", "word" (4-9 letters A-Z), "scramble" (the exact shuffled order shown), "clue" <= 60, "fact" <= 110}`
- riddles item: `{"id", "kind": "riddle" | "teaser", "q" <= 150, "a" <= 40, "why" <= 120}`
- Family-friendly and recovery-safe: nothing about alcohol, drugs or medication, smoking, gambling, violence, death,
  illness, crime, politics, religion or romance, and no double meanings (craving, high, trip, shot, fix, clean...).
- Bump `version` when you change items (it reseeds the daily order). Run the lint; it fails on any problem:
```bash
cd ~/grv-signage-data && python3 games/lint.py && git add games/ && git commit -m "games: ..." && git push
```
