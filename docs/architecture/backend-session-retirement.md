# Backend Session Retirement: Discord → iPhone API Gateway

**Document type:** Architecture Analysis  
**Status:** Authoritative — produced by Task 1 source-code audit  
**Feeds into:** Tasks 2 (endpoint schema), 4 (audio pipeline), 5 (session storage), 6 (auth)

---

## 1. Overview

The current backend is a Discord bot (`app.py`, 1 512 lines). It owns the full learner lifecycle: identity resolution, session state, audio ingestion, AI scoring, and response delivery — all wired through Discord's event loop.

The iPhone app cannot use Discord as a transport. The bot will be **fully retired**. A new **FastAPI HTTP gateway** will replace `app.py` as the sole process owner of the session lifecycle. Every module under `db/`, `engines/`, and `analysis/` is Discord-free and will be reused **unchanged**.

### What changes vs. what stays

| Layer | Discord bot | FastAPI gateway |
|---|---|---|
| Transport | `discord.Client` event loop | HTTP + multipart/form-data |
| Identity | `message.author.id` (Discord snowflake) | New `user_id` issued at registration |
| Audio ingestion | `message.attachments[0].url` → `requests.get()` | Raw bytes in request body |
| Response delivery | `channel.send()` / `message.reply()` | JSON response body |
| ANSI feedback | `` ```ansi\n...\n``` `` Discord code block | Structured word-score array (no ANSI) |
| Audio playback | `discord.File(path)` attached to message | URL or base64 in response body |
| Session state | `user_sessions` dict + `active_sessions` table | Same `active_sessions` table; dict scoped to process |
| Business logic | `engines/`, `analysis/`, `db/` | **Unchanged** |

---

## 2. Current Session Flow (Full Lifecycle Trace)

### 2.1 Boot — session restoration

```
on_ready()
  └─ load_all_sessions()          # db/sessions.py → SELECT * FROM active_sessions
       ↓ JSON-deserialize each row
  └─ user_sessions.update(restored)
  └─ _migrate_legacy_sessions()   # drops rows with unrecognised mode
```

The in-memory `user_sessions: dict[str, dict]` is the runtime cache. It is continuously written back to `active_sessions` via `_persist_session()` and pruned by `_end_session()` + `delete_session()`.

### 2.2 `_init_session(user_id, mode, **kwargs)`

Creates the canonical session dict and stores it in `user_sessions`. Every key present at creation time:

```python
{
  "round": 1, "max_rounds": 5,
  "sentence": "", "new_word": None,
  "fail_count": 0,
  "mode": <mode>,               # ← routing key for all subsequent events
  "drill_words": [], "drill_index": 0,
  "drill_fails": 0, "drill_passed": 0, "drill_done": False,
  "used_sentences": [],
  "session_stats": {"passed_first_try": 0, "needed_drill": 0, "skipped": 0},
  "started_at": datetime.now().isoformat(),
  "scores": [],
  "content_segments_used": 0,
  "round_history": [],
  "difficulty_pref": 1,
  # Curriculum keys
  "curriculum_id": None, "current_phase_id": None,
  "current_phase_number": None, "phase_theme": None,
  "phase_total_content": None, "phase_mastered_count": None,
  # Onboarding keys
  "onboarding_turn": 0,
  "pending_goal_synthesis": None,
}
```

`kwargs` merges over defaults, so `_init_session(uid, "curriculum_practice", sentence=s, content_id=c, ...)` populates the curriculum keys inline.

### 2.3 `_persist_session(user_id)` and `_end_session(user_id)`

```
_persist_session(uid)
  └─ save_session(uid, user_sessions[uid])
       └─ INSERT OR REPLACE INTO active_sessions (user_id, session_data, updated_at)
            VALUES (?, json.dumps(session), datetime('now'))

_end_session(uid)
  └─ session.pop("pending_goal_synthesis")
  └─ user_sessions.pop(uid)
  └─ delete_session(uid)
       └─ DELETE FROM active_sessions WHERE user_id = ?
```

`_persist_session` is called after every meaningful state mutation (mode change, sentence advance, score recorded). `_end_session` is called on `!stop`, session completion, onboarding abort, and goal-change commit.

### 2.4 Session TTL and stale-session cleanup

`_cleanup_stale_sessions()` runs at the top of every `on_message` event:

| Mode | TTL |
|---|---|
| `onboarding`, `awaiting_goal_confirmation`, `awaiting_goal_change_confirmation` | 86 400 s (24 h) |
| `curriculum_practice` | **never evicted** (always skipped) |
| all other modes | 7 200 s (2 h) |

For stale onboarding sessions, `clear_onboarding_conversation(uid)` is called before deletion to remove orphaned `onboarding_conversations` rows.

---

## 3. Session Modes — Triggers and Persistence Points

### 3.1 `onboarding`

**Trigger:** `!go` command when `needs_onboarding(user_id)` returns `True` (i.e. `onboarding_completed_at IS NULL`).

**Flow:**
```
_init_session(uid, "onboarding", onboarding_turn=0)
  └─ _onboarding_chat.start_conversation_async(uid)
       └─ OnboardingChat.start_conversation()
            ├─ clear_onboarding_conversation(uid)     # wipe any prior attempt
            ├─ ollama.chat_sync(messages)              # AI greeting
            └─ add_onboarding_turn(uid, 1, "user", opening_text)
               add_onboarding_turn(uid, 2, "assistant", ai_greeting)
  └─ channel.send(greeting)
  └─ _persist_session(uid)
```

**Subsequent turns:** each plain-text reply (non-command) → `OnboardingChat.submit_user_reply_async()` → `add_onboarding_turn()` → AI chat → either returns `{"type": "question"}` or `{"type": "synthesis", "goal": {...}}`.

**Persistence points:**
- `onboarding_conversations` table: every turn persisted immediately via `add_onboarding_turn`.
- `active_sessions`: persisted after every reply (`_persist_session`).

**Exit condition:** AI returns synthesis → mode transitions to `awaiting_goal_confirmation`.

---

### 3.2 `awaiting_goal_confirmation`

**Trigger:** Automatic transition from `onboarding` when `OnboardingChat.submit_user_reply` returns `type == "synthesis"`.

**State change:**
```python
session["pending_goal_synthesis"] = result["goal"]
session["mode"] = "awaiting_goal_confirmation"
```

**User replies:**
- `yes/y/ok/có/đúng` →
  - `confirm_and_create_curriculum_async(uid, goal)` → `create_curriculum()` (INSERT into `curriculums`) + `mark_onboarding_complete()` (sets `onboarding_completed_at`, `active_curriculum_id` on `users`) + `clear_onboarding_conversation(uid)`
  - `generate_full_phase_async(curriculum_id, ...)` → creates Phase 1 in `phases` + `phase_content`
  - `_end_session(uid)` (user must re-`!go` to start practice)
- `no/n/không` → `clear_onboarding_conversation(uid)` + `_end_session(uid)` (restart onboarding on next `!go`)
- other → prompt re-confirmation, no state change

**Persistence points:** `curriculums`, `phases`, `phase_content`, `users.onboarding_completed_at`, `users.active_curriculum_id`.

---

### 3.3 `awaiting_goal_change_confirmation`

**Trigger:** `!goal change` command (user must already have a completed onboarding + active curriculum).

**State:**
```python
_init_session(uid, "awaiting_goal_change_confirmation")
```

**User replies:**
- `yes` → `archive_curriculum(cur["id"])` (sets `status='archived'`) + `clear_active_curriculum(uid)` + `_end_session(uid)`
- anything else → `_end_session(uid)` (cancels, keeps old curriculum)

**Persistence points:** `curriculums.status`, `users.active_curriculum_id`.

---

### 3.4 `curriculum_practice`

**Trigger:** `!go` command when user has completed onboarding and an active curriculum + phase exists.

**Initialisation:**
```python
_init_session(uid, "curriculum_practice",
  curriculum_id=curriculum["id"],
  current_phase_id=phase["id"],
  current_phase_number=phase["phase_number"],
  phase_theme=phase["theme"],
  phase_total_content=progress["total"],
  phase_mastered_count=progress["mastered"],
  sentence=content["sentence"],
  content_id=content["id"],
)
```

**Primary loop (audio attachment received):**
1. Download audio from Discord CDN → temp file `temp_{uid}_{filename}`
2. Route to sub-mode handler (see `word_drill` below for fail path)
3. `analyze_audio_with_whisper(path, sentence)` → `(score, ansi_feedback, error_details, problem_words, error_types, word_scores)`
4. `log_score`, `log_error_pattern`, `record_word_attempts_batch`, `record_phoneme_errors_batch`, `record_pattern_attempts_batch`
5. `record_phase_content_attempt(content_id, score)` → marks `mastered_at` if score ≥ 80
6. Score routing:
   - `≥ 80` + no weak words → advance to next sentence (`get_next_practice_sentence`)
   - `≥ 80` + weak words + score < 95 → AI borderline-pass decision (may trigger `word_drill`)
   - `< 80` + fail_count = 1 → retry with sample audio
   - `< 80` + fail_count = 2 + problem_words → transition to `word_drill`
   - `< 80` + fail_count ≥ 3 → auto-advance to next sentence
   - `< 80` + fail_count ≥ 6 → force move_on
7. `_persist_session(uid)` after every branch

**Phase exhaustion:** when `get_next_practice_sentence` returns `None` and `should_check_progression` → `evaluate_phase_async` (Ollama) → `apply_decision_async`:
- `advance` → `complete_phase` + `increment_phase_number` + `generate_full_phase_async`
- `repeat` → continue with same phase
- `regenerate` → `mark_phase_regenerated` + `generate_full_phase` (new content, same slot) — capped at 2 regenerations then force-advance

**Persistence points:** `score_history`, `error_patterns`, `word_statistics`, `phoneme_errors`, `speaking_patterns`, `phase_content.attempt_count / last_score / mastered_at`, `phases.status / completed_at`, `curriculums.current_phase_number`, `session_analytics`.

---

### 3.5 `word_drill`

**Trigger:** Auto-transition inside `curriculum_practice` on second consecutive fail with identifiable problem words. Also triggered by AI `drill_words` decision on borderline pass.

**State change:**
```python
session["mode"] = "word_drill"
session["drill_words"] = [<list of words>]
session["drill_index"] = 0
session["drill_fails"] = 0
session["drill_passed"] = 0
```

**Loop:** Per-word `analyze_single_word(path, word)` → pass/fail. On completion, restores `mode` to `curriculum_practice` (or `sentence` for adaptive mode) and re-presents the original sentence.

**Exit conditions:**
- All words drilled → restore mode + present full sentence
- 2 fails on one word → `save_failed_word` + advance drill_index
- pass_rate < 0.5 on full drill → move to next sentence

**Persistence points:** `failed_words`, `word_statistics` (via `record_word_attempts_batch` on each word).

---

### 3.6 Legacy/adaptive modes (`sentence`, `keyword_drill`)

These modes are used by the older adaptive (non-curriculum) path that pulls from the `sentences` table. They remain valid mode values (`_migrate_legacy_sessions` only drops **unknown** modes). In the iPhone API they are lower priority and can be removed in a later iteration; the focus is `curriculum_practice`.

| Mode | Trigger | Notes |
|---|---|---|
| `sentence` | `_advance_to_next_round` in adaptive path | Pulls from `sentences` table via `get_next_sentence` |
| `keyword_drill` | `start_keyword_drill()` when sentence has `new_word` | Requires correct pronunciation of keyword before full sentence |

---

## 4. Database Tables Involved

### 4.1 Session lifecycle tables

| Table | Purpose | Key columns | Written by |
|---|---|---|---|
| `active_sessions` | Persists `user_sessions` dict to survive restarts | `user_id PK`, `session_data TEXT (JSON)`, `updated_at` | `db/sessions.py`: `save_session`, `delete_session` |
| `users` | Learner identity + onboarding gate + level | `user_id PK`, `onboarding_completed_at`, `active_curriculum_id`, `current_level`, `total_sessions`, `streak_count` | `db/users.py` |
| `curriculums` | One per learning goal; survives goal changes via archive | `id PK`, `user_id`, `goal_title`, `goal_description`, `status (active/archived/completed)`, `current_phase_number` | `db/curriculum.py` |
| `phases` | Weekly blocks inside a curriculum | `id PK`, `curriculum_id FK`, `phase_number`, `theme`, `vocabulary JSON`, `milestones JSON`, `status`, `regeneration_count` | `db/curriculum.py` |
| `phase_content` | Individual practice sentences in a phase | `id PK`, `phase_id FK`, `sentence`, `target_phonemes JSON`, `target_words JSON`, `difficulty_score`, `attempt_count`, `last_score`, `mastered_at` | `db/curriculum.py` |
| `onboarding_conversations` | Turn-by-turn onboarding chat history | `user_id`, `turn_number`, `role (user/assistant)`, `content` | `db/curriculum.py` |

### 4.2 Performance tracking tables

| Table | Purpose | Written by |
|---|---|---|
| `score_history` | Raw score per sentence per attempt | `database.py: log_score` |
| `error_patterns` | Aggregated error type + word counts | `database.py: log_error_pattern` |
| `word_statistics` | Per-word attempt/success/avg_score | `db/word_stats.py: record_word_attempts_batch` |
| `phoneme_errors` | IPA phoneme error counts | `db/phoneme_errors.py: record_phoneme_errors_batch` |
| `speaking_patterns` | Sentence-structure mastery | `db/pattern_stats.py: record_pattern_attempts_batch` |
| `failed_words` | "Revenge list" — words needing re-drill | `database.py: save_failed_word, clear_failed_word` |
| `user_progress` | Leitner box levels per (user, sentence) | `database.py: update_sentence_progress` |
| `session_analytics` | Per-session aggregates | `app.py: _write_session_analytics` |

### 4.3 Legacy tables (lower priority for iPhone)

| Table | Notes |
|---|---|
| `sentences` | Fixed sentence bank with difficulty levels; used by adaptive mode only |

---

## 5. Discord-Specific Dependencies (Full Inventory)

These are the concrete patterns that must be replaced by the FastAPI gateway. None of them exist inside `db/`, `engines/`, or `analysis/`.

### 5.1 Bot framework / event loop

| Pattern | Location | What it does |
|---|---|---|
| `discord.Client(intents=...)` | `app.py:60` | Creates the bot process |
| `@client.event / on_ready()` | `app.py:315-338` | Boot hook — session restore, DB stats print |
| `@client.event / on_message(message)` | `app.py:351-1512` | All command + audio routing |
| `client.run(DISCORD_BOT_TOKEN)` | `app.py:1512` | Blocking event-loop start |
| `DISCORD_BOT_TOKEN` env var | `app.py:55` | Auth credential |
| `message.author.id` / `message.author.name` | `app.py:356-357` | User identity derivation |
| `message.content.strip()` | Throughout | Text command parsing (`!go`, `!skip`, etc.) |

### 5.2 Audio ingestion via attachment

| Pattern | Location | Replacement |
|---|---|---|
| `message.attachments` | `app.py:852` | Audio arrives via `multipart/form-data` in HTTP POST body |
| `message.attachments[0]` | `app.py:855` | Single `UploadFile` parameter in FastAPI endpoint |
| `attachment.filename` | `app.py:858, 862` | `file.filename` from `UploadFile` |
| `attachment.url` | `app.py:866` | Not applicable — bytes are already in memory |
| `requests.get(attachment.url).content` | `app.py:866` | `await file.read()` |
| Supported formats: `.ogg`, `.wav`, `.mp3`, `.m4a` | `app.py:858` | Must remain supported; iPhone sends `.m4a` by default |

### 5.3 Message sending / response delivery

| Pattern | File | Replacement |
|---|---|---|
| `await channel.send(text)` | `app.py` (60+ calls) | JSON response field `{"message": "..."}` |
| `await message.reply(text)` | `app.py` (15+ calls) | Same as above (no distinction in HTTP) |
| `await channel.send(file=discord.File(path))` | `app.py` (20+ calls) | Return audio as base64 or presigned URL |
| `discord.File(sample_path)` | `app.py:470, 596, 633, 797, ...` | Audio bytes or URL in response |
| `send_chunked(channel, text)` | `utils/discord_helpers.py` | Not needed — HTTP responses have no 2000-char limit |
| `utils/discord_helpers.py` (entire file) | `utils/discord_helpers.py` | **Retire completely** |

### 5.4 ANSI color codes

| Pattern | File | Notes |
|---|---|---|
| `` ```ansi\n{ansi_feedback}\n``` `` | `app.py:1078` | Discord-specific Markdown block that renders ANSI colors |
| `ANSI_GREEN/YELLOW/RED/GRAY/RESET` constants | `analysis/errors.py:57-61` | Used by `engines/whisper.py` and `engines/azure.py` to build `ansi_feedback` string |
| `ansi_feedback` return value | `engines/whisper.py:130`, `engines/azure.py:107` | Currently a pre-formatted string; must be replaced with structured per-word score array |

**Migration note:** `analysis/errors.py` ANSI constants are imported by `analysis/__init__.py`. They should be retained in-place (they do not harm anything) but the callers in `whisper.py` and `azure.py` must return a structured list instead of (or in addition to) the ANSI string. The iPhone client will render its own colour coding from the structured data.

### 5.5 `ai_brain.py` — Discord coupling in `send_new_word_tutorial`

```python
# ai_brain.py:38-48
await channel.send(f"🆕 **HỌC TỪ MỚI...**")
await channel.send(f"👉 **`{sentence}`**")
await channel.send(file=discord.File(output_audio_path))
```

`send_new_word_tutorial(channel, sentence, new_word)` takes a Discord `channel` object. This function is the **only Discord dependency in `ai_brain.py`**. Its core logic (Ollama tip generation + TTS) is already clean. The FastAPI gateway should inline this logic or replace the signature with `(sentence, new_word) -> dict`.

### 5.6 Temp file naming

All temp files use `user_id` as a collision prefix:
- `temp_{user_id}_{filename}` — uploaded audio
- `curriculum_sample_{user_id}.mp3` — TTS sample for sentence
- `drill_sample_{user_id}.mp3` — TTS sample for single word
- `keyword_sample_{user_id}.mp3`
- `minimal_pair_{user_id}.mp3`
- `chunked_sample_{user_id}.mp3`
- `teacher_sample.mp3` (unscoped — race condition risk under concurrency)

Under the FastAPI gateway these should use a UUID-prefixed temp dir per request, not `user_id`, to avoid concurrency collisions.

---

## 6. Migration Plan: Discord → FastAPI Gateway

### 6.1 Architectural principle

```
BEFORE:
  Discord Event Loop (app.py)
    ├─ Identity: message.author.id
    ├─ Input: message.attachments / message.content
    ├─ State: user_sessions dict + active_sessions table
    └─ Output: channel.send() / discord.File()

AFTER:
  FastAPI HTTP Server (new gateway)
    ├─ Identity: JWT / UUID issued at registration
    ├─ Input: JSON body / multipart audio
    ├─ State: request-scoped session load/save via db/sessions.py
    └─ Output: JSON response body + audio bytes/URL

  db/ engines/ analysis/  ←── unchanged, imported by gateway
```

### 6.2 Module reuse map

| Module | Reuse status | Notes |
|---|---|---|
| `db/sessions.py` | **Reuse as-is** | `save_session`, `load_all_sessions`, `delete_session`, `get_session_by_mode` |
| `db/schema.py` | **Reuse as-is** | `init_db()` called at gateway startup |
| `db/curriculum.py` | **Reuse as-is** | All CRUD unchanged |
| `db/users.py` | **Reuse as-is** | `get_or_create_user`, `needs_onboarding`, `mark_onboarding_complete`, etc. |
| `engines/onboarding_chat.py` | **Reuse as-is** | All methods are sync/async, no Discord imports |
| `engines/curriculum_generator.py` | **Reuse as-is** | No Discord imports |
| `engines/ollama_client.py` | **Reuse as-is** | HTTP-based, no Discord |
| `engines/tts.py` | **Reuse as-is** | Returns local file path; gateway streams bytes |
| `engines/whisper.py` | **Reuse, modify output** | Add structured word-score list return alongside ansi_feedback |
| `engines/azure.py` | **Reuse, modify output** | Same as whisper.py |
| `analysis/phase_engine.py` | **Reuse as-is** | No Discord |
| `analysis/errors.py` | **Reuse as-is** | ANSI constants harmless; keep for internal use |
| `analysis/pronunciation.py` | **Reuse as-is** | Returns tuple including ansi_feedback |
| `ai_brain.py` | **Retire** | Backward-compat wrapper; `send_new_word_tutorial` has Discord arg — refactor or inline |
| `utils/discord_helpers.py` | **Retire** | Discord-only chunking utility |
| `app.py` | **Retire** | Entire Discord event loop |

### 6.3 Session lifecycle mapping (Discord event → HTTP endpoint)

| Discord trigger | HTTP equivalent | Session mode involved |
|---|---|---|
| `!go` (new user) | `POST /session/start` | `onboarding` |
| Plain text reply during onboarding | `POST /onboarding/reply` | `onboarding` |
| `yes`/`no` to goal confirmation | `POST /onboarding/confirm` | `awaiting_goal_confirmation` |
| `!go` (returning user) | `POST /session/start` | `curriculum_practice` |
| Voice attachment | `POST /session/audio` (multipart) | `curriculum_practice` or `word_drill` |
| `!skip` | `POST /session/skip` | `curriculum_practice` |
| `!stop` | `POST /session/stop` | any |
| `!goal change` | `POST /goal/change/init` | `awaiting_goal_change_confirmation` |
| `yes`/`no` to goal change | `POST /goal/change/confirm` | `awaiting_goal_change_confirmation` |
| `!me` | `GET /me` | stateless read |

### 6.4 Session state in HTTP context

The `user_sessions` dict is a process-level cache. Under the gateway:

1. **Every request** loads session from DB at start: `session = load_all_sessions().get(user_id)`  
2. **Every response** persists back: `save_session(user_id, session)`  
3. **No in-memory dict** is maintained between requests (stateless HTTP model)

This is safe because `save_session` uses `INSERT OR REPLACE` (atomic upsert) and all session fields are JSON-serialisable already.

### 6.5 Audio pipeline mapping

```
Discord path:
  message.attachments[0].url
    → requests.get(url).content           # network fetch from Discord CDN
    → open(temp_path, "wb").write(bytes)
    → analyze_audio_with_whisper(temp_path, sentence)
    → os.remove(temp_path)

FastAPI path:
  POST /session/audio (multipart)
    → audio_bytes = await file.read()
    → write to tmp/{request_uuid}/audio.{ext}   # no user_id collision
    → analyze_audio_with_whisper(tmp_path, sentence)
    → os.remove(tmp_path)
```

### 6.6 ANSI → structured word scores

`engines/whisper.py` and `engines/azure.py` must additionally return a `word_scores` list in the following form (already partially available via `word_scores` in the existing return tuple):

```json
{
  "words": [
    {"word": "schedule", "status": "green", "score": 0.92},
    {"word": "the",      "status": "yellow", "score": 0.61},
    {"word": "meeting",  "status": "red",    "score": 0.38}
  ]
}
```

The `ansi_feedback` string can remain as an internal field — it does not need to be sent to the client.

### 6.7 `send_new_word_tutorial` refactor

Replace the Discord-coupled function in `ai_brain.py` with a pure return:

```python
# New signature (engines/tutoring.py or similar)
def build_word_tutorial(sentence: str, new_word: str) -> dict:
    """Returns {"tip": str, "audio_path": str | None}"""
    ...
```

The gateway then streams `audio_path` bytes in the response.

---

## 7. Risk Register

### Risk 1 — Ollama Latency During Curriculum Generation

**Description:** `generate_full_phase_async` makes two sequential Ollama calls (`generate_phase_plan` then `generate_phase_content`). With `gemma4:31b-cloud`, each call typically takes 5–30 seconds on local hardware. Combined, Phase 1 generation can take 30–90 seconds. In the Discord bot this is acceptable because the user sees progress messages. In an HTTP request, a 60-second response will time out in virtually all mobile clients.

**Manifestation points:**
- `POST /session/start` when no active phase exists
- `POST /session/audio` when phase exhaustion triggers `generate_full_phase_async`
- `POST /onboarding/confirm` (Phase 1 generation immediately after goal confirmation)

**Mitigation:**
- Switch to an **async job model**: the endpoint returns `202 Accepted` with a `job_id` immediately; the iPhone polls `GET /jobs/{job_id}` until status = `completed`.
- Alternatively use **Server-Sent Events** (SSE) to stream progress messages.
- Minimum viable: increase gateway timeout to 120 s and show a spinner in the iPhone UI while waiting.

---

### Risk 2 — Concurrent Requests for Single-User Profile

**Description:** The `user_sessions` dict in `app.py` is process-local and synchronously mutated within asyncio coroutines. Discord's event loop serialises message handling per user implicitly. Under HTTP, a user could fire two simultaneous requests (e.g., a retry while a first audio upload is still processing), resulting in a race condition on `save_session` / the in-memory dict.

**Concrete scenario:** User taps "submit" twice → two `POST /session/audio` requests arrive concurrently → both load the same session from DB (same state) → both score the same audio → both call `record_phase_content_attempt(content_id, score)` → attempt_count double-incremented → session dict inconsistency on persist.

**Mitigation:**
- **Per-user request serialisation**: use an asyncio `Lock` keyed by `user_id` in the gateway process. Acquire before loading session, release after saving.
- Alternatively, add an `optimistic_lock_version INTEGER` column to `active_sessions` and reject concurrent writes via `UPDATE ... WHERE version = ?`.
- Ensure the iPhone client disables the submit button while a request is in flight (complementary, not sufficient alone).

---

### Risk 3 — Whisper Model Loading Time

**Description:** `openai-whisper` (`small` model) is loaded at import time in `ai_brain.py` / `analysis/pronunciation.py`. On typical hardware this takes 3–8 seconds and consumes ~500 MB RAM. Under the Discord bot, this is paid once at startup and amortised over the bot's lifetime. Under the FastAPI gateway, if the process is restarted (e.g., after a crash, deploy, or cold start in a container), the first audio request will experience a multi-second delay as the model loads.

**Manifestation:** First `POST /session/audio` after cold start returns slowly or times out. In a serverless/containerised deployment (e.g., Fly.io, Railway), this happens on every scale-to-zero wake.

**Mitigation:**
- Preload Whisper **eagerly** at FastAPI `startup` event rather than at first request: `@app.on_event("startup") async def _load_models(): _ = get_whisper_model()`.
- Add a readiness probe (`GET /health`) that returns `200` only after model load completes; configure mobile client to retry with backoff if health check fails.
- Avoid scale-to-zero if latency SLA is < 5 seconds; use a minimum of 1 warm instance.

---

### Risk 4 — Audio Format Compatibility

**Description:** The Discord bot accepts `.ogg`, `.wav`, `.mp3`, `.m4a` (hardcoded in `app.py:858`). Discord mobile sends `.ogg` (Opus-encoded). iPhone's native `AVAudioRecorder` produces `.m4a` (AAC) or `.wav`. Whisper requires `.wav` or formats supported by ffmpeg. Azure Speech SDK requires `.wav` (PCM 16 kHz 16-bit mono) and uses `pydub`/ffmpeg for conversion (in `engines/azure.py`).

**Concrete risks:**
- iPhone sends `.m4a` (AAC, 44.1 kHz stereo) → Whisper needs ffmpeg to decode → ffmpeg may not be installed in deployment environment.
- iPhone sends `.caf` (Core Audio Format) → not in the accepted list → silently ignored.
- Discord `.ogg` (Opus, 48 kHz) works today because ffmpeg handles it; iPhone `.m4a` should also work but has not been tested.

**Mitigation:**
- Validate accepted MIME types at the gateway level: `audio/m4a`, `audio/wav`, `audio/mpeg`, `audio/ogg`, `audio/x-m4a`.
- Add ffmpeg to deployment `Dockerfile`/`Procfile` as an explicit dependency (it is already needed by `pydub` for Azure conversion).
- Add an integration test that submits a real `.m4a` file from iPhone and asserts a non-error score response.
- Consider normalising all audio to 16 kHz mono `.wav` **before** routing to Whisper or Azure, using a single `_ensure_wav(path)` utility (already exists in `ai_brain.py` / `engines/` for Azure path).

---

### Risk 5 (Bonus) — `teacher_sample.mp3` Race Condition

**Description:** `ai_brain.py:35` writes TTS output to a hardcoded path `teacher_sample.mp3` with no user scoping. Under concurrent multi-user requests this file will be overwritten by a second user before the first user's response sends it.

**Mitigation:** Pass a UUID-scoped output path from the gateway: `build_word_tutorial(sentence, new_word, output_path=f"/tmp/{uuid4()}/sample.mp3")`.

---

## 8. Summary: What the FastAPI Gateway Must Own

The gateway process (replacing `app.py`) is responsible for exactly these concerns that are currently Discord-coupled:

1. **Identity** — map iPhone user token to a `user_id` string stored in `users` table (not a Discord snowflake)
2. **Request routing** — replace `message.content` command parsing with named HTTP endpoints
3. **Audio ingestion** — accept `multipart/form-data`, write to scoped temp dir, delete after processing
4. **Response serialisation** — replace `channel.send()` + `discord.File()` with JSON + audio bytes
5. **Session load/save per request** — call `save_session`/`load_session` on every request (no persistent in-memory dict between requests)
6. **Stale session cleanup** — move `_cleanup_stale_sessions()` to a background task (`asyncio.create_task` or APScheduler) running every 5 minutes
7. **ANSI stripping** — never send `ansi_feedback` to the client; send the structured `word_scores` list instead

Everything else — DB, engines, analysis — is unchanged.
