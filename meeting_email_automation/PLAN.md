# Meeting Notes → Email Automation: Plan

**Goal:** After a meeting, automatically take synced Granola notes and draft (or send) an email with clear next steps — either to yourself as a follow-up reminder or as a reply to the founder you met with.

---

## 1. How Granola Works (and Where Notes Live)

Granola is a macOS-native AI meeting notes app. Key facts that shape this design:

- Notes are stored locally at `~/Library/Application Support/Granola/` as structured JSON files
- After a meeting ends, Granola processes the audio transcript and writes/updates a note file — this is the "sync" moment that triggers the workflow
- Granola surfaces the meeting title, participants, transcript, and a structured AI-generated summary with bullets and action items
- Granola has no native public webhook API as of early 2026, so triggering from the cloud directly is not possible without a local intermediary

This means: **the trigger must originate on your Mac**, and then you can choose how much of the processing happens locally vs. in the cloud.

---

## 2. Workflow Overview (End-to-End)

```
[Meeting ends]
      ↓
[Granola syncs note to ~/Library/Application Support/Granola/]
      ↓
[File system watcher detects new/modified note file]
      ↓
[Note text is extracted + enriched with metadata]
      ↓
[Claude API drafts email: subject, body, next steps]
      ↓
[Email is created as Gmail draft OR sent directly]
      ↓
[You review and hit send (or it goes automatically)]
```

---

## 3. Key Components

| Component | Role |
|---|---|
| **Granola local storage** | Source of meeting notes (JSON files on disk) |
| **File system watcher** | Detects when a new note appears after a meeting |
| **Note parser** | Extracts the structured content from Granola's JSON format |
| **Claude API** | Reads the note and drafts the email (subject + body + action items) |
| **Gmail API** | Creates a draft or sends the email |
| **Email context logic** | Decides: is this a reply to the founder, or a self-memo? |

---

## 4. Implementation Options

There are two viable architectures. The core tradeoff is: **fully local (simple, immediate)** vs. **local trigger + cloud processing (more robust, observable, shareable)**.

---

### Option A: Fully Local Mac Script (Recommended to Start)

**How it works:**

1. A lightweight daemon runs permanently on your Mac (via `launchd`, macOS's native process supervisor)
2. It uses `watchdog` (Python library) or `fswatch` (CLI) to watch the Granola notes directory
3. When a new or modified note is detected and is "settled" (a brief cooldown to wait for Granola to finish writing), the script runs
4. The script reads and parses the note JSON, calls the Claude API, and uses the Gmail API to create a draft or send
5. A macOS notification fires to tell you the email was drafted

**Pros:**
- No cloud infrastructure needed — runs entirely on your machine
- No latency from network hops between trigger and processing
- Works offline for note detection (only needs internet for Claude + Gmail calls)
- Easy to iterate: it's a single Python script
- Secrets (API keys) stay on your machine in a `.env` file or macOS Keychain

**Cons:**
- Only runs when your Mac is on and you're logged in
- No logging dashboard or retry visibility unless you add it
- Harder to share or run on behalf of someone else

**Tech stack:**
- Python 3 script
- `watchdog` or `fswatch` for file watching
- `anthropic` Python SDK for Claude
- `google-auth` + `google-api-python-client` for Gmail
- `launchd` plist for keeping it alive as a background service

---

### Option B: Local Trigger + Google Cloud Run (More Robust)

**How it works:**

1. Same local file watcher on your Mac detects a new Granola note
2. Instead of processing locally, it `POST`s the raw note content to a **Cloud Run endpoint** (a small HTTP service you deploy once)
3. Cloud Run handles: calling Claude API, deciding email context, calling Gmail API, and creating the draft
4. Cloud Run returns a success/failure response; the local script fires a notification

**Pros:**
- Processing is off your machine — your Mac just sends a small payload and is done
- Easy to add logging, retries, and monitoring via Google Cloud Logging
- The Cloud Run service can be reused or extended (e.g., triggered by other note sources in the future)
- You can inspect runs, see errors, and replay failures in the GCP console
- Can later add a simple UI or webhook from other tools

**Cons:**
- Requires a GCP project, Cloud Run service, and IAM setup
- Cold starts on Cloud Run (mitigated with minimum instances = 1, but adds cost ~$5–10/mo)
- Secrets need to be stored in Google Secret Manager
- Still requires the local watcher — you can't fully eliminate the Mac-side component
- Slightly more operational overhead to set up and maintain

**Tech stack:**
- Python 3 local watcher script (`watchdog` or `fswatch`)
- Cloud Run service: Python/FastAPI with a single `POST /process-note` endpoint
- `anthropic` SDK (inside Cloud Run)
- `google-auth` + `google-api-python-client` for Gmail (inside Cloud Run)
- Google Secret Manager for API keys
- Optional: Cloud Logging for observability

---

### Option C: What About a "Cloud Skill" in Claude Code?

A **cloud skill** (a Claude Code skill invoked manually from the CLI) is a third option. In this model:

- You run `/process-meeting-notes` (or similar) from your terminal after a meeting
- Claude Code reads the latest Granola note from disk, drafts the email, and either prints it or pushes it to Gmail
- No automation daemon needed — it's fully manual-trigger

**This is the right choice if:**
- You want control over when the email is drafted (not every meeting needs a follow-up)
- You don't want any background processes running
- You'd rather review the email in your terminal before anything touches Gmail

**This is the wrong choice if:**
- You want the workflow to be truly automatic and hands-off after meetings

---

## 5. Recommendation

**Start with Option A (fully local), and evolve to Option B if needed.**

Here's the rationale:
- The local watcher is required regardless of which option you pick — Granola has no cloud webhook
- Option A gets you the full workflow with the least moving parts
- If you find yourself wanting logs, retries, or to extend the service to other inputs, wrap the processing logic in a Cloud Run service at that point
- The code is nearly identical between A and B — the only difference is where the note-parsing + Claude call happens

---

## 6. Email Context Logic (Self vs. Founder Reply)

One of the most important design decisions is: **how does the system know whether to send the email to you or to the founder?**

Proposed logic (in priority order):

1. **Calendar participant check**: If the meeting has exactly 2 participants (you + founder), assume it's a founder meeting and draft the email as a reply to them. If 3+ participants, default to a self-memo.
2. **Manual tag in Granola**: If you add a tag like `#founder-followup` or `#self-memo` to the note, the script respects that.
3. **Fallback**: Always create a Gmail draft (never auto-send) so you review before anything goes out. You can add auto-send as an opt-in later.

The Claude prompt will need to adapt its tone based on recipient:
- **Founder reply**: Professional, warm, concise, action-item focused, closes the loop on what was discussed
- **Self-memo**: Bullet-point tasks, deadlines if mentioned, no pleasantries

---

## 7. Granola Note Structure (What We're Working With)

The Granola notes directory needs to be explored to confirm the exact JSON schema, but expected fields include:

| Field | Description |
|---|---|
| `title` | Meeting name (usually pulled from calendar) |
| `participants` | List of attendees with names/emails |
| `date` / `created_at` | Meeting timestamp |
| `transcript` | Raw transcript text |
| `summary` | AI-generated summary paragraphs |
| `action_items` | Granola-extracted action items (if present) |
| `notes` | Your own typed notes during the meeting (if any) |

The Claude prompt will use `summary`, `action_items`, `notes`, and `participants` as its primary inputs. The full `transcript` will be passed only if summary is sparse.

---

## 8. The Claude Prompt (Design Intent)

The prompt will instruct Claude to:

1. Identify all concrete **next steps and commitments** from the note
2. Determine who owns each action item (you vs. the founder)
3. Draft an email that:
   - Has a clear, specific subject line (not "Following up on our meeting")
   - Opens with a brief recap of what was decided
   - Lists your action items and theirs as distinct sections
   - Ends with a proposed timeline or next touchpoint if mentioned
4. Keep it concise — founders get short emails, not essays
5. Match the tone to any previous context if provided

---

## 9. Open Questions to Resolve Before Implementation

1. **Granola note path + schema**: Need to inspect the actual `~/Library/Application Support/Granola/` directory to confirm file format and when files are written vs. updated
2. **Gmail OAuth flow**: Will use OAuth 2.0 with offline access — need to decide whether to store the refresh token in macOS Keychain, a local `.env`, or Google Secret Manager (Cloud Run path)
3. **Founder email detection**: Granola may or may not surface participant emails — need to verify. If not, we may need to match against Google Calendar API instead
4. **Auto-send vs. draft-only**: Start with draft-only. Add a `--send` flag later once you trust the output quality
5. **Deduplication**: The watcher may fire multiple times as Granola writes the file incrementally. Need a "settle time" (e.g., wait 30s after last modification before processing) and a record of already-processed note IDs

---

## 10. Suggested Build Order

1. Explore the Granola notes directory and document the exact JSON schema
2. Write the note parser (extract the fields we care about)
3. Write and test the Claude prompt with a sample note
4. Set up Gmail API credentials and test creating a draft
5. Wire up the file watcher and test end-to-end locally
6. Add launchd plist to keep the watcher alive (Option A complete)
7. (Optional) Extract the Claude + Gmail logic into a Cloud Run service (Option B)
8. (Optional) Add a CLI skill for manual-trigger use (Option C)

---

## 11. Files This Project Will Create

```
meeting_email_automation/
├── PLAN.md                    ← this file
├── watcher.py                 ← local file system daemon
├── note_parser.py             ← parses Granola JSON into structured data
├── email_drafter.py           ← calls Claude API, returns email content
├── gmail_client.py            ← Gmail API wrapper (create draft / send)
├── config.py                  ← env var loading, constants
├── requirements.txt           ← anthropic, watchdog, google-auth, etc.
├── com.ali.meeting-emailer.plist  ← launchd plist for auto-start on login
└── cloud_run/                 ← (optional, Option B)
    ├── main.py                ← FastAPI app with POST /process-note
    └── Dockerfile
```
