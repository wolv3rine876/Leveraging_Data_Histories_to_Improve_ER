import click

from aggr.aggregator import aggregate
from aggr.reformatter import reformat

@click.group()
def aggr():
  """Utilities for aggregating per-revision classifications (zipping)."""
  pass

aggr.add_command(aggregate)
aggr.add_command(reformat)