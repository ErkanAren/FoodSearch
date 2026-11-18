"""Stage 05: the 3-model rank vote and the agreement level (standard library only).

Shared by text_variants.py, serve_models.py and the local browser pages (tools/browser/foods_browser.py),
so every place combines the models the same way.
"""
VOTE = [("qwen3-0.6b", "lr"), ("qwen3-0.6b", "knn"), ("arctic-l-v2", "knn")]  # best vote in REPORT.md Result 3
LEVELS = {"all": "all 3 agree", "two": "2 of 3 agree", "none": "all 3 differ"}


def rank_vote(tops):
    """tops: the top-3 code lists of the VOTE members, in VOTE order -> [(code, points)], best first.

    A member's 1st, 2nd and 3rd choice get 3, 2 and 1 points. The first member (Qwen3 classifier, the best single
    model) adds 0.1 per choice, which breaks ties in its favour."""
    points = {}
    for i, top in enumerate(tops):
        for rank, code in enumerate(top[:3]):
            points[code] = points.get(code, 0) + (3 - rank) + (0.1 if i == 0 else 0)
    return sorted(points.items(), key=lambda x: -x[1])  # stable: ties keep first-seen order


def agreement(tops):
    """How many VOTE members have the same first choice: 'all', 'two' or 'none'."""
    firsts = [t[0] for t in tops if t]
    most = max((firsts.count(c) for c in firsts), default=0)
    return "all" if most >= 3 else "two" if most == 2 else "none"
