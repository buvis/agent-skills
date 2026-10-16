import pytest

from survey_test_helpers import _init_git_repo


@pytest.fixture()
def git_repo(tmp_path):
    """A fresh git repo with one committed Python file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    return repo
