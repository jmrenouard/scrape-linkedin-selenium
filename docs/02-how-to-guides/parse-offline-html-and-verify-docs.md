# Parse Offline HTML and Verify Docs

Use this procedure to extract JSON from saved HTML files and verify repository documentation.

CAUTION: Never commit `LI_AT` session cookies or credentials to Git. Exposed cookies grant account access.

## Prerequisites

- Local clone of `scrape-linkedin-selenium` with Python 3, `beautifulsoup4`, and `click` installed.
- Saved LinkedIn HTML file in a readable local directory.

NOTE: Review supported flags and API attributes in [CLI, API, and Parser Reference](../03-reference/cli-api-and-parser-matrix.md).

## Steps

1. Confirm that you work on a saved HTML file and not a live URL.
2. Run the CLI help command to confirm available flags.

```bash
python -m scrape_linkedin.cli --help
```

3. Run the CLI with `-i` and `-o` to parse one saved HTML profile cleanly.

```bash
python -m scrape_linkedin.cli -i test/html_files/profile.html -a skills -o /tmp/skills.json
```

4. Check the generated JSON file to confirm expected keys and values.
5. Delete temporary `scrapeli_*.log` files if any appear in your directory.
6. Run the offline test suite from the repository root.

```bash
python -B -m unittest discover -s tests -p "test_*.py" -v
```

7. If any link, snippet, or Mermaid test fails, fix the Markdown file and repeat Step 6.

## Validation

Run both checks from the repository root to verify code syntax and documentation compliance:

```bash
python -B -m compileall -q scrape_linkedin examples test
python -B -m unittest discover -s tests -p "test_*.py" -v
```

Verify that both commands exit with status `0` and zero failed tests.

## Rollback

Revert edited documentation or configuration files with Git if validation fails after a change:

```bash
git checkout -- README.md .gitignore docs/ tests/
```
