import numpy as np
from datetime import datetime

from util.wiki.wikilink_util import parse_wiki_date

def nearest_rev(revisions: list, t: datetime):
  """Find the revision with the lowest time distance to the given date."""

  dists = [dist(t, parse_wiki_date(rev["revisionDate"])) for rev in revisions]
  return revisions[np.argmin(dists)]

def nearest_time(revisions: list, t: datetime) -> datetime:
  """Find the revision date with the lowest time distance to the given date."""

  times = [parse_wiki_date(rev["revisionDate"]) for rev in revisions]
  dists = [dist(t, time) for time in times]
  return times[np.argmin(dists)]

def dist(t1: datetime, t2: datetime):
  """Compute the distance between two dates."""

  return abs(t1 - t2)

def get_rev_at_time(revisions: list, t: datetime):
  """Find the revision at the given time. Returns None if no revision matches the t."""

  rev_times = [(parse_wiki_date(rev["revisionDate"]), rev) for rev in revisions]
  for time, rev in sorted(rev_times, reverse=True, key=lambda rt: rt[0]):
    if time <= t:
      return rev
  return None