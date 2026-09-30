"""Tests for output folder handling and report saving."""

from pathlib import Path

import pytest

from yt_transcribe.output import (
    create_output_directory,
    find_output_directory,
    sanitize_title_for_folder,
    save_report,
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Bodybuilding for the Mind", "Bodybuilding_for_the_Mind"),
        ('What? A <weird> "title": yes/no', "What_A_weird_title_yesno"),
        ("...", "video"),
        ("", "video"),
        ("a" * 80, "a" * 50),
    ],
)
def test_sanitize_title_for_folder(title: str, expected: str) -> None:
    assert sanitize_title_for_folder(title) == expected


def test_create_output_directory_includes_date_title_and_id(tmp_path: Path) -> None:
    path = create_output_directory(tmp_path, "My Video", "abcdefghijk")

    assert path.is_dir()
    assert path.name == "My_Video_abcdefghijk"
    assert path.parent.parent == tmp_path
    assert len(path.parent.name) == len("YYYY-MM-DD")


def test_same_title_different_ids_get_separate_directories(tmp_path: Path) -> None:
    first = create_output_directory(tmp_path, "Same Title", "aaaaaaaaaaa")
    second = create_output_directory(tmp_path, "Same Title", "bbbbbbbbbbb")
    assert first != second


def test_existing_directory_is_reused_from_an_earlier_date(tmp_path: Path) -> None:
    old = tmp_path / "2020-01-01" / "Old_Title_abcdefghijk"
    old.mkdir(parents=True)

    assert create_output_directory(tmp_path, "Renamed Title", "abcdefghijk") == old


def test_find_output_directory_picks_most_recent_date(tmp_path: Path) -> None:
    for date in ("2020-01-01", "2021-06-30", "2019-12-31"):
        (tmp_path / date / "Title_abcdefghijk").mkdir(parents=True)

    assert find_output_directory(tmp_path, "abcdefghijk") == tmp_path / "2021-06-30" / "Title_abcdefghijk"


def test_find_output_directory_does_not_match_other_ids(tmp_path: Path) -> None:
    (tmp_path / "2020-01-01" / "Title_Xbcdefghijk").mkdir(parents=True)
    assert find_output_directory(tmp_path, "abcdefghijk") is None
    assert find_output_directory(tmp_path / "missing", "abcdefghijk") is None


def test_save_report_writes_markdown_only_by_default(tmp_path: Path) -> None:
    md_path, pdf_path = save_report("# Report\n\nBody", tmp_path)

    assert md_path.read_text() == "# Report\n\nBody"
    assert pdf_path is None
    assert not (tmp_path / "report.pdf").exists()


def test_pdf_does_not_embed_local_files(tmp_path: Path) -> None:
    pytest.importorskip("weasyprint")
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET-MARKER-123")
    report = (
        "# Report\n\n"
        f'<link rel="attachment" href="file://{secret}">\n'
        f'<a rel="attachment" href="file://{secret}">x</a>\n'
        f'<img src="file://{secret}">\n'
    )

    _, pdf_path = save_report(report, tmp_path, pdf=True)

    data = pdf_path.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"SECRET-MARKER-123" not in data
    assert b"EmbeddedFile" not in data
