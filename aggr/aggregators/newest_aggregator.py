from aggr.aggregators.base_aggregator import BaseAggregator


class NewestAggregator(BaseAggregator):

  def aggr(self, classifications: list) -> bool:
    return classifications[0]["prediction"]