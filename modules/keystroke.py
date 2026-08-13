import math
import statistics

MAX_FEATURES = 40
STD_FLOOR_MS = 30.0
MATCH_THRESHOLD = 2.2


def _clip(values):
    values = [max(0.0, float(v)) for v in values]
    return values[:MAX_FEATURES]


def enroll(samples):
    profile = {}
    for name in ("holds", "intervals"):
        per_position = []
        for sample in samples:
            per_position.append(_clip(sample.get(name, [])))
        width = min(len(s) for s in per_position) if per_position else 0
        means, stds = [], []
        for i in range(width):
            col = [s[i] for s in per_position if i < len(s)]
            means.append(round(statistics.fmean(col), 3))
            stds.append(round(max(statistics.pstdev(col) if len(col) > 1 else STD_FLOOR_MS, STD_FLOOR_MS), 3))
        profile[name] = {"means": means, "stds": stds}
    return profile


def distance(profile, holds, intervals):
    distances = []
    for name, values in (("holds", holds), ("intervals", intervals)):
        stat = profile.get(name)
        if not stat or not stat["means"]:
            continue
        means = stat["means"]
        stds = stat["stds"]
        clipped = _clip(values)
        if not clipped:
            continue
        for i in range(min(len(means), len(clipped))):
            sigma = max(stds[i], STD_FLOOR_MS)
            d = (clipped[i] - means[i]) / sigma
            distances.append(d * d)
    if not distances:
        return float("inf")
    return math.sqrt(sum(distances) / len(distances))


def is_match(profile, holds, intervals):
    d = distance(profile, holds, intervals)
    return d <= MATCH_THRESHOLD, round(d, 2)
