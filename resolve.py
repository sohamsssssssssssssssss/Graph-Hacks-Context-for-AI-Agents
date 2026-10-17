"""Deterministic R1 identity resolution from document metadata only."""


def resolve_author(doc, people, memberships, claim_team=None):
    people = [person for person in people if person.get("label", "Person") == "Person"]
    for field, metadata in (("email", "author_email"), ("handle", "author_handle")):
        value = doc.get(metadata)
        matches = [person["id"] for person in people if value and person.get(field) == value]
        if matches:
            return matches[0] if len(matches) == 1 else None
    tokens = (doc.get("author_name") or doc.get("author_handle") or "").casefold().replace(".", "").split()
    if len(tokens) != 2 or claim_team is None:
        return None
    candidates = []
    for person in people:
        teams = memberships.get(person["id"], set())
        teams = {teams} if isinstance(teams, str) else set(teams)
        other = person["name"].casefold().replace(".", "").split()
        if claim_team not in teams or len(other) != 2:
            continue
        if all(a == b or (len(a) == 1 and b.startswith(a)) or
               (len(b) == 1 and a.startswith(b)) for a, b in zip(tokens, other)):
            candidates.append(person["id"])
    return candidates[0] if len(candidates) == 1 else None
