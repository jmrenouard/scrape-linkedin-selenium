# Tutorial: Offline HTML Profile and CLI Parsing

In this tutorial, you will load local HTML fixtures in Python, inspect extracted skills and jobs with `Profile`, construct a `Company` parser object, and run `scrapeli --help` without opening a browser or sending network requests.

## Prerequisites

- A local checkout of `scrape-linkedin-selenium` on branch `master`.
- Python 3 installed with `beautifulsoup4` and `click` (see [requirements.txt](../../requirements.txt)).
- Zero LinkedIn credentials (`LI_AT` is not needed for offline HTML files).

## Step 1: Inspect Available CLI Flags

Check the Click help output to verify all supported options and confirm `--headless` and `--company` support:

```bash
python -m scrape_linkedin.cli --help
```

Expect exit code `0` displaying `--url`, `--user`, `--company`, `-a, --attribute`, `-i, --input_file`, `--headless`, `-o, --output_file`, `--driver`, and `--help`.

## Step 2: Parse a Local Profile HTML Fixture

Run a Python snippet against `test/html_files/profile.html` to extract structured data offline:

```python
from scrape_linkedin import Profile

with open("test/html_files/profile.html", "r", encoding="utf-8") as handle:
    profile = Profile(handle.read())

print("Skills count:", len(profile.skills))
print("Top skill:", profile.skills[0])
print("Jobs count:", len(profile.experiences["jobs"]))
```

Expect `39` parsed skills sorted by descending endorsement count (`Leadership` first with `24`) and `8` job records.

## Step 3: Instantiate `Company` with Four HTML Arguments

`Company` requires four HTML strings (`overview`, `jobs`, `life`, `insights`). Supply empty strings for subpages you do not inspect:

```python
from scrape_linkedin import Company

with open("test/html_files/facebook_overview.html", "r", encoding="utf-8") as handle:
    company = Company(handle.read(), "", "", "")

print("Logo URL:", company.overview["image"])
print("Metadata keys:", list(company.overview["metadata"].keys()))
```

## Step 4: Run the Offline `unittest` Verification Suite

Execute the automated offline suite to validate parsers, CLI `-i` extraction, documentation links, and Mermaid diagrams:

```bash
python -B -m unittest discover -s tests -p "test_*.py" -v
```

Expect all tests in `tests/test_docs_tutorials_howtos.py` to report `ok`.

## Next Steps

- Follow the repeatable workflow in [Parse Offline HTML and Verify Docs](../02-how-to-guides/parse-offline-html-and-verify-docs.md).
- Inspect full field schemas in [CLI, API, and Parser Reference](../03-reference/cli-api-and-parser-matrix.md).
