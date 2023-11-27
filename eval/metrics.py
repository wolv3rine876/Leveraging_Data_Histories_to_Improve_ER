import json
import click

@click.command() 
@click.argument('src', type=str)
@click.argument('truth', type=str)
def metrics(src, truth):
  """Computes precision and recall for the predictions at truth and ground truth labels at truth."""

  TP, TN, FP, FN = compute_metrics(src, truth)

  TP = len([1 for v in TP if v])
  TN = len([1 for v in TN if v])
  FP= len([1 for v in FP if v])
  FN = len([1 for v in FN if v])

  precision = TP / (TP + FP)
  recall = TP / (TP + FN)
  f1 = 2 * ((precision * recall) / (precision + recall))

  click.echo(f"Precision: {round(precision * 100, 2)}%, Recall: {round(recall * 100, 2)}%, F1: {round(f1 * 100, 2)}%")

def compute_metrics(src, truth):

  predictions = []
  with open(src, "rb") as file:
    predictions = [True if json.loads(line)["match"] == 1 else False for line in file]
  
  truths = []
  with open(truth, "r", encoding="utf-8") as file:
    truths = [line.strip().split('\t')[2].strip() == str(1) for line in file]

  assert len(predictions) == len(truths)
  
  TP = [p and t for p, t in zip(predictions, truths)]
  FP = [p and not t for p, t in zip(predictions, truths)]
  TN = [not p and not t for p, t in zip(predictions, truths)]
  FN = [not p and t for p, t in zip(predictions, truths)]

  return TP, TN, FP, FN