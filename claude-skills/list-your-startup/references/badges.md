# Adding directory badges to the user's site

Many free directory listings are approved only while the directory's badge or link
sits on the product's homepage. A bot checks for it at submit time, and some sites
re-check later. These steps add every agreed badge in one change, keep the links
working for the directories, and keep the site looking intentional.

## Before touching anything

- Stay inside the badge budget the user agreed in step 2 of the skill. If a
  directory you want to add isn't on the list they confirmed, ask first.
- Collect every badge's exact code before editing the site, so the change goes in
  as one PR or snippet and needs one deploy.
- Keep the `href` exactly as issued, including listing-specific paths and utm
  parameters. Some directories check for their exact URL.
- Use the image `src` they give you. Hotlinking it is normal and expected. Pick the
  light or dark variant that suits the site's footer.
- Some directories want a plain text link instead of an image, for example
  `<a href="https://example-directory.com">Example Directory</a>`. Render it as text
  in the same row.

## What the links must look like

- A plain followed link: no `rel="nofollow"`, `rel="sponsored"` or `rel="ugc"`. Those
  make verification fail or remove the value of the listing. `target="_blank"` with
  `rel="noopener"` is fine.
- Visible on the homepage. A sitewide footer counts, because it renders on the
  homepage.
- Images at one consistent height (32 px works well in a footer). Set width from each
  image's own aspect ratio to avoid layout shift, use `loading="lazy"`, and give each
  one alt text like `<Product> on <Directory>`.

## Option A: pull request (site repo is available)

1. Find the shared footer component or partial, and read the site's design rules
   (DESIGN.md, CLAUDE.md, a tokens file) so the new row matches.
2. Add one small "Featured on" row, driven by a data array so later badges are a
   one-line change. Framework-neutral sketch:

```js
// One entry per directory. Keep href exactly as the directory issued it.
// Entries without img render as a plain text link.
const featured = [
  { name: "Example Directory", href: "https://example.com/listing/your-product", img: "https://example.com/badge.svg", w: 119, h: 32 },
  { name: "Text Link Directory", href: "https://example-two.com" },
];
```

```html
<div class="featured-on">
  <h2>Featured on</h2>
  <div class="badges">
    <!-- for each entry -->
    <a href="{href}" target="_blank" rel="noopener">
      <img src="{img}" alt="{Product} on {name}" width="{w}" height="{h}" loading="lazy" decoding="async">
    </a>
    <!-- or, when there is no img -->
    <a class="text" href="{href}" target="_blank" rel="noopener">{name}</a>
  </div>
</div>
```

```css
.featured-on .badges { display: flex; flex-wrap: wrap; align-items: center; gap: .6rem .7rem; }
.featured-on a { display: block; line-height: 0; }
.featured-on img { height: 32px; width: auto; }
.featured-on a.text { line-height: 32px; }
```

3. Add a short code comment saying the hrefs must stay as issued, because removing or
   changing a badge can get a listing pulled.
4. Build and preview locally. Check that every image loads (`naturalWidth > 0`), and
   that the row wraps cleanly at phone width.
5. Commit on a new branch and open a PR. Its description should list each directory,
   its DR, and why the badge is there. Ask the user to merge.

## Option B: snippet (no repo access, or user prefers)

Give the user one block of HTML containing every badge, plus a one-line CSS hint, and
ask them to paste it into their site footer. Wait for them to say it's live.

## Verify it's live, then verify on each directory

Poll the live homepage until every href is present. Bust the CDN cache with a query
parameter:

```bash
for i in $(seq 1 20); do
  n=$(curl -s "https://example.com/?cb=$RANDOM" | grep -o 'href="https://\(dir-one.com\|dir-two.com\)[^"]*"' | sort -u | wc -l)
  echo "try $i: $n found"; [ "$n" -ge 2 ] && break; sleep 15
done
```

Then go back to each directory and click its "Verify badge" button. If one fails,
check its exact expected href against the live HTML before retrying.

## Tell the user

- Which badges are now on their site and why each is there.
- That removing or changing one can get that listing removed.
- Which directories only give a dofollow link if the product ranks in the top 3, so
  the user can judge whether each badge is worth keeping.
