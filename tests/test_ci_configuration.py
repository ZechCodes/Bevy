"""Keep CI on declared Python versions with a portable, complete test toolchain."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CiConfigurationTests(unittest.TestCase):
    def test_matrix_matches_the_project_python_floor(self):
        workflow = (ROOT / ".github/workflows/tests.yaml").read_text(encoding="utf-8")
        self.assertIn("python-version: ['3.12', '3.13']", workflow)

    def test_poetry_uses_the_selected_interpreter_on_every_platform(self):
        workflow = (ROOT / ".github/workflows/tests.yaml").read_text(encoding="utf-8")
        self.assertNotIn("snok/install-poetry", workflow)
        self.assertIn('version: "0.13.4"', workflow)
        self.assertIn(
            'uv pip install --system "poetry==1.8.5" "certifi>=2026.10.19"', workflow
        )
        self.assertIn("python -I -m poetry env use python", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s*(?:run: )?poetry (?:install|run)")

    def test_poetry_commands_ignore_repository_module_shadows(self):
        workflow = (ROOT / ".github/workflows/tests.yaml").read_text(encoding="utf-8")
        self.assertNotIn("python -m poetry", workflow)
        self.assertIn("python -I -m poetry install", workflow)

    def test_coverage_upload_uses_authentication_and_keeps_failure_gate(self):
        workflow = (ROOT / ".github/workflows/tests.yaml").read_text(encoding="utf-8")
        self.assertIn("use_oidc: true", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("fail_ci_if_error: true", workflow)

    def test_coverage_plugin_is_declared_and_locked(self):
        manifest = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('pytest-cov = "^5.0"', manifest)
        self.assertRegex(
            (ROOT / "poetry.lock").read_text(encoding="utf-8"),
            r'(?m)^name = "pytest-cov"$',
        )


if __name__ == "__main__":
    unittest.main()
