"""SM-2 spaced repetition algorithm for flashcard reviews."""
from datetime import datetime, timedelta

from .. import models


def review(card: models.Flashcard, quality: int) -> models.Flashcard:
    """Apply an SM-2 review. quality: 0-5 (0=blackout, 5=perfect recall)."""
    quality = max(0, min(5, quality))
    if quality < 3:
        # Failed — restart
        card.repetitions = 0
        card.interval_days = 1
    else:
        card.repetitions += 1
        if card.repetitions == 1:
            card.interval_days = 1
        elif card.repetitions == 2:
            card.interval_days = 6
        else:
            card.interval_days = max(1, round(card.interval_days * card.ease))

    # Update ease factor (bounded below at 1.3)
    card.ease = max(1.3, card.ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    card.due_at = datetime.utcnow() + timedelta(days=card.interval_days)
    return card
