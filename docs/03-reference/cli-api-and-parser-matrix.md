# CLI, API, and Parser Reference

Verified interface specification derived directly from `scrape_linkedin/cli.py`, `Profile.py`, `Company.py`, `Scraper.py`, and `test/`.

## `scrapeli` CLI Options (`scrape_linkedin/cli.py`)

| Flag | Type / Choice | Default | Description |
| :--- | :--- | :--- | :--- |
| `--url` | `TEXT` | `None` | Full profile or target URL |
| `--user` | `TEXT` | `None` | Profile username (`linkedin.com/in/<user>`) |
| `--company` | `TEXT` | `None` | Company slug (`linkedin.com/company/<company>/`) |
| `-a`, `--attribute` | `[personal_info\|experiences\|skills\|accomplishments\|interests\|recommendations]` | `None` | Return a single attribute from `Profile` |
| `-i`, `--input_file` | `PATH` (must exist) | `None` | Local HTML file path parsed by `Profile(html)` |
| `--headless` | Boolean flag | `False` | Apply `HEADLESS_OPTIONS` to Chrome WebDriver |
| `-o`, `--output_file` | `PATH` | `None` | Destination JSON file (prints via `pprint` if omitted) |
| `--driver` | `[Chrome\|Firefox]` | `Chrome` | Selenium WebDriver backend |
| `--help` | Flag | — | Show help message and exit (`-h` is not registered) |

> **Logging behavior:** `cli._init_logging()` creates `scrapeli_YYYY-MM-DD-HH-MM-SS.log` in the current working directory (`*.log` is ignored by `.gitignore`).

## `Profile` Attribute Schema (`scrape_linkedin/Profile.py`)

`Profile.attributes` exposes `6` properties (`to_dict()` exports all `6` keys):

| Property | Structure / Keys |
| :--- | :--- |
| `personal_info` | `name`, `headline`, `company`, `school`, `location`, `summary`, `image`, `followers`, `email`, `phone`, `connected`, `websites` |
| `experiences` | `jobs` (`title`, `company`, `date_range`, `location`, `description`, `li_company_url`), `education`, `volunteering` |
| `skills` | List of `{"name": str, "endorsements": str\|0}` sorted descending by numeric endorsements |
| `accomplishments` | `publications`, `certifications`, `patents`, `courses`, `projects`, `honors`, `test_scores`, `languages`, `organizations` |
| `interests` | List of `.pv-entity__summary-title` text strings |
| `recommendations` | `{"received": [...], "given": [...]}` (`text`, `date`, `connection`: `{relationship, name, li_id}`) |

## `Company` Constructor and Properties (`scrape_linkedin/Company.py`)

Constructor signature: `Company(overview, jobs, life, insights)` (`4` required HTML strings; empty string `""` skips unused tabs).

| Property | Current Output |
| :--- | :--- |
| `overview` | `{"description": str\|None, "image": str, "name": str\|None, "num_employees": int\|None, "metadata": dict}` |
| `jobs` | `None` (placeholder stub) |
| `life` | `None` (placeholder stub) |
| `insights` | Dict containing `"6m change"`, `"1y change"`, and `"2y change"` from `.org-insights-module__summary-table` |

## `Scraper` Parameters and Auth Environment (`scrape_linkedin/Scraper.py`)

| Parameter / Env Var | Default | Purpose |
| :--- | :--- | :--- |
| `LI_AT` env var / `cookie` arg | `None` | LinkedIn session cookie (`cookie` overrides `LI_AT`) |
| `LI_EMAIL` + `LI_PASS` | Unset | Optional login form credential pair |
| `driver` / `driver_options` | `Chrome` / `{}` | Selenium WebDriver class and keyword options (`HEADLESS_OPTIONS` adds `--headless`) |
| `scroll_pause` / `scroll_increment` / `timeout` | `0.1` / `300` / `10` | Incremental scroll timing (seconds, pixels) and `WebDriverWait` timeout |

## Test Suite Audit Matrix

| Suite | Mode | Baseline Result (`Python 3.14` + `bs4>=4.7`) | Notes |
| :--- | :--- | :--- | :--- |
| `tests/test_docs_tutorials_howtos.py` | Offline | **Passes 100%** | Validates compilation, offline CLI/parsers, code fences, Diátaxis, STE, links, Mermaid |
| `test/utils_test.py` | Offline | `4/5` pass | `test_text_or_default` uses CSS `.1` rejected by `soupsieve` |
| `test/parsers_test.py` | Offline | `0/3` fail | `Company()` uses obsolete 3 args; `profile.html` retains pre-2021 top-card DOM classes |
| `test/scrapers_test.py` | Live Selenium | Not safe offline | Opens Chrome against `linkedin.com`; skipped in offline verification |
