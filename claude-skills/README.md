# Claude Code Skills 🧩

Skills you can drop into Claude Code. Each folder is a self-contained skill: copy it
into `~/.claude/skills/` and Claude uses it when your request matches.

---

## 🚀 `list-your-startup`

**TL;DR:** Lists your startup, app or website on free startup directories, launch
platforms and AI-tool directories. Claude works through them in your own Chrome, then
reports where you're listed, what still needs you, and when each listing goes live.

### ⚠️ Requirements (read first)

| Requirement | Why |
|---|---|
| **Claude Code** | Runs the skill |
| **[Claude in Chrome](https://claude.ai/chrome) extension**, connected to Claude Code | Claude fills forms in your real browser, so you can watch and step in |
| **A Google account signed in to that Chrome** (required) | Most directories only allow "Continue with Google" sign-up, and the skill never creates password accounts. It also uses **Gmail** in the same Chrome to open confirmation emails and magic sign-in links, and, if you allow it, to email directories that only accept email submissions |
| Optional: your site's repo open in Claude Code, with `gh` logged in | Lets Claude add "Featured on" badges with a pull request. Without it, you get HTML snippets to paste |

Without the Chrome extension and a signed-in Google account, the skill stops and asks
you to set them up.

### What it does

1. **Builds your listing kit:** taglines, short and long descriptions, categories,
   logo, cover image and screenshots, all taken from your own site or repo. You
   approve it once.
2. **Agrees the plan with you:** how many directories, whether dofollow links
   matter, how many badges you'll accept on your site, and whether it may send
   emails.
3. **Finds and triages directories live,** starting from
   [ScrollLaunch's free-dofollow list](https://www.scrolllaunch.com/directories/free-dofollow)
   or your own. Each one is sorted as open, badge-gated, captcha, engagement-gated,
   paid-only, email-only or dead.
4. **Submits the open ones:** signs in with Google, fills the forms, uploads the
   images, picks the free plan, and confirms by email.
5. **Handles badges:** adds a single "Featured on" footer row for the directories
   you approve (PR or snippet), checks it's live, then verifies each one.
6. **Writes a final report:** submitted listings with go-live dates, what needs you
   (with exact steps), what needs your decision, and what was skipped and why.

### What it will never do

- Solve captchas or bot checks. Those are handed to you.
- Create accounts with a password.
- Pay for anything or enter card details. Upsells are declined.
- Upvote, comment on or vote for other products, or post on social media for you.
- Make up claims about your product.
- Send an email or add a badge to your site without your go-ahead.

### Install

```bash
git clone https://github.com/samyakjain0606/awesome-learning-material.git
mkdir -p ~/.claude/skills
cp -r awesome-learning-material/claude-skills/list-your-startup ~/.claude/skills/
```

Restart Claude Code. To check it's installed, ask "what skills do you have?".

### Use it

In Claude Code, with Chrome open and signed in to Google:

```
List my app https://myapp.com on free startup directories, dofollow preferred.
Use Google sign-in with me@gmail.com. Aim for 15 directories.
```

For long runs, combine it with `/loop` so Claude keeps going and reports at the end:

```
/loop list https://myapp.com on directories and give me a final report
```

### What to expect

- **Time:** roughly 5 to 10 minutes per directory, with many tabs opening in your
  Chrome.
- **Badges:** in 2026 most free dofollow directories require their badge on your
  homepage. The skill asks how many you're comfortable showing before adding any.
  Keep them up afterwards, because removing one can get that listing pulled.
- **Your to-dos:** expect a few, such as a captcha, a password-only sign-up, or an X
  post a directory asks for. Each comes with exact steps in the report.

### Files

```
list-your-startup/
├── SKILL.md                      # The workflow Claude follows
└── references/
    ├── browser-playbook.md       # Reliable form filling, Google sign-in, Gmail links, uploads
    ├── badges.md                 # "Featured on" row by PR or snippet, plus live verification
    └── report.md                 # Running log + final report template
```
