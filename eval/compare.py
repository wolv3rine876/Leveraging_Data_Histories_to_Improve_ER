import click

from eval.metrics import compute_metrics

@click.command() 
@click.argument('base_src', type=str)
@click.argument('compare_src', type=str)
@click.argument('truth', type=str)
def compare(base_src, compare_src, truth):
  """Computes an error matrix for comparison of the predictions by base and compare.
     truth should be the file with the ground truth labels.
  """
  
  bTP, bTN, bFP, bFN = compute_metrics(base_src, truth)
  cTP, cTN, cFP, cFN = compute_metrics(compare_src, truth)

  bT = [tp or tn for tp, tn in zip(bTP, bTN)]
  cT = [tp or tn for tp, tn in zip(cTP, cTN)]

  bases = [bT, bFP, bFN]
  comps = [cT, cFP, cFN]


  results = [[len([1 for c, v in zip(cVals, bVals) if c and v]) for cVals in comps] for bVals in bases]

  click.echo(f"--------------- Comp ---------------")
  click.echo(f"       TP/TN,    FP,    FN")
  for label, val in zip(["TP/TN", "FP", "FN"], results):
    click.echo(f"{_pad(label)}: {_pad(val[0])}, {_pad(val[1])}, {_pad(val[2])}")


def _pad(n, places: int=5):
  n = str(n)
  return "".join([" " for _ in range(max(places - len(n), 0))]) + n