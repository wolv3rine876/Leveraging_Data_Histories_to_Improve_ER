from aggr.aggregators.base_aggregator import BaseAggregator


class MajorityAggregator(BaseAggregator):

  def aggr(self, classifications: list) -> bool:
    return len([1 for p in classifications if p["prediction"]]) >= len(classifications)