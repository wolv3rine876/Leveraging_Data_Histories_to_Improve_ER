import datetime
from genericpath import isfile
import locale
import click
from click import echo
import json
import numpy as np
from os import listdir
from os.path import join
from util.sampling.line_sampler import LineSampler
from util.html.html_util import transform_to_matrix, get_cols
from util.wiki.wiki_table_util import get_tr
from util.wiki.wikilink_util import build_wikipedia_url

_LABELED_FILE_NAME = "row-history-labels.json"

@click.command()
@click.argument('src', type=str)
@click.argument('dest', type=str)
@click.option('-s', '--size', type=int, default=200, help='Number of tables to sample.')
def row_matching(src, dest, size):
  """Command-line utility for handlabeling row matches."""

  label_file = join(dest, _LABELED_FILE_NAME)
  counter = 0
    
  files = [src]
  if not isfile(src):
    files = [join(src, f) for f in listdir(src)]
  sampler = LineSampler(files)

  try:

    while counter < size:

      if counter > 0 and counter % 10 == 0:
        _stats(label_file)
      
      doc = None

      # Choose a random doc
      file_path, offset = sampler.choice()
      with open(file_path, "rb") as file:
        file.seek(offset)
        doc = json.loads(file.readline())
      
      page_name = doc["pageTitle"]
      rows = doc["rows"]

      # Choose a random row and revision
      rnd_row = np.random.choice(rows)
      rnd_rev_idx = np.random.randint(0, len(rnd_row["revisions"]))
      rnd_rev = rnd_row["revisions"][rnd_rev_idx]

      # Find the previous revision
      prev_rev_id = None
      prev_rev_row_position = -1
      prev_rev_row_content = None

      # Sort the table's revisions by date
      if locale.getlocale()[0] != "en_US":
        locale.setlocale(locale.LC_ALL, 'en_US.utf8')
      revisions = set([(rev["revisionID"], datetime.datetime.strptime(rev["revisionDate"], "%b %d, %Y, %I:%M:%S %p")) for row in rows for rev in row["revisions"]])
      revisions = sorted(revisions, key=lambda r: r[1]) # sort by date
      revisions = [r[0] for r in revisions] # map to revisionID

      # find the index of the random revision
      idx = revisions.index(rnd_rev["revisionID"])
      # No previous revision exists -> we choose the first revision of the table and have no predecessor to compare against
      if idx == 0:
        continue
      prev_rev_id = revisions[idx-1]
      # Check if prev_rev_id is also the predecessor of rnd_rev. If so, get the position of the matched row
      if rnd_rev_idx > 0 and rnd_row["revisions"][rnd_rev_idx-1]["revisionID"] == prev_rev_id:
        prev_rev_row_position = rnd_row["revisions"][rnd_rev_idx-1]["position"]
        prev_rev_row_content = get_tr(rnd_row["revisions"][rnd_rev_idx-1])

      # built the previous table
      schema = doc["schemas"][str(prev_rev_id)]
      body = [rev for row in rows for rev in row["revisions"] if rev["revisionID"] == prev_rev_id]
      body.sort(key=lambda r: r["position"])

      # - Output -
      # Pagename + link
      echo(f"\nPagename: {page_name}        ({build_wikipedia_url(page_name, prev_rev_id)}) -> ({build_wikipedia_url(page_name, rnd_rev['revisionID'])})")
      
      # Changed
      contentChange = prev_rev_row_content != get_tr(rnd_rev)
      positionChange = prev_rev_row_position != rnd_rev["position"]
      echo(f"Changed: {contentChange or positionChange}")
      
      # Previous schema
      for row in transform_to_matrix(schema):
        echo(f'   {row}')
      
      # Previous Body
      for row in body:
        idx = row["position"]
        output = f'{idx}  {get_cols(get_tr(row))}'
        if idx == prev_rev_row_position:
          output = "----------\n>" + output + "<\n----------"
        echo(output)

      # Current row
      echo("\n")
      echo(f'{rnd_rev["position"]}  {transform_to_matrix(get_tr(rnd_rev))[0]}')

      # Read true row index
      valid_prompt = False
      while not valid_prompt:

        prompt = input(">").lower()

        try:
          prompt = int(prompt)
          valid_prompt = True

          output = {
            "pageID": doc["pageID"],
            "tableID": doc["tableID"],
            "revisionID": rnd_rev["revisionID"],
            "position": rnd_rev["position"],
            "previousPosition": prev_rev_row_position,
            "truePreviousPosition": prompt,
            "contentChange": contentChange,
            "positionChange": positionChange
          }

          with open(label_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(output, ensure_ascii=False) + "\n")

        except:
          echo("Unknown number format. Try again...")
      
      counter += 1

  except KeyboardInterrupt:
    pass
  
  _stats(label_file)

def _stats(label_file: str):

  def _print(labels: list):

    TP = 0
    FP = 0
    TN = 0
    FN = 0

    for label in labels:

      matched_pos = label["previousPosition"]
      true_pos = label["truePreviousPosition"]

      # Both have the same predecessor
      if matched_pos > -1 and matched_pos == true_pos:
        TP += 1
      # Both have no predecessor
      elif matched_pos == -1 and true_pos == -1:
        TN += 1
      # Missing match
      elif matched_pos == -1 and true_pos > -1:
        FN += 1
      # Additional match
      elif matched_pos > -1 and true_pos == -1:
        FP += 1
      # Wrong match
      elif matched_pos > -1 and true_pos > -1 and matched_pos != true_pos:
        FP += 1
        FN += 1
    
    precision = TP / (TP + FP)
    recall = TP / (TP + FN)
    f1 = (2 * TP) / (2 * TP + FP + FN)

    echo(f"Sample size      : {len(labels)}")
    echo(f"Precision        : {precision}")
    echo(f"Recal            : {recall}")
    echo(f"F1               : {f1}")

  with open(label_file, "rb") as file:

    docs = [json.loads(line) for line in file]

    echo(f"\n========== Stats ==========")
    echo("===== Overall =====")
    _print(docs)
    echo("===== Changes =====")
    _print(list(filter(lambda d: d["positionChange"] or d["contentChange"], docs)))
