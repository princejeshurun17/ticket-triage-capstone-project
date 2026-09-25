"""Category ontology and keyword-based suggestion logic.

No external AI service required, which matches the rubric's "AI classification
or free keyword search logic" requirement without spending Azure AI Language
quota. Each category has a small set of weighted keywords; the ticket title +
description is scored against every category and the highest scorer wins.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

CATEGORIES: List[str] = [
    "IT Support",
    "Facilities",
    "Course Registration",
    "Student Finance",
    "Library Services",
    "General Enquiry",
]

# word/phrase -> weight. Longer, more specific phrases are weighted higher so
# they win over a generic single word that could belong to another category.
_KEYWORDS: Dict[str, List[Tuple[str, int]]] = {
    "IT Support": [
        ("wifi", 3), ("wi-fi", 3), ("password", 3), ("login", 2), ("laptop", 2),
        ("computer", 2), ("network", 2), ("vpn", 3), ("email account", 3),
        ("printer", 2), ("software", 2), ("account locked", 3),
    ],
    "Facilities": [
        ("classroom", 2), ("air conditioning", 3), ("aircon", 3), ("elevator", 3),
        ("lift", 2), ("broken", 1), ("lighting", 2), ("leak", 2), ("cleaning", 2),
        ("parking", 2), ("building", 1),
    ],
    "Course Registration": [
        ("register", 2), ("registration", 3), ("enrol", 3), ("enroll", 3),
        ("course add", 3), ("drop course", 3), ("timetable", 2), ("class schedule", 3),
        ("prerequisite", 2),
    ],
    "Student Finance": [
        ("tuition", 3), ("student loan", 4), ("payment", 2), ("invoice", 2),
        ("refund", 2), ("scholarship", 2), ("financial aid", 3), ("fee", 1),
    ],
    "Library Services": [
        ("library", 3), ("book loan", 4), ("librarian", 3), ("overdue", 2),
        ("library fine", 4), ("journal access", 3), ("ebook", 2),
    ],
}


def suggest_category(title: str, description: str) -> Tuple[str, float]:
    """Return (category, confidence 0..1). Falls back to General Enquiry."""
    text = f" {title} {description} ".lower()
    text = re.sub(r"\s+", " ", text)

    scores: Dict[str, int] = {name: 0 for name in _KEYWORDS}
    for category, terms in _KEYWORDS.items():
        for term, weight in terms:
            if f" {term} " in text or term in text:
                scores[category] += weight

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score == 0:
        return "General Enquiry", 0.3

    total = sum(scores.values()) or 1
    confidence = min(0.95, 0.4 + 0.6 * (best_score / total))
    return best_category, round(confidence, 2)
