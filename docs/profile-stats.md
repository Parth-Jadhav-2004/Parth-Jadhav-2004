# Profile statistics

## Why the old card was delayed

On November 6, 2026, the existing `streak-stats.demolab.com` endpoint returned
`Cache-Control: public, max-age=86400`: a 24-hour freshness lifetime. GitHub's
image proxy and browser caches can retain that image instead of requesting a
new one on every visit. A successful image response does not mean live data.

## How the replacement works

- GitHub Actions requests a refresh at minute 17 every six hours (UTC).
  Scheduled jobs can be delayed; this is not a real-time counter.
- `scripts/update_stats.py` reads GitHub's API using the built-in workflow token;
  no external service account or personal access token is needed.
- Light and dark SVGs live in this repository. Each refresh changes the image
  URL's content-derived revision so an old proxy cache entry is not reused.
- Cards show their generation time. GitHub's own contribution processing can
  still lag behind an event; the timestamp is not an upstream freshness guarantee.
- Contributions and both streaks cover GitHub's default past-year calendar
  window. Pull requests use the profile's total pull request count, not the
  past-year contribution count.
- Current streak counts consecutive active UTC dates backwards from today.
  If today has no contributions yet, counting starts at yesterday instead;
  a zero yesterday breaks that streak. Longest streak is the longest sequence
  of active UTC dates in the supplied past-year calendar, not an all-time record.
  Missing dates break a run, future dates are ignored, and an empty calendar
  gives zero for both streaks. A new year does not extend a streak
  beyond the API calendar window.
- Repository and star counts include all owned public repositories, including
  forks, with pagination. Followers are the public profile count. Private
  repository details are neither requested nor published. Local runs should
  use a public-data-only token if private aggregates must also be excluded.
- Failed API requests leave the previous generated files untouched. The workflow
  reports failure rather than replacing stats with an error image.
- Byte-identical output files are not rewritten. The workflow's existing
  `git diff --cached --quiet` guard prevents empty commits. A changed generation
  timestamp is itself a meaningful card change, even when the counters match.

## Card layout

Both self-contained SVGs use an 840 × 344 viewBox, system fonts, and matching
dark/light palettes. The current streak is the visual hero: a blue progress
ring with an orange flame. Its arc shows current / longest streak, capped at
100%; an empty streak has no progress arc. Longest streak and past-year
contributions complete the hero row. Pull requests, public repos, stars, and
followers are smaller secondary stats.

The card deliberately omits a contribution heatmap because GitHub already
displays one on the profile. Its shorter layout keeps the streak statistics
prominent without duplicating that graph or leaving an empty chart area.
The footer retains the UTC generation timestamp. The API calendar is still
fetched to calculate streaks; no chart-specific data processing is needed.

The README centers the card and its refresh explanation. Tech icons are
individual 40px-high images, not a comma-separated multi-icon `srcset`.
On verification, the previous strip endpoint returned all 13 icons in both
themes, including when queried with literal `&amp;` separators (which changed
the layout, not the icon count). That does not reproduce the reported GitHub
rendering issue at the service itself. All 13 single-icon URLs returned valid
SVGs; separate images avoid depending on multi-icon `<picture>` handling.

Run **Actions → Refresh profile stats → Run workflow** for an on-demand update.
Locally, authenticate `gh` and run `python3 scripts/update_stats.py`.
GitHub can disable schedules on public repositories after extended inactivity;
re-enable the workflow in Actions if needed. Standard hosted runners for public
repositories use GitHub's free Actions allocation policy.

## Free alternatives reviewed

- [GitHub Readme Streak Stats](https://github.com/DenverCoder1/github-readme-streak-stats):
  specialized streak images, but the current hosted endpoint advertises a full
  day of caching. Replacing colors or adding a fixed query string does not make
  it live.
- [GitHub Readme Stats](https://github.com/anuraghazra/github-readme-stats):
  free hosted cards with documented caching and best-effort availability.
  Its maintainers recommend generating static cards with GitHub Actions for
  reliability; the built-in token supports public stats.
- [GitHub Profile Summary Cards](https://github.com/vn7n24fzkq/github-profile-summary-cards):
  free, open-source contribution and language cards. Its documented generator
  setup requires a personal access token and also notes raw-image caching.

The selected approach follows the static-card pattern without adding another
hosted dependency or a long-lived secret. A visitor badge was intentionally not
restored: image requests are not a reliable count of unique profile visitors.
