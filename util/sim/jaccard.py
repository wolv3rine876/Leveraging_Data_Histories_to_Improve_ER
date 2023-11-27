import re

def jaccard_similarity(s1, s2) -> float:
  """
    Computes the jaccard similarity of the two values.
    s1 and s2 can be strings or sets of unique strings.
  """

  if type(s1) is str:
    s1 = _text_to_set(s1)
  if type(s2) is str:
    s2 = _text_to_set(s2)

  intersection = len(list(s1.intersection(s2)))
  union = (len(s1) + len(s2)) - intersection
  if union > 0:
    return float(intersection) / union
  return 0

def jaccard_similarities(s, sN):
  """
    Computes the jaccard similirity of s (str, or set) with values in sN (list(str) or list(set)).
    Returns a generator that yields the similarity and the index of the value s was compared to.
  """

  for i in range(len(sN)):
    yield jaccard_similarity(s, sN[i]), i

def _text_to_set(text: str) -> set:
  """
    Splits the text by whitespaces, removes empty strings and returns a set of unique values (unsorted)
  """
  
  return set([s for s in re.split("\W", text) if s])