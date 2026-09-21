import math
import statistics

MAX_FEATURES = 40
DEVIATION_FLOOR_MS = 30.0
MATCH_THRESHOLD = 2.2

CHANNELS = ("holds", "intervals")


def enroll(samples):
    profile = {}
    for channel in CHANNELS:
        vectors = [_clean(sample.get(channel, [])) for sample in samples]
        vectors = [vector for vector in vectors if vector]
        width = min((len(vector) for vector in vectors), default=0)
        means = []
        deviations = []
        for position in range(width):
            column = [vector[position] for vector in vectors]
            means.append(round(statistics.fmean(column), 3))
            spread = statistics.pstdev(column) if len(column) > 1 else DEVIATION_FLOOR_MS
            deviations.append(round(max(spread, DEVIATION_FLOOR_MS), 3))
        profile[channel] = {"means": means, "deviations": deviations}
    return profile


def compare(profile, holds, intervals):
    score = distance(profile, holds, intervals)
    if math.isinf(score):
        return False, None
    return score <= MATCH_THRESHOLD, round(score, 2)


def distance(profile, holds, intervals):
    squares = []
    for channel, values in (("holds", holds), ("intervals", intervals)):
        reference = profile.get(channel) or {}
        means = reference.get("means") or []
        deviations = reference.get("deviations") or reference.get("stds") or []
        observed = _clean(values)
        if not means or not observed:
            continue
        for position in range(min(len(means), len(observed))):
            spread = max(deviations[position] if position < len(deviations) else DEVIATION_FLOOR_MS, DEVIATION_FLOOR_MS)
            squares.append(((observed[position] - means[position]) / spread) ** 2)
    if not squares:
        return math.inf
    return math.sqrt(sum(squares) / len(squares))


def is_enrolled(profile):
    return bool((profile or {}).get("holds", {}).get("means"))


def _clean(values):
    cleaned = []
    for value in values or []:
        try:
            cleaned.append(max(0.0, float(value)))
        except (TypeError, ValueError):
            continue
    return cleaned[:MAX_FEATURES]


def parse(raw):
    if not raw:
        return []
    return _clean(part for part in str(raw).split(",") if part.strip())
