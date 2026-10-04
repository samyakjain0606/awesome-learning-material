# Browser playbook

These techniques are for submitting forms through the Claude in Chrome tools. Each
section exists because the failure it describes happens often on directory sites.

## Contents

1. Session setup
2. Filling forms reliably
3. Special inputs
4. Google sign-in
5. Gmail: magic links, confirmations, sending
6. Reading values without leaking tokens
7. Things to leave alone
8. After submitting

## 1. Session setup

- Call `tabs_context_mcp` first. Create your own tabs with `tabs_create_mcp` and don't
  take over the user's existing tabs.
- Use one tab per directory. Navigating a tab that holds a half-filled form loses it.
- Batch predictable steps (navigate, wait, click, type, screenshot) with
  `browser_batch` so each directory costs fewer round trips.
- Take small screenshots (`scale` 0.4 to 0.5) to find layout. Use `find` or
  `read_page` with `filter: "interactive"` to get element refs. Click by ref where you
  can, since refs survive layout shifts better than coordinates.

## 2. Filling forms reliably

**Wait for the page to finish loading before typing.** Many directory sites are
single-page apps. Text typed before the page finishes loading gets wiped, or lands in
the wrong field when the page re-renders or scrolls. Wait 3 to 6 seconds after
navigation. If fields come back empty, wait and retype.

**Read every value back before submitting.** After filling, run something like:

```js
[...document.querySelectorAll('form input, form textarea, form select')]
  .filter(e => e.type !== 'hidden' && e.type !== 'file')
  .map(e => (e.name || e.id || e.placeholder) + ' = ' +
       (e.type === 'checkbox' || e.type === 'radio' ? e.checked : String(e.value).slice(0, 60)))
  .join('\n')
```

This catches text that went into the wrong field, such as a description appended to
the maker name. It also catches values the page silently reset.

**Watch for prefilled fields.** Sites often prefill name, username or email from your
Google profile. Select all (`cmd+a` or `ctrl+a`) in the field before typing, or
your text gets appended to the prefill.

**When typing doesn't stick,** set the value with the native setter and fire the
events the framework listens for:

```js
const el = document.querySelector('textarea[name=description]');
const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, 'text');
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
```

Using the input prototype on a textarea throws "Illegal invocation". If the setter
approach still doesn't stick, click the field and type instead.

**Use character counters.** If a field shows "0/60" after you typed, the page didn't
register the input.

## 3. Special inputs

- **Rich-text editors** (contenteditable, often with H1/H2 toolbars): focus with
  `document.querySelector('[contenteditable=true]').focus()`, then type. A single
  newline makes a new paragraph. Confirm with `innerText` and a word count when the
  site enforces a minimum.
- **Custom dropdowns and comboboxes:** open the visible control and click the option.
  A hidden native `<select>` may already hold a value while the visible control still
  says "Select…". Trust the visible control, because that is what validation reads.
- **Tag inputs:** type one tag, press Enter, repeat. Check the tag count afterwards.
- **Category chips and checkboxes:** click each, then confirm selection state with
  `aria-checked`, `aria-pressed` or `data-state`.
- **File uploads:** use `file_upload` with the ref of the `input[type=file]`. Never
  click the file input itself, because the native file dialog it opens can't be
  driven. Upload one file input at a time. Two uploads in quick succession can drop
  one. Confirm each upload landed by checking the preview image's `naturalWidth`, or
  that a hidden field now holds a CDN URL. If one fails, retry with a smaller copy of
  the image.
- **Date pickers with slot counts:** pick the earliest date that shows free slots,
  unless the user asked for a specific launch day.

## 4. Google sign-in

1. Click the site's "Continue with Google" or "Sign in with Google".
2. On the account chooser, click the account the user named.
3. On the consent screen ("Google will allow <site> to access…"), click Continue.
4. Wait about 5 seconds and confirm you're back on the site and signed in.

Notes:

- Screenshots of accounts.google.com are sometimes briefly denied. Wait a couple of
  seconds and try again.
- Some sites open Google sign-in as a popup window outside the tab group, where the
  tools can't reach it. Tell the user, or look for a redirect-based sign-in link.
- If the site returns an error after Google sign-in (for example a server
  configuration error), try once more. Then fall back to the site's email magic link
  if it has one, or record the site as broken.
- Never enter a password, and never choose "Use another account" to type
  credentials.

## 5. Gmail: magic links, confirmations, sending

**Finding the email.** Navigate to `https://mail.google.com/mail/u/0/#search/from%3A<domain>`
and open the newest message. Check the account in the window title matches the one
the user named.

**Opening a sign-in or confirm link without printing its token.** Links in Gmail are
often wrapped in `google.com/url?q=`. Unwrap the link and navigate the tab itself:

```js
const a = [...document.querySelectorAll('div[role=main] a[href]')]
  .find(a => /confirm|verify|sign in/i.test(a.innerText));
let h = a.href;
if (h.includes('google.com/url')) h = new URL(h).searchParams.get('q');
setTimeout(() => { location.href = h; }, 100);
'navigating'
```

Then continue in that tab. Don't paste one-time tokens into chat.

**Sending an email-only submission** (only with the user's permission):

1. Click Compose. If the compose window opens minimised, click its title bar.
2. Type the recipient, then the subject, then the body.
3. Before sending, confirm the recipient chip and subject with JavaScript or a zoomed
   screenshot.
4. Send, wait for "Message sent", and log the time.

## 6. Reading values without leaking tokens

Tool output may be blocked when it contains URLs with query strings or cookie-like
data. Print `host + pathname` and the names of the query parameters, not their
values:

```js
const u = new URL(someHref);
u.host + u.pathname + ' params:' + [...u.searchParams.keys()].join(',')
```

To read a badge embed snippet, parse it with `DOMParser`. Then report the `<a>` href
and `<img>` src the same way, and the full values only if they have no secrets
(utm params are fine).

## 7. Things to leave alone

- **Honeypot fields.** These are inputs labelled "leave this field blank", or hidden
  or off-screen fields with names like `website_url`, `email_confirm` or
  `phone_confirm`. Filling them gets the submission silently dropped. Confirm they're
  still empty before you submit.
- **Captchas and bot checks,** however trivial. Hand them to the user.
- **Upsell steps** ("Activate now", "Fast track", "Featured", coupon timers). Pick the
  free option ("Wait in line", "Free launch", "Basic") and confirm any "are you sure"
  dialog in favour of free.
- **"Support the community" steps** that ask you to vote on other launches, and
  "free premium" offers that need posts or blogs about the directory. These are the
  user's decision.
- **AI autofill buttons.** If a site generated the copy anyway, replace it with the
  approved text.

## 8. After submitting

- Capture the confirmation page text and the final URL path. Directories often show
  an id or slug ("projects/<slug>", "status/<id>").
- Look for the listing's own status page (pending, scheduled, live) and any stated
  review time, launch date or queue position. These go into the report.
- If the site saved a draft instead of submitting, record where the draft lives and
  what's needed to finish it.
- Close the tab once the directory is fully logged, unless the user needs it for a
  hand-off.
