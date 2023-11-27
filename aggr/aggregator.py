import json
import logging
import click
from aggr.aggregators.majority_aggregator import MajorityAggregator
from aggr.aggregators.newest_aggregator import NewestAggregator


logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(levelname)s [%(process)d] - %(message)s")

_aggr_builders = {
  "majority": lambda s: MajorityAggregator(**s),
  "newest": lambda s: NewestAggregator(**s),
}

@click.command()
@click.argument('src', type=str)
@click.argument('dest', type=str)
@click.option('-aggr', '--aggregator', type=str, default='majority', help='The aggregator to use for aggregating the src classifications (majority)')
@click.option('-gs', '--aggregator-settings', type=(str, bool), default=dict(), multiple=True, help='Settings passed to the selected aggregator')
def aggregate(src, dest, aggregator, aggregator_settings):
  """Aggregates the per-revision predictions when using zipping.
     The input should first be reformatted using /aggr/reformatter.py
  """
  
  aggr = _aggr_builders[aggregator](dict(aggregator_settings))

  entitiy_classifications = []

  with open(src, "rb") as src_file:
    entitiy_classifications = [json.loads(line) for line in src_file]

  TP = 0
  FP = 0
  FN = 0
  TN = 0
  
  with open(dest, "w", encoding="utf-8") as dest_file:

    for rev_classifications in entitiy_classifications:
      
      prediction = aggr.aggr(rev_classifications)
      match = rev_classifications[0]["match"]
      if prediction and match:
        TP += 1
      elif not prediction and not match:
        TN += 1
      elif not prediction and match:
        FN += 1
      elif prediction and not match:
        FP += 1
      
      dest_file.write(json.dumps({"match": prediction}, ensure_ascii=False) + "\n")

  precision = TP / (TP + FP) if TP + FP != 0 else 1
  recall = TP / (TP + FN) if TP + FP != 0 else 1
  F1 = 2 * ((precision * recall) / (precision +  recall))

  click.echo(f"Precision: {precision}, recall: {recall}, F1: {F1}")