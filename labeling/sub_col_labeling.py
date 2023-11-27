import json
from os.path import join, exists

from click import echo
import numpy as np
import matplotlib.pyplot as plt

from util.html.html_util import get_text, get_cols
from util.wiki.wikilink_result import WikilinkResult

from util.wiki.wiki_constants import WIKIPEDIA_HOSTNANE
from urllib.parse import urljoin

from util.sampling.line_sampler import LineSampler

import click

_FILE_NAME = "labeled.json"

@click.command()
@click.argument('src', type=str)
@click.argument('dest', type=str)
def sub_col(src, dest):
  """Command-line utility for handlabeling subject columns."""

  stats(dest, True)

  echo("Command-line utility for hand-labeling.")
  echo("Enter the true zero-based index of the subject column. Enter -1 if there is not real subject column")
  echo(f"Add an additional 's' to save this example to {dest}.")
  echo("Press Ctrl + C to finish.")

  dest_file = join(dest, _FILE_NAME)

  # files = [f for f in listdir(src) if isfile(join(src, f))]
  seen_samples = set()
  
  sampler = LineSampler(src)

  if exists(dest_file):
    with open(dest_file, "rb") as file:
      seen_samples = set([json.loads(line)["tableID"] for line in file])
  
  try:

    while True:

      if len(seen_samples) > 0 and len(seen_samples) % 10 == 0:
        stats(dest)

      table_id = None
      doc = None

      while table_id is None or table_id in seen_samples:

        file_path, offset = sampler.choice()

        with open(file_path, "rb") as file:
          file.seek(offset)
          
          doc = json.loads(file.readline())
          table_id = doc["tableID"]
      
      # remember which rows have been checked
      seen_samples.add(table_id)

      subject_col_idx = doc["subjectColumnIndex"]
      page_name = doc["pageTitle"]
      row = doc["rows"][0]
      link = row["link"]
      last_revision = row["revisions"][-1]
      revision_date = last_revision["revisionDate"]
      wikilink = WikilinkResult(pagename=link["pageName"], anchor=link["anchor"], namespace=link["namespace"], display_text=link["text"], match=link["match"])
      ref = f"{link['namespace']}:{link['pageName']}#{link['anchor']}"
      content = f"{get_text(last_revision['content'], page_name)}"
      
      schema_cols = get_cols(doc["schemas"][str(last_revision["revisionID"])])
      schema_cols[subject_col_idx] = ">" + schema_cols[subject_col_idx] + "<"
      schema_cols = [ str(i) + ") " + schema_cols[i] for i in range(len(schema_cols))]
      schema = " || ".join(schema_cols)

      echo(f"\n========== {len(seen_samples)} ==========")
      echo(f"Pagename: {page_name}        ({urljoin('https://' + WIKIPEDIA_HOSTNANE, 'wiki/' + page_name.replace(' ', '_'))})")
      echo(f"Link    : {str(wikilink)}        ({wikilink.match})")
      echo(f"Date    : {revision_date}")
      echo(f"Index   : {subject_col_idx}")
      echo(f"Schema  : {schema}")
      echo(f"Content : {content}")

      valid_prompt = False
      while not valid_prompt:
        
        prompt = input(">").lower()

        if "s" in prompt:
          with open(join(dest, 'examples.json'), "a", encoding="utf-8") as file:
            output = {
              "pageTitle": page_name,
              "date": revision_date,
              "link": ref,
              "schema": schema,
              "content": content,
              "subjectColumnIndex": subject_col_idx
            }
            file.write(json.dumps(output, ensure_ascii=False) + "\n")
        
        prompt = prompt.replace("s", "")
        try:
          prompt = int(prompt)
          valid_prompt = True

          with open(dest_file, "a", encoding="utf-8") as file:
            doc["trueSubjectColumnIndex"] = prompt
            file.write(json.dumps(doc, ensure_ascii=False) + "\n")

        except:
          echo("Unknown number format. Try again...")

  except KeyboardInterrupt:
    stats(dest, True)

def stats(path: str, plot: bool=False):

  right = []
  wrong = []

  with open(join(path, _FILE_NAME), "rb") as file:
    
    for line in file:
      
      doc = json.loads(line)

      if doc["trueSubjectColumnIndex"] == doc["subjectColumnIndex"]:
        right.append(doc["subjectColumnProbability"])
      else:
        wrong.append(doc["subjectColumnProbability"])
  
  r = [v for v in right if v > 2.5]
  w = [v for v in wrong if v > 2.5]

  _print_stats(right, wrong)

  if plot:
    _plot(right, wrong)

def _print_stats(right_scores, wrong_scores):
  right_scores = np.array(right_scores)
  wrong_scores = np.array(wrong_scores)
  
  right = len(right_scores)
  wrong = len(wrong_scores)
  sample_size = right + wrong
  
  echo(f"\n========== Stats ==========")
  echo(f"Sample size      : {sample_size}")
  echo(f"Correct cols     : {right} ({round(right / sample_size * 100, 2)}%)")
  echo(f"Incorrect cols   : {wrong} ({round(wrong / sample_size * 100, 2)}%)")
  echo(f"Correct scores   : max={np.max(right_scores)}, avg={np.mean(right_scores)}, median={np.median(right_scores)}, std={np.std(right_scores)}")
  echo(f"Incorrect scores : max={np.max(wrong_scores)}, avg={np.mean(wrong_scores)}, median={np.median(wrong_scores)}, std={np.std(wrong_scores)}")

def _plot(right_scores, wrong_scores):

  minimum = min(np.min(right_scores), np.min(wrong_scores))
  maximum = max(np.max(right_scores), np.max(wrong_scores))

  thresholds = np.arange(minimum, maximum, 0.001)

  TP = np.array([len([v for v in right_scores if v > threshold]) for threshold in thresholds])
  FP = np.array([len([v for v in wrong_scores if v > threshold]) for threshold in thresholds])
  TN = np.array([len([v for v in wrong_scores if v <= threshold]) for threshold in thresholds])
  FN = np.array([len([v for v in right_scores if v <= threshold]) for threshold in thresholds])

  precision = TP / (TP + FP)
  recall = TP / (TP + FN)
  FPR = FP / (FP + TN)

  fig1, ax1 = plt.subplots(1, 1, figsize=(16, 9))
  ax1.scatter(FPR, recall, color="grey", s=2)
  ax1.set_xlabel("False-positive rate")
  ax1.set_ylabel("True-positive rate")
  ax1.set_xticks(np.arange(0, 1.05, 0.05))
  ax1.set_yticks(np.arange(0, 1.05, 0.05))  

  fig2, ax2 = plt.subplots(1, 1, figsize=(16, 9))
  ax2.scatter(recall, precision, color="grey", s=2)
  ax2.set_xlabel("Recall", fontsize=14)
  ax2.set_ylabel("Precision", fontsize=14)
  ax2.set_xticks(np.arange(0, 1.05, 0.05))
  ax2.set_yticks(np.arange(0, 1.05, 0.05))

  bucket_size = 0.01
  buckets = np.arange(0, maximum + bucket_size, bucket_size)
  right_buckets = [len([v for v in right_scores if bucket - bucket_size / 2 <= v < bucket + bucket_size / 2]) for bucket in buckets]
  wrong_buckets = [len([v for v in wrong_scores if bucket - bucket_size / 2 <= v < bucket + bucket_size / 2]) for bucket in buckets]
  fig3, ax3 = plt.subplots(1, 1, figsize=(16, 9))
  ax3.bar(buckets - bucket_size / 4, right_buckets, color="green", label="Positive", width=bucket_size / 2)
  ax3.bar(buckets + bucket_size / 4, wrong_buckets, color="red", label="Negative", width=bucket_size / 2)
  ax3.set_xlabel("Subect Column Scores", fontsize=14)
  ax3.set_ylabel("Absolute Frequency", fontsize=14)
  ax3.set_xticks(np.arange(0, 3.05, 0.25))
  ax3.set_yticks(np.arange(0, 251, 25))
  ax3.legend()

  fig4, ax4 = plt.subplots(1, 1, figsize=(16, 9))
  ax4.plot(thresholds, recall, color="green", label="Recall")
  ax4.plot(thresholds, precision, color="blue", label="Precision")
  ax4.plot(thresholds, FPR, color="purple", label="False-positive rate")
  ax4.set_xlabel("Threshold")
  # ax4.set_xticks(np.arange(0, 1.05, 0.05))
  # ax4.set_yticks(np.arange(0, 1.05, 0.05))
  ax4.legend()

  plt.show()
