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
- Contributions and pull requests cover GitHub's default past-year window.
  Current streak uses that calendar's UTC dates, permits an unfinished today,
  and is bounded by that window. It is not an all-time longest streak.
- Repository and star counts include all owned public repositories, including
  forks, with pagination. Followers are the public profile count. Private
  repository details are neither requested nor published. Local runs should
  use a public-data-only token if private aggregates must also be excluded.
- Failed API requests leave the previous generated files untouched. The workflow
  reports failure rather than replacing stats with an error image.

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
