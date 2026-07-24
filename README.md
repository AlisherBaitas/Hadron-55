# Hadron-55

`Hadron-55` is the data-processing suite for the **HADRON-55** cosmic-ray
detector at the Tien Shan mountain station (3,340 m, Kazakhstan). It cleans
raw `.dat` event files coming off the detector's 25 scintillator channels —
dropping calibration runs, empty/noisy events, and per-channel outliers — and
ships that filtering logic through three interfaces built around one shared
core: a **desktop GUI** for batch folder processing, a **Telegram bot + REST
API** for on-demand filtering, and a **public marketing/demo site** (EN/RU/KZ)
that runs the filter live in the browser.

```bash
$ python bot.py
🌐 Flask запущен на порту 8080
🤖 Бот запущен...
```

## Project objective

Each detector run produces `.dat` files full of `|EVENT` blocks — one block
per cosmic-ray event, with 21 high-sensitivity channel lines (`back_1`,
`front_g`, `middle_3`, …) plus scintillator veto lines. A lot of that data is
noise: calibration/test runs, events where the scintillator vetoes fired on
mostly-zero readings, single-channel spikes, and events that are almost
entirely near-zero. The project's job is to filter that down to clean,
analyzable events, and to make the filter available however the person on the
other end needs it:

1. **Filtering core (`bot.py` / `src/hadron55_gui.py`).** Shared logic that
   splits a file into `|EVENT … #` blocks, drops calibration/test blocks and
   blocks failing the scintillator zero-ratio check, replaces per-channel
   outliers with neighbor averages, and drops events that are still mostly
   near-zero after cleaning.
2. **Telegram bot + Flask API.** Send a `.dat` file to the bot (or `POST` it to
   `/filter`) and get back the filtered file plus total/kept/dropped counts —
   no install required beyond the bot itself.
3. **Desktop GUI (`src/hadron55_gui.py`).** A Tkinter app for batch-processing
   a whole folder of `B######.dat` files at once, with a live log and
   progress bar, for people working directly with station data offline.
4. **Public site (`index.html`).** A static, fully localized (EN/RU/KZ)
   landing page describing the station and pipeline, with a live demo section
   that uploads a file straight to the Flask API and lets you download the
   filtered result — deployed at [hadron-55.kz](https://hadron-55.kz).

## Features

**Filtering core**

- Splits raw `.dat` content into `|EVENT … #` blocks and processes each
  independently.
- Drops calibration/test events (matched by keyword in the event header).
- Drops events where both the high- and mid-sensitivity scintillator lines are
  ≥70% zero (`ZERO_RATIO_THRESHOLD`) — a dead/vetoed event.
- Requires all 21 target channel lines to be present, or the event is dropped.
- Replaces outlier readings with neighbor-average smoothing (ratio + absolute
  thresholds) and suppresses isolated noise surrounded by zeros.
- Drops events that are still ≥90% near-zero (0-7) after cleaning.
- Reports total / kept / dropped counts for every run.

**Telegram bot**

- `/start`, `/help` commands with usage instructions.
- Accepts a `.dat` document, filters it, and returns the cleaned file with a
  kept/dropped summary — or a plain message if nothing survived filtering.

**REST API (Flask, embedded in `bot.py`)**

- `GET /` — health check.
- `POST /filter` — multipart file upload, returns the filtered `.dat` as a
  streamed attachment (no temp files), with `X-Total-Events` /
  `X-Kept-Events` / `X-Dropped-Events` headers and CORS enabled for the demo
  site.
- Filename sanitized against path traversal and header injection; 500 MB
  upload cap with a proper `413` handler.

**Desktop GUI**

- Pick an input folder and an output folder, batch-processes every
  `B######.dat` file, with a scrolling log, indeterminate progress bar, and
  guards against missing/identical/unwritable folders.

**Public site**

- Full EN/RU/KZ localization with a language switcher (persisted to
  `localStorage`).
- Sections covering the station, the pipeline, a live filter demo (talks to
  the Flask API), and the team.
- Canvas starfield background and animated pulse visualization; responsive,
  no build step.

## Technologies used

- **Python 3.11**, `aiogram==3.4.1` for the Telegram bot, `flask==3.0.0` for
  the REST API.
- **Tkinter** (standard library) + `numpy` for the desktop GUI.
- **Vanilla HTML/CSS/JS** for the public site (no build step, no framework).
- **Nixpacks** (`nixpacks.toml`) for deployment.

## Authors

- **Alisher Baitas** — GUI, Flask API, Telegram bot, deployment and
  repository architecture; QA (vulnerability detection, fault tolerance, test
  coverage).
- **Hanni** — core filtering algorithms: outlier detection, scintillator
  screening, and event classification.

## Usage: How to Run

### Prerequisites

- **Python 3.11** or newer.
- A Telegram bot token (only required to run the bot; the Flask API alone
  doesn't need one — see below).

### Environment setup

```bash
pip install -r requirements.txt
export BOT_TOKEN="your-telegram-bot-token"
export PORT=8080  # optional, defaults to 8080
```

| Variable   | Default | Description                                    |
| ---------- | ------- | ----------------------------------------------- |
| `BOT_TOKEN`| _empty_ | Telegram bot token. Required — process exits without it. |
| `PORT`     | `8080`  | Port the embedded Flask API listens on.          |

### Running the bot + API

```bash
$ python bot.py
🌐 Flask запущен на порту 8080
🤖 Бот запущен...
```

This starts the Flask API in a background thread and the Telegram bot's
polling loop in the foreground. Send a `.dat` file to the bot in Telegram, or:

```bash
curl -F "file=@run.dat" http://localhost:8080/filter -o filtered_run.dat
```

### Running the desktop GUI

```bash
pip install numpy
python src/hadron55_gui.py
```

Pick an input folder (containing `B######.dat` files) and an output folder,
then click **Run Filter** — results are written per-file to the output
folder with a summary log.

### Viewing the public site

`index.html` is a static file — open it directly in a browser, or serve it
locally:

```bash
python -m http.server 8000
```

Point the demo section at a running Flask API instance (`bot.py`) to test the
live filter from the browser.

## The filtering pipeline

Given a raw `.dat` file, each `|EVENT … #` block goes through, in order:

1. **Calibration/test check** — dropped if the header line mentions
   `calibr` or `test`.
2. **Scintillator zero check** — dropped if both `scinti : high sensitivity`
   and `scinti : midi sensitivity` lines are ≥70% zeros.
3. **Completeness check** — dropped unless all 21 `TARGET_LABELS` channel
   lines are present.
4. **Outlier replacement** — per channel, values that spike relative to
   their neighbors (ratio/absolute thresholds) are replaced with the
   neighbor average; isolated non-zero readings surrounded by zeros are
   zeroed out.
5. **Near-zero check** — dropped if ≥90% of all cleaned readings are still
   in the 0-7 range.

Surviving events are reassembled in original order and returned/written with
the total/kept/dropped counts the bot, API, and GUI all report.

## API endpoints

| Method | Path      | Body                          | Purpose                                  |
| ------ | --------- | ------------------------------ | ----------------------------------------- |
| GET    | `/`       | —                               | Health check (`{"status":"ok"}`).         |
| POST   | `/filter` | multipart form, field `file`   | Filter an uploaded `.dat` file, stream back the cleaned file. |
| OPTIONS| `/filter` | —                               | CORS preflight.                           |

**Status codes:** `200` OK · `400` missing file / wrong extension · `404`
unknown route · `405` wrong method · `413` file over 500 MB · `500` unexpected
processing error.

## Folder structure

```
Hadron-55/
├── bot.py                       # Telegram bot + embedded Flask REST API (shared filter core)
├── src/
│   └── hadron55_gui.py          # Tkinter desktop GUI for batch folder processing
├── drafts/                      # exploratory/legacy filtering scripts (pre-bot.py)
│   ├── filter_sc_zero_events.py
│   ├── filtr.py
│   └── scinti_non_zero.py
├── tests/
│   └── test_api.py              # Flask API test suite (aiogram mocked out)
├── index.html                   # public EN/RU/KZ landing page + live filter demo
├── requirements.txt              # aiogram, flask
├── nixpacks.toml                 # deployment build config
├── CNAME                         # hadron-55.kz
└── LICENSE                       # MIT
```

## Testing

```bash
python tests/test_api.py -v
```

The suite mocks `aiogram` before importing `bot.py` so it can exercise the
real Flask app in isolation. It covers health/404/405 routing, bad-request
handling (missing file, wrong extension), valid filtering runs (including a
500-event stress test), response headers, filename sanitization against path
traversal and header injection, absence of leaked temp files, and 10
concurrent requests against `/filter`.