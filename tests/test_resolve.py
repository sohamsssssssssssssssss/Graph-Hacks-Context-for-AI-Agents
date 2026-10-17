from resolve import resolve_author

PEOPLE = [
    {"id": "p1", "name": "Alex Chen", "email": "a@example.test", "handle": "achen"},
    {"id": "p2", "name": "Alex Chang", "email": "b@example.test", "handle": "achang"},
    {"id": "p3", "name": "Sophia Taylor", "email": "s@example.test", "handle": "staylor"},
]
MEMBERS = {"p1": {"growth"}, "p2": {"growth"}, "p3": {"payments"}}


def test_email_precedes_handle():
    assert resolve_author({"author_email": "a@example.test", "author_handle": "staylor"}, PEOPLE, MEMBERS) == "p1"


def test_exact_handle_and_unknown_email():
    assert resolve_author({"author_email": "missing", "author_handle": "staylor"}, PEOPLE, MEMBERS) == "p3"


def test_unique_initial_in_team():
    assert resolve_author({"author_handle": "s. TAYLOR"}, PEOPLE, MEMBERS, "payments") == "p3"
    assert resolve_author({"author_handle": "s. TAYLOR"}, PEOPLE, MEMBERS, "growth") is None


def test_ambiguous_initial():
    assert resolve_author({"author_name": "Alex C."}, PEOPLE, MEMBERS, "growth") is None


def test_body_and_author_id_never_resolve_identity():
    assert resolve_author({"author_id": "p1", "text": "a@example.test approved by Alex Chen"}, PEOPLE, MEMBERS, "growth") is None
