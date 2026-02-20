"""Signal decay weighting engine.

Calculates temporal decay weights for all signal types based on
configurable peak, half-life, and max relevance parameters.
"""

import logging
from datetime import date

from prism.config import SIGNAL_DECAY_CONFIG

logger = logging.getLogger(__name__)


def calculate_decay_weight(
    signal_type: str,
    signal_date: date,
    current_date: date,
) -> float:
    """Calculate 0.0-1.0 weight based on signal freshness.

    Uses a ramp-up-to-peak then exponential decay model:
    - Before peak: linear ramp from 0 to 1.0
    - At peak: 1.0
    - After peak: exponential decay with configured half-life
    - After max relevance: 0.0

    Args:
        signal_type: Type of signal (must exist in SIGNAL_DECAY_CONFIG).
        signal_date: When the signal was detected.
        current_date: Reference date for freshness calculation.

    Returns:
        Decay weight between 0.0 and 1.0.
    """
    if signal_type not in SIGNAL_DECAY_CONFIG:
        logger.warning("Unknown signal type '%s', returning 0.0", signal_type)
        return 0.0

    peak, half_life, max_days = SIGNAL_DECAY_CONFIG[signal_type]
    age_days = (current_date - signal_date).days

    if age_days > max_days:
        return 0.0
    if age_days < 0:
        return 0.0
    if age_days <= peak:
        return min(1.0, age_days / peak) if peak > 0 else 1.0

    # Exponential decay after peak
    decay_age = age_days - peak
    return max(0.0, 0.5 ** (decay_age / half_life))


def calculate_signal_freshness_avg(
    signal_weights: list[float],
) -> float:
    """Calculate average signal freshness for timing score.

    Args:
        signal_weights: List of decay weights for all signals.

    Returns:
        Score between 0.0 and 1.0 based on average freshness.
    """
    if not signal_weights:
        return 0.0

    avg = sum(signal_weights) / len(signal_weights)

    if avg > 0.80:
        return 1.0
    elif avg > 0.60:
        return 0.80
    elif avg > 0.40:
        return 0.55
    elif avg > 0.20:
        return 0.30
    else:
        return 0.10
