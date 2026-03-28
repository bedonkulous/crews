"""Unit tests for DeploymentScaffold."""

import yaml
import pytest
from pathlib import Path

from core.deployment_scaffold import DeploymentScaffold


EXPECTED_FILES = [
    ".github/workflows/deploy.yml",
    "infra/cloudformation/ecs.yml",
    "infra/cloudformation/alb-waf.yml",
    "infra/cloudformation/s3.yml",
    "infra/cloudformation/dynamodb.yml",
    "infra/cloudformation/rds.yml",
]


@pytest.fixture
def scaffold_dir(tmp_path):
    scaffold = DeploymentScaffold()
    scaffold.generate(tmp_path, "my-crew")
    return tmp_path


def test_all_six_files_are_created(scaffold_dir):
    for relative in EXPECTED_FILES:
        assert (scaffold_dir / relative).exists(), f"Missing: {relative}"


def test_all_files_are_non_empty(scaffold_dir):
    for relative in EXPECTED_FILES:
        content = (scaffold_dir / relative).read_text()
        assert content.strip(), f"File is empty: {relative}"


def test_deploy_yml_references_aws_access_key_id(scaffold_dir):
    content = (scaffold_dir / ".github/workflows/deploy.yml").read_text()
    assert "AWS_ACCESS_KEY_ID" in content


def test_deploy_yml_references_aws_secret_access_key(scaffold_dir):
    content = (scaffold_dir / ".github/workflows/deploy.yml").read_text()
    assert "AWS_SECRET_ACCESS_KEY" in content


def test_deploy_yml_triggers_on_push_to_main(scaffold_dir):
    content = (scaffold_dir / ".github/workflows/deploy.yml").read_text()
    assert "main" in content


@pytest.mark.parametrize("cf_file", [
    "infra/cloudformation/ecs.yml",
    "infra/cloudformation/alb-waf.yml",
    "infra/cloudformation/s3.yml",
    "infra/cloudformation/dynamodb.yml",
    "infra/cloudformation/rds.yml",
])
def test_cloudformation_files_are_valid_yaml(scaffold_dir, cf_file):
    content = (scaffold_dir / cf_file).read_text()
    parsed = yaml.safe_load(content)
    assert parsed is not None


@pytest.mark.parametrize("cf_file", [
    "infra/cloudformation/ecs.yml",
    "infra/cloudformation/alb-waf.yml",
    "infra/cloudformation/s3.yml",
    "infra/cloudformation/dynamodb.yml",
    "infra/cloudformation/rds.yml",
])
def test_cloudformation_files_have_required_sections(scaffold_dir, cf_file):
    content = (scaffold_dir / cf_file).read_text()
    parsed = yaml.safe_load(content)
    assert "AWSTemplateFormatVersion" in parsed
    assert "Description" in parsed
    assert "Resources" in parsed


def test_crew_name_is_interpolated(tmp_path):
    scaffold = DeploymentScaffold()
    scaffold.generate(tmp_path, "alpha-team")
    for relative in EXPECTED_FILES:
        content = (tmp_path / relative).read_text()
        assert "alpha-team" in content


def test_generate_creates_parent_directories(tmp_path):
    """Directories like .github/workflows/ should be created automatically."""
    scaffold = DeploymentScaffold()
    scaffold.generate(tmp_path, "test-crew")
    assert (tmp_path / ".github" / "workflows").is_dir()
    assert (tmp_path / "infra" / "cloudformation").is_dir()
