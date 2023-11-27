import click

from eval.metrics import metrics
from eval.compare import compare

@click.group()
def eval():
  """Utility for evaluating the final predictions by ditto."""
  pass

eval.add_command(metrics)
eval.add_command(compare)