"""Offline checks of selected real records, never new remote requests."""
from scripts import check_submission


def test_selected_current_prompt_evidence_covers_required_behaviors():
    assert check_submission.verify()['verified']


def test_evidence_for_another_prompt_is_not_accepted(monkeypatch):
    monkeypatch.setattr(check_submission, 'SYSTEM_PROMPT', 'different future prompt')
    report = check_submission.verify()
    assert not report['verified']
    assert all(not row['checks']['current_prompt'] for row in report['cases'])
