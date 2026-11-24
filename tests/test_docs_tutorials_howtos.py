"""Offline tests for scrape-linkedin-selenium parsers, CLI, Diataxis docs, STE, links, and Mermaid."""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import json
import logging
import os
import pathlib
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from urllib.parse import unquote

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
REQUIRED_QUADRANTS = ("01-tutorials", "02-how-to-guides", "03-reference", "04-explanation")

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ASCII_BOX_RE = re.compile(r"[┌┐└┘├┤┬┴┼═║╔╗╚╝]|^\s*\+[-+]+\+\s*$", re.M)
MERMAID_TYPES = ("graph ", "flowchart ", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram")

MODERN_PROFILE_HTML = """
<html><body>
  <section class="pv-top-card">
    <h1>Ada Lovelace</h1>
    <div class="text-body-medium break-words">Analytical Engine Architect</div>
    <div aria-label="Current company">Difference Engine Works</div>
    <div aria-label="Education">University of London</div>
    <span class="text-body-small inline break-words">London, United Kingdom</span>
    <img class="pv-top-card__photo" src="https://example.invalid/ada.jpg" />
  </section>
  <section class="pv-about-section">About Pioneering scientific programmer.</section>
  <section class="pv-recent-activity-section-v2"> 1,250 followers </section>
  <section class="pv-contact-info">
    <section class="ci-email"><div class="pv-contact-info__ci-container">ada@example.invalid</div></section>
    <section class="ci-websites"><ul><li><a href="https://example.invalid/notes">Notes</a></li></ul></section>
  </section>
  <section class="pv-accomplishments-section">
    <section class="certifications"><ul><li>Analytical Mathematics</li></ul></section>
    <section class="test_scores"><ul><li>Logic Exam 100</li></ul></section>
  </section>
  <section class="pv-recommendations-section">
    <div class="artdeco-tabpanel">
      <li class="pv-recommendation-entity">
        <div class="pv-recommendation-entity__highlights">Rigorous mathematical notes.</div>
        <a class="pv-recommendation-entity__member" href="/in/charles-babbage/">
          <div class="pv-recommendation-entity__detail">
            <h3>Charles Babbage</h3>
            <p>Inventor</p>
            <p>June 10, 2020, Charles worked directly with Ada</p>
          </div>
        </a>
      </li>
    </div>
    <div class="artdeco-tabpanel"></div>
  </section>
</body></html>
"""

MODERN_COMPANY_OVERVIEW_HTML = """
<html><body>
  <div id="main"><h1>Engine Systems</h1></div>
  <section class="org-top-card">
    <img class="org-top-card-primary-content__logo" src="https://example.invalid/logo.png" />
  </section>
  <section class="org-grid__content-height-enforcer">
    <section><p>Precision mechanical computing tools.</p></section>
    <dl>
      <dt>Website</dt><dd>https://example.invalid</dd>
      <dt>Industry</dt><dd>Computer Software</dd>
      <dt>Company size</dt><dd>501-1,000 employees 640 on LinkedIn</dd>
      <dt>Headquarters</dt><dd>London, UK</dd>
      <dt>Founded</dt><dd>1843</dd>
    </dl>
  </section>
</body></html>
"""

MODERN_COMPANY_INSIGHTS_HTML = """
<table class="org-insights-module__summary-table">
  <tr>
    <td>Headcount</td>
    <td><span></span><span></span><span>+4%</span></td>
    <td><span></span><span></span><span>+9%</span></td>
    <td><span></span><span></span><span>+18%</span></td>
  </tr>
</table>
"""


def _strip_inline_code(line: str) -> str:
    return re.sub(r"`[^`]*`", " ", line)


def _github_anchor_slug(heading_text: str) -> str:
    cleaned = re.sub(r"`([^`]+)`", r"\1", heading_text.strip().lower())
    out: list[str] = []
    for ch in cleaned:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        elif ch in (" ", "-"):
            out.append("-")
    return "".join(out)


def _split_fenced_blocks(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str, str]], bool]:
    non_code: list[tuple[int, str]] = []
    blocks: list[tuple[int, str, str]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_lang = ""
    fence_start = 0
    buf: list[str] = []

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        m = FENCE_RE.match(line)
        if not in_fence:
            if m:
                marker = m.group(1)
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
                fence_lang = stripped[fence_len:].strip().split()[0].lower() if stripped[fence_len:].strip() else ""
                fence_start = lineno
                buf = []
                continue
            non_code.append((lineno, line))
        else:
            if stripped.startswith(fence_char * fence_len) and stripped[fence_len:].strip() == "":
                blocks.append((fence_start, fence_lang, "\n".join(buf)))
                in_fence = False
                buf = []
            else:
                buf.append(line)

    return non_code, blocks, in_fence


@contextlib.contextmanager
def _offline_selenium_stubs():
    """Provide temporary selenium/joblib module stubs when optional live drivers are not installed."""
    missing = [
        "selenium",
        "selenium.webdriver",
        "selenium.webdriver.chrome",
        "selenium.webdriver.chrome.options",
        "selenium.webdriver.common",
        "selenium.webdriver.common.by",
        "selenium.webdriver.common.keys",
        "selenium.webdriver.support",
        "selenium.webdriver.support.expected_conditions",
        "selenium.webdriver.support.ui",
        "selenium.common",
        "selenium.common.exceptions",
        "joblib",
    ]
    injected: list[str] = []
    need_selenium = importlib.util.find_spec("selenium") is None
    need_joblib = importlib.util.find_spec("joblib") is None

    if need_selenium or need_joblib:
        for name in missing:
            if name.startswith("selenium") and not need_selenium:
                continue
            if name == "joblib" and not need_joblib:
                continue
            if name not in sys.modules:
                sys.modules[name] = types.ModuleType(name)
                injected.append(name)
        for name in injected:
            if "." in name:
                parent, child = name.rsplit(".", 1)
                setattr(sys.modules[parent], child, sys.modules[name])
        if need_selenium:
            class _Options:
                def add_argument(self, *args):
                    return None

            class _DummyDriver:
                pass

            sys.modules["selenium.webdriver.chrome.options"].Options = _Options
            sys.modules["selenium.webdriver"].Chrome = _DummyDriver
            sys.modules["selenium.webdriver"].Firefox = _DummyDriver
            sys.modules["selenium.common.exceptions"].NoSuchElementException = Exception
            sys.modules["selenium.common.exceptions"].TimeoutException = Exception
            sys.modules["selenium.webdriver.common.by"].By = object
            sys.modules["selenium.webdriver.common.keys"].Keys = object
            sys.modules["selenium.webdriver.support.ui"].WebDriverWait = object
        if need_joblib:
            sys.modules["joblib"].Parallel = object
            sys.modules["joblib"].delayed = object

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        yield
    finally:
        for name in reversed(injected):
            sys.modules.pop(name, None)


class TestOfflineParsersAndCLI(unittest.TestCase):
    """Validate compilation, offline HTML fixture parsing, utilities, and click CLI paths."""

    def test_py_compile_all_python_sources(self) -> None:
        py_files = sorted([
            *(REPO_ROOT / "scrape_linkedin").glob("*.py"),
            *(REPO_ROOT / "examples").glob("*.py"),
            *(REPO_ROOT / "test").glob("*.py"),
            *(REPO_ROOT / "tests").glob("*.py"),
            REPO_ROOT / "setup.py",
        ])
        self.assertGreaterEqual(len(py_files), 18)
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, src in enumerate(py_files):
                py_compile.compile(str(src), cfile=os.path.join(tmpdir, f"{idx}.pyc"), doraise=True)

    def test_offline_html_parsers_and_utils(self) -> None:
        with _offline_selenium_stubs():
            from scrape_linkedin import Company, Profile, utils as u

            profile_html = (REPO_ROOT / "test" / "html_files" / "profile.html").read_text(encoding="utf-8")
            profile = Profile(profile_html)
            self.assertEqual(len(profile.skills), 39)
            self.assertEqual(profile.skills[0]["name"], "Leadership")
            self.assertEqual(len(profile.experiences["jobs"]), 8)
            self.assertTrue(profile.experiences["jobs"][0]["li_company_url"])

            other_html = (REPO_ROOT / "test" / "html_files" / "otherProfile.html").read_text(encoding="utf-8")
            other_profile = Profile(other_html)
            self.assertEqual(len(other_profile.skills), 12)

            fb_html = (REPO_ROOT / "test" / "html_files" / "facebook_overview.html").read_text(encoding="utf-8")
            fb_company = Company(fb_html, "", "", "")
            self.assertTrue(fb_company.overview["image"].startswith("https://"))
            self.assertIsNone(fb_company.jobs)
            self.assertIsNone(fb_company.life)

            modern_profile = Profile(MODERN_PROFILE_HTML)
            self.assertEqual(modern_profile.personal_info["name"], "Ada Lovelace")
            self.assertEqual(modern_profile.personal_info["location"], "London, United Kingdom")
            self.assertEqual(modern_profile.personal_info["followers"], "1,250")
            self.assertEqual(modern_profile.accomplishments["certifications"], ["Analytical Mathematics"])
            self.assertEqual(modern_profile.accomplishments["test_scores"], ["Logic Exam 100"])
            self.assertEqual(modern_profile.recommendations["received"][0]["connection"]["li_id"], "charles-babbage")

            modern_company = Company(MODERN_COMPANY_OVERVIEW_HTML, "", "", MODERN_COMPANY_INSIGHTS_HTML)
            self.assertEqual(modern_company.overview["name"], "Engine Systems")
            self.assertEqual(modern_company.overview["num_employees"], 640)
            self.assertEqual(modern_company.overview["metadata"]["industry"], "Computer Software")
            self.assertEqual(modern_company.insights["6m change"], "+4%")

            # Validate core BeautifulSoup helpers without the legacy .1 selector rejected by soupsieve
            self.assertEqual(u.split_lists([1, 2, 3, 4], 2), [[1, 2], [3, 4]])
            test_html = (REPO_ROOT / "test" / "test.html").read_text(encoding="utf-8")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(test_html, "html.parser")
            self.assertEqual(len(u.all_or_default(soup, ".test1")), 2)
            self.assertEqual(u.text_or_default(soup, ".inner"), "Test")
            self.assertEqual(u.get_info(soup, {"a": ".inner", "b": ".missing"}), {"a": "Test", "b": None})

    def test_cli_scrapeli_help_and_offline_input_file(self) -> None:
        from click.testing import CliRunner

        with _offline_selenium_stubs():
            from scrape_linkedin.cli import scrape

            runner = CliRunner()
            help_res = runner.invoke(scrape, ["--help"])
            self.assertEqual(help_res.exit_code, 0)
            for flag in ("--url", "--user", "--company", "--attribute", "--input_file", "--headless", "--output_file", "--driver"):
                self.assertIn(flag, help_res.output)

            short_h = runner.invoke(scrape, ["-h"])
            self.assertNotEqual(short_h.exit_code, 0)

            profile_path = str((REPO_ROOT / "test" / "html_files" / "profile.html").resolve())
            with tempfile.TemporaryDirectory() as tmpdir:
                old_cwd = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    bad_none = runner.invoke(scrape, [])
                    self.assertNotEqual(bad_none.exit_code, 0)

                    bad_both = runner.invoke(scrape, ["--user", "ada", "-i", profile_path])
                    self.assertNotEqual(bad_both.exit_code, 0)

                    skills_json = os.path.join(tmpdir, "skills.json")
                    ok_res = runner.invoke(scrape, ["-i", profile_path, "-a", "skills", "-o", skills_json])
                    self.assertEqual(ok_res.exit_code, 0, ok_res.output)
                    parsed_skills = json.loads(pathlib.Path(skills_json).read_text(encoding="utf-8"))
                    self.assertEqual(len(parsed_skills), 39)
                    self.assertEqual(parsed_skills[0]["name"], "Leadership")

                    modern_html = pathlib.Path(tmpdir) / "modern.html"
                    modern_html.write_text(MODERN_PROFILE_HTML, encoding="utf-8")
                    info_json = os.path.join(tmpdir, "info.json")
                    ok_modern = runner.invoke(scrape, ["-i", str(modern_html), "-a", "personal_info", "-o", info_json])
                    self.assertEqual(ok_modern.exit_code, 0, ok_modern.output)
                    info = json.loads(pathlib.Path(info_json).read_text(encoding="utf-8"))
                    self.assertEqual(info["name"], "Ada Lovelace")
                finally:
                    os.chdir(old_cwd)
                    # Close file handlers opened by cli._init_logging() so Windows temp cleanup succeeds
                    root_logger = logging.getLogger()
                    for handler in root_logger.handlers[:]:
                        handler.close()
                        root_logger.removeHandler(handler)


class TestDocsSyntaxDiataxisSTEAndMermaid(unittest.TestCase):
    """Validate documented Python/bash blocks, Diataxis layout, STE rules, links, and Mermaid."""

    def test_documented_python_and_bash_fences(self) -> None:
        bash_bin = shutil.which("bash") if os.name == "posix" else None
        py_checked = 0
        bash_checked = 0

        for md in (REPO_ROOT / "README.md", *sorted(DOCS_DIR.rglob("*.md"))):
            _, blocks, _ = _split_fenced_blocks(md.read_text(encoding="utf-8"))
            for start_line, lang, code in blocks:
                if lang == "python":
                    ast.parse(code, filename=f"{md.name}:{start_line}")
                    py_checked += 1
                elif lang in ("bash", "sh") and bash_bin:
                    chk = subprocess.run(
                        [bash_bin, "-n"],
                        input=code,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(chk.returncode, 0, f"{md.name}:{start_line}: bash -n failed: {chk.stderr}")
                    bash_checked += 1

        self.assertGreaterEqual(py_checked, 6)
        if bash_bin:
            self.assertGreaterEqual(bash_checked, 7)

    def test_diataxis_ste_links_mermaid_and_accuracy(self) -> None:
        self.assertTrue((DOCS_DIR / "index.md").is_file())
        for q in REQUIRED_QUADRANTS:
            qdir = DOCS_DIR / q
            self.assertTrue(qdir.is_dir())
            self.assertTrue((qdir / "index.md").is_file())
            self.assertTrue([p for p in qdir.glob("*.md") if p.name != "index.md"])

        howtos = [p for p in (DOCS_DIR / "02-how-to-guides").glob("*.md") if p.name != "index.md"]
        for md in howtos:
            non_code, _, _ = _split_fenced_blocks(md.read_text(encoding="utf-8"))
            body = "\n".join(ln for _, ln in non_code)
            self.assertRegex(body, r"(?im)^##\s+Validation")
            self.assertRegex(body, r"(?im)^##\s+Rollback")
            for lineno, line in non_code:
                s = line.strip()
                if not s or s.startswith(("#", "|", "NOTE:", "CAUTION:", ">")):
                    continue
                self.assertNotIn(";", s, f"{md.name}:{lineno}: semicolon violates STE")
                self.assertNotRegex(s, r"\b(should|would|may|might|shall)\b")
                clean = re.sub(r"`[^`]+`|\[([^\]]+)\]\([^)]+\)", r"\1", re.sub(r"^\d+\.\s+|^-\s+", "", s))
                for sent in [p.strip() for p in re.split(r"(?<=[.!?])\s+", clean) if p.strip()]:
                    words = [w for w in sent.split() if re.search(r"[A-Za-z0-9]", w)]
                    self.assertLessEqual(len(words), 20, f"{md.name}:{lineno} > 20 words: {sent}")

        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("jmrenouard/scrape-linkedin-selenium", readme)
        self.assertNotIn("git+git://", readme)
        self.assertIn("--company", readme)
        self.assertIn("--headless", readme)
        self.assertIn("Company(overview, jobs, life, insights)", readme)
        self.assertIn("__pycache__/", (REPO_ROOT / ".gitignore").read_text(encoding="utf-8"))

        for prereq_doc in (
            DOCS_DIR / "01-tutorials" / "01-offline-html-profile-and-cli-tutorial.md",
            DOCS_DIR / "02-how-to-guides" / "parse-offline-html-and-verify-docs.md",
        ):
            doc_text = prereq_doc.read_text(encoding="utf-8")
            self.assertIn("selenium", doc_text)
            self.assertIn("joblib", doc_text)
            self.assertIn("requirements.txt", doc_text)

        mermaid_count = 0
        mmdc_bin = shutil.which("mmdc")
        errors: list[str] = []
        for md in sorted(REPO_ROOT.rglob("*.md")):
            rel = md.relative_to(REPO_ROOT).as_posix()
            txt = md.read_text(encoding="utf-8")
            non_code, blocks, unclosed = _split_fenced_blocks(txt)
            if unclosed:
                errors.append(f"{rel}: unclosed fenced block")
            if ASCII_BOX_RE.search(txt):
                errors.append(f"{rel}: ASCII/Unicode box diagram found")

            prose = "\n".join(_strip_inline_code(ln) for _, ln in non_code)
            self.assertNotRegex(prose, r"\b(Voici|Étape|Procédure|Vérification|dépôt)\b")

            for start_line, lang, code in blocks:
                first_non_empty = next((ln.strip() for ln in code.splitlines() if ln.strip()), "")
                if lang == "mermaid":
                    mermaid_count += 1
                    raw_open = txt.splitlines()[start_line - 1]
                    if raw_open != raw_open.lstrip():
                        errors.append(f"{rel}:{start_line}: indented mermaid fence")
                    if mmdc_bin:
                        with tempfile.TemporaryDirectory() as tmp:
                            in_mmd = os.path.join(tmp, "diag.mmd")
                            out_svg = os.path.join(tmp, "diag.svg")
                            pathlib.Path(in_mmd).write_text(code, encoding="utf-8")
                            r = subprocess.run([mmdc_bin, "-i", in_mmd, "-o", out_svg], capture_output=True, text=True, check=False)
                            if r.returncode != 0:
                                errors.append(f"{rel}:{start_line}: mmdc failed: {r.stderr.strip()}")
                elif lang == "" and any(first_non_empty.startswith(t) for t in MERMAID_TYPES):
                    errors.append(f"{rel}:{start_line}: untagged mermaid block")

            for lineno, line in non_code:
                for m in LINK_RE.finditer(_strip_inline_code(line)):
                    raw_target = m.group(1).strip().strip("<>")
                    if raw_target.startswith(("http://", "https://", "mailto:")):
                        continue
                    path_part, _, frag = raw_target.partition("#")
                    resolved = md if not path_part else (md.parent / unquote(path_part)).resolve()
                    if not resolved.exists():
                        errors.append(f"{rel}:{lineno}: broken link '{raw_target}'")
                        continue
                    if frag and resolved.is_file() and resolved.suffix.lower() == ".md":
                        target_non_code, _, _ = _split_fenced_blocks(resolved.read_text(encoding="utf-8"))
                        slugs = {
                            _github_anchor_slug(hm.group(2))
                            for _, tline in target_non_code
                            if (hm := HEADING_RE.match(tline))
                        }
                        if frag not in slugs:
                            errors.append(f"{rel}:{lineno}: missing anchor '#{frag}' in {resolved.name}")

        self.assertGreaterEqual(mermaid_count, 3)
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
