from typing import TYPE_CHECKING

import pydantic
import pytest

from pipeline.seed_test.manifest import load_seed_fetches

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (
            'dataset = "company_facts"\ncik = 320193\nhttp_status = 404\nfile = "facts.json"\n',
            "A 404 fetch has no body file",
        ),
        ('dataset = "submissions"\ncik = 320193\n', "A 200 fetch needs a body file"),
    ],
)
def test_a_body_file_is_listed_for_every_fetch_but_a_404(
    tmp_path: Path, entry: str, message: str
) -> None:
    path = tmp_path / "fetches.toml"
    path.write_text(f"[[fetches]]\n{entry}")

    with pytest.raises(pydantic.ValidationError, match=message):
        load_seed_fetches(path)
