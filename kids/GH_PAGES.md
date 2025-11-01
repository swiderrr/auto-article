# GitHub Pages deployment for this Hugo site

This repository contains the Hugo site in the `kids/` subdirectory. The included GitHub Actions workflow `./.github/workflows/deploy-gh-pages.yml` builds the site and deploys the generated files to the `gh-pages` branch.

What the workflow does
- Runs on pushes to `main` and on manual dispatch.
- Builds Hugo from the `kids/` folder and outputs to a temporary `kids_public` directory.
- Pushes the contents of `kids_public` to the `gh-pages` branch using the `GITHUB_TOKEN`.

Required repository settings
- In the repository Settings → Pages, set the source to the `gh-pages` branch and the root (/) folder.
- Ensure GitHub Actions are enabled for the repository.

Optional secrets
- The workflow uses the built-in `GITHUB_TOKEN`. No extra secrets are required for a basic setup.

Notes
- If you use a custom domain, set it in the Pages settings or add `CNAME` into the `kids_public` output.
- If your site expects a specific `baseURL`, you can either update `kids/hugo.toml` or modify the workflow to pass `--baseURL` to `hugo`.

Local testing
- To build locally from the repo root:

  cd kids
  hugo --minify

This will populate `kids/public` locally; the workflow writes to `kids_public` to avoid clashing with the repo's own `public/`.
