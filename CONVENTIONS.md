# Project Conventions

Guidelines for LLMs and contributors working on this repo.

## Structure

- Each project lives in its own subfolder at the repo root
- Each subfolder must have its own `README.md`
- The root `README.md` must list every project under `## Projects`

## GitHub Pages

This repo has GitHub Pages enabled, served from the `main` branch root.

- Base URL: `https://albybarber.github.io/ai-play-projects/`
- When a project includes HTML that can run in a browser, link to the live demo in both the root and subfolder READMEs
- Demo URL pattern: `https://albybarber.github.io/ai-play-projects/<subfolder>/<file>.html`

## Git

- `.DS_Store` is in `.gitignore` — never commit it
- Write clear commit messages describing the change
- Push to `main` after committing
