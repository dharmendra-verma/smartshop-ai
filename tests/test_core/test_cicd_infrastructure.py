"""Verify CI/CD infrastructure files exist and are properly configured."""

import os

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


class TestDockerfiles:
    """Validate Dockerfile configurations."""

    def test_dockerfile_exists(self):
        assert os.path.isfile(os.path.join(ROOT_DIR, "Dockerfile"))

    def test_dockerfile_streamlit_exists(self):
        assert os.path.isfile(os.path.join(ROOT_DIR, "Dockerfile.streamlit"))

    def test_dockerignore_exists(self):
        assert os.path.isfile(os.path.join(ROOT_DIR, ".dockerignore"))

    def test_dockerfile_has_git_sha_label(self):
        with open(os.path.join(ROOT_DIR, "Dockerfile"), "r") as f:
            content = f.read()
        assert "GIT_SHA" in content
        assert "LABEL git.sha" in content

    def test_dockerfile_copies_alembic(self):
        with open(os.path.join(ROOT_DIR, "Dockerfile"), "r") as f:
            content = f.read()
        assert "alembic" in content.lower()

    def test_dockerfile_streamlit_uses_slim_requirements(self):
        with open(os.path.join(ROOT_DIR, "Dockerfile.streamlit"), "r") as f:
            content = f.read()
        assert "requirements-ui.txt" in content

    def test_requirements_ui_exists(self):
        filepath = os.path.join(ROOT_DIR, "requirements-ui.txt")
        assert os.path.isfile(filepath)
        with open(filepath, "r") as f:
            content = f.read()
        assert "streamlit" in content
        assert "httpx" in content

    def test_dockerignore_excludes_tests(self):
        with open(os.path.join(ROOT_DIR, ".dockerignore"), "r") as f:
            content = f.read()
        assert "tests/" in content
        assert ".git/" in content
        assert "venv/" in content


class TestGitHubWorkflows:
    """Validate GitHub Actions workflow files."""

    WORKFLOWS_DIR = os.path.join(ROOT_DIR, ".github", "workflows")

    def test_ci_workflow_exists(self):
        assert os.path.isfile(os.path.join(self.WORKFLOWS_DIR, "ci.yml"))

    def test_cd_staging_workflow_exists(self):
        assert os.path.isfile(os.path.join(self.WORKFLOWS_DIR, "cd-staging.yml"))

    def test_cd_production_workflow_exists(self):
        assert os.path.isfile(os.path.join(self.WORKFLOWS_DIR, "cd-production.yml"))

    def test_infra_workflow_exists(self):
        assert os.path.isfile(os.path.join(self.WORKFLOWS_DIR, "infra.yml"))

    def test_ci_has_lint_test_build(self):
        with open(os.path.join(self.WORKFLOWS_DIR, "ci.yml"), "r") as f:
            content = f.read()
        assert "lint:" in content or "Lint" in content
        assert "test:" in content or "Test" in content
        assert "build:" in content or "Build" in content

    def test_ci_uses_postgres_and_redis(self):
        with open(os.path.join(self.WORKFLOWS_DIR, "ci.yml"), "r") as f:
            content = f.read()
        assert "postgres" in content
        assert "redis" in content

    def test_cd_staging_triggers_on_push_main(self):
        with open(os.path.join(self.WORKFLOWS_DIR, "cd-staging.yml"), "r") as f:
            content = f.read()
        assert "push:" in content
        assert "main" in content

    def test_cd_production_has_manual_trigger(self):
        with open(os.path.join(self.WORKFLOWS_DIR, "cd-production.yml"), "r") as f:
            content = f.read()
        assert "workflow_dispatch:" in content

    def test_cd_production_has_rollback(self):
        with open(os.path.join(self.WORKFLOWS_DIR, "cd-production.yml"), "r") as f:
            content = f.read()
        assert "rollback" in content.lower() or "Rollback" in content


class TestInfrastructure:
    """Validate Bicep IaC files."""

    INFRA_DIR = os.path.join(ROOT_DIR, "infra")

    def test_main_bicep_exists(self):
        assert os.path.isfile(os.path.join(self.INFRA_DIR, "main.bicep"))

    def test_resources_module_exists(self):
        assert os.path.isfile(
            os.path.join(self.INFRA_DIR, "modules", "resources.bicep")
        )

    def test_staging_params_exists(self):
        assert os.path.isfile(os.path.join(self.INFRA_DIR, "parameters.staging.json"))

    def test_prod_params_exists(self):
        assert os.path.isfile(os.path.join(self.INFRA_DIR, "parameters.prod.json"))

    def test_bicep_has_container_apps(self):
        with open(os.path.join(self.INFRA_DIR, "modules", "resources.bicep"), "r") as f:
            content = f.read()
        assert "Microsoft.App/containerApps" in content

    def test_bicep_has_postgres(self):
        with open(os.path.join(self.INFRA_DIR, "modules", "resources.bicep"), "r") as f:
            content = f.read()
        assert "Microsoft.DBforPostgreSQL" in content

    def test_bicep_has_redis(self):
        with open(os.path.join(self.INFRA_DIR, "modules", "resources.bicep"), "r") as f:
            content = f.read()
        assert "Microsoft.Cache/redis" in content

    def test_bicep_has_key_vault(self):
        with open(os.path.join(self.INFRA_DIR, "modules", "resources.bicep"), "r") as f:
            content = f.read()
        assert "Microsoft.KeyVault" in content

    def test_bicep_has_health_probes(self):
        with open(os.path.join(self.INFRA_DIR, "modules", "resources.bicep"), "r") as f:
            content = f.read()
        assert "/health" in content
        assert "Liveness" in content
        assert "Readiness" in content


class TestSmokeTestScript:
    """Validate smoke test script."""

    def test_smoke_test_script_exists(self):
        assert os.path.isfile(os.path.join(ROOT_DIR, "scripts", "smoke_test.sh"))

    def test_smoke_test_checks_health_endpoints(self):
        with open(os.path.join(ROOT_DIR, "scripts", "smoke_test.sh"), "r") as f:
            content = f.read()
        assert "/health" in content
        assert "/health/metrics" in content
        assert "/health/alerts" in content

    def test_smoke_test_has_retry_logic(self):
        with open(os.path.join(ROOT_DIR, "scripts", "smoke_test.sh"), "r") as f:
            content = f.read()
        assert "MAX_RETRIES" in content
        assert "RETRY_DELAY" in content


class TestDocumentation:
    """Validate new CI/CD documentation."""

    DOCS_DIR = os.path.join(ROOT_DIR, "docs")

    def test_cicd_doc_exists(self):
        filepath = os.path.join(self.DOCS_DIR, "CICD.md")
        assert os.path.isfile(filepath)
        with open(filepath, "r") as f:
            content = f.read()
        assert "CI Pipeline" in content or "CI/CD" in content

    def test_azure_setup_doc_exists(self):
        filepath = os.path.join(self.DOCS_DIR, "AZURE_SETUP.md")
        assert os.path.isfile(filepath)
        with open(filepath, "r") as f:
            content = f.read()
        assert "Container Apps" in content or "Azure" in content
