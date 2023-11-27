class BaseAggregator:

  def aggr(self, classifications: list) -> bool:
    """
      Aggregates the classifications per revision to one final classification
    """
    raise NotImplementedError()