# auto-article — Hugo + Article Generator

This repository contains a Hugo site and a small Python tool to generate articles with AI and images.

Notes about a recent template fix

- Problem: Hugo failed to build with an error like:
  "unable to cast maps.Params{...} of type maps.Params to string" coming from the `absURL` call in `layouts/partials/head/seo.html`.

- Cause: `Site.Params.defaultImage` in `kids/hugo.toml` is a table (map) describing image settings, not a simple string path. The template expected a string and passed the map to `absURL`, causing the cast error.

- Fix implemented: The `seo.html` partial now safely extracts a string image path from several possible places:
  - `.Params.featured_image` if provided (string)
  - `.Site.Params.defaultImage.article.src` if present
  - `.Site.Params.defaultImage.opengraph.src` if present
  - fallback to `.Site.Params.favicon`

This prevents passing a map to `absURL` and makes the template robust to the project's param structure.

How to run the site

1. From the project root, start a local Hugo server for the `kids/` site:

```bash
cd kids
hugo server --gc -D
```

2. To generate an article (dry-run or using OpenAI keys):

```bash
python3 kids/tools/generate_article.py
```

Make sure to set environment variables if you want full functionality (place them in `kids/.env`):

- `OPENAI_API_KEY` — API key for OpenAI
- `PEXELS_API_KEY` — API key for Pexels image downloads

If you run into template issues, inspect `kids/layouts/partials/head/seo.html` and `kids/hugo.toml` to ensure the `params` values are compatible with your theme.

If you'd like, I can also:

- Update `kids/hugo.toml` to include `defaultImage.article.src` and/or `defaultImage.opengraph.src` sample paths.
- Replace `datetime.utcnow()` usages in the generator with timezone-aware datetimes.
- Add a small test to validate the Hugo templates via the Hugo build in CI.


Note about GitHub Pages deployment
---------------------------------

This repository contains the Hugo site in the `kids/` subdirectory. A GitHub Actions workflow has been added at `.github/workflows/deploy-gh-pages.yml` which builds the Hugo site from `kids/` and deploys the generated output to the `gh-pages` branch. See `kids/GH_PAGES.md` for more details.

