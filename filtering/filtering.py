import datetime
from os import listdir
from os.path import isfile, join, exists
from multiprocessing import Pool
import json
import logging
import re
from click import echo
import numpy as np
import click
from util.wiki.wiki_table_util import get_tr

from util.wiki.wikilink_util import extract_wikilink, parse_wiki_date
from util.html.html_util import get_text, contains_list

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(levelname)s [%(process)d] - %(message)s")

# Threshold for subject column scores by TableMiner+. This score was received by manually labeling subject columns and provides the best trade-off
# between precision and recall.
_THRESHOLD = 0.969

@click.command()
@click.argument('src', type=str)
@click.argument('dest', type=str)
@click.option('-l', '--labeled', type=str, default=None, help='Path to labeled subject column file (see the label sub-col command)')
@click.option('-f', '--force', type=bool, default=False, is_flag=True, help='Overwrite already processed files at dest.')
@click.option('-p', '--processes', type=int, default=None, help='The number of processes to use. If not given, the CPU\'s max. will be used.')
def filter(src, dest, labeled, force, processes):
  """Implementation of the filtering stage of the data creation pipeline."""

  # get the files
  src_files = set(f for f in listdir(src) if isfile(join(src, f)) and f.endswith(".json"))
  # process only the files that are not yet in dest
  if not force:
    dest_files = set(f for f in listdir(dest) if isfile(join(dest, f)) and f.endswith(".json"))
    src_files = src_files - dest_files

  logging.info(f'Found {len(src_files)} files to process.')

  # start processes
  with Pool(processes) as p:
    input = [(src, dest, file, labeled) for file in src_files]
    try:
      results =  np.array(p.starmap(_filter_file, input))

      # print stats
      skipped_tables = sum(results[:,0])
      matched_tables = sum(results[:,1])
      skipped_rows = sum(results[:,2])
      matched_rows = sum(results[:,3])
      hist_lens = [val for sublist in results[:,4] for val in sublist]
      row_lens = [val for sublist in results[:,5] for val in sublist]
    
      echo(f"#Ignored tables={skipped_tables}")
      echo(f"#Accepted tables={matched_tables}")
      echo(f"#Ignored rows={skipped_rows}")
      echo(f"#Accepted rows={matched_rows}")
      echo(f"Histories per row: max={np.max(hist_lens)}, avg={np.mean(hist_lens)}, median={np.median(hist_lens)}")
      echo(f"Rows per table: max={np.max(row_lens)}, avg={np.mean(row_lens)}, median={np.median(row_lens)}")

      logging.info("Processed all files.")
    except KeyboardInterrupt:
      p.terminate()
      logging.info("Aborting")


def _filter_file(src_dir: str, dest_dir: str, file_name: str, labeled_file: str):

  skipped_tables = 0
  matched_tables = 0
  skipped_rows = 0
  matched_rows = 0
  hist_lens = []
  row_lens = []

  # Use manually labeled columns if existant
  labed_subject_cols = dict()
  if labeled_file and exists(labeled_file):
    logging.info(f"Found file with labeled subject columns at {labeled_file}")
    with open(labeled_file, "rb") as file:
      for line in file:
        doc = json.loads(line)
        labed_subject_cols[doc["tableID"]] = doc["trueSubjectColumnIndex"]
  
  with open(join(src_dir, file_name), "rb") as src_file:
    
    dest_file = None

    for line in src_file:
      
      # parse each line as json
      doc = json.loads(line)
            
      page_title = doc["pageTitle"]
      table_id = doc["tableID"]
      rows = doc["rows"]

      if "subjectColumnIndex" not in doc or "subjectColumnProbability" not in doc:
        skipped_tables += 1
        skipped_rows += len(rows)
        continue

      subject_col_idx = doc["subjectColumnIndex"]
      subject_col_score =  doc["subjectColumnProbability"]

      # Ignore tables with a subject column score below the threshold.
      if subject_col_score <= _THRESHOLD and table_id not in labed_subject_cols:
        skipped_tables += 1
        skipped_rows += len(rows)
        continue

      if table_id in labed_subject_cols:
        doc["subjectColumnIndex"] = subject_col_idx = labed_subject_cols[table_id]

      # tables with just one or two rows are mostly used for layout and therefore uninteresting
      if len(rows) < 3:
        skipped_tables += 1
        skipped_rows += len(rows)
        continue

      # all rows that satisfy the filtering
      filtered_rows = []
      # all revision ids that are contained in filtered_rows
      contained_revision = set()

      for row in rows:

        revisions = row["revisions"]

        # some rows are just used for foodnotes.
        revisions = [rev for rev in revisions if re.match("{{nodelist.*}}", get_tr(rev)) is None]

        # Check if this rows schema matches the one used for subject column detection
        if len(revisions) == 0 or doc["schemas"][str(doc["lastRevisionID"])] != doc["schemas"][str(revisions[-1]["revisionID"])]:
          skipped_rows += 1
          continue

        # filter rows that existed only for a month or less
        revisions = sorted(revisions, key=lambda r: parse_wiki_date(r["revisionDate"]))
        first_revision_date = parse_wiki_date(revisions[0]["revisionDate"])
        last_revision_date = parse_wiki_date(revisions[-1]["revisionDate"])
        if abs(last_revision_date - first_revision_date) < datetime.timedelta(days=30):
          skipped_rows += 1
          continue

        # filter all revisions that contributed no meaningful value in comparinson to the revision before (e.g. whitespace added or css changed).
        # In rare cases, someone added a new link, 
        filtered_revisions = [revisions[0]]
        last_link = extract_wikilink(get_tr(revisions[0]), page_title, subject_col_idx)
        last_link = last_link[0] if last_link else last_link
        last_text = get_text(get_tr(revisions[0]), page_title)

        for r in revisions[1:]:
          new_link = extract_wikilink(get_tr(r), page_title, subject_col_idx)
          new_link = new_link[0] if new_link else new_link
          new_text = get_text(get_tr(r), page_title)

          # Pure text changed
          if re.sub("\W", "", last_text) != re.sub("\W", "", new_text):
            filtered_revisions.append(r)
          
          # Rare: text did not change but new link was added.
          # -> replace the old revision (they have the same meaning but just different links)
          elif last_link != new_link:
            filtered_revisions[-1] = r
          
          last_link = new_link
          last_text = new_text
        
        row["revisions"] = filtered_revisions

        # mark the 'new' last revision as deleted, if the old one was deleted
        if revisions[-1] != filtered_revisions[-1] and "deleted" in revisions[-1] and "deleted" not in filtered_revisions[-1]:
          filtered_revisions[-1]["deleted"] = revisions[-1]["deleted"]
          filtered_revisions[-1]["deleteDate"] = revisions[-1]["deleteDate"]

        # consider only rows with more than two revision remaining
        if len(filtered_revisions) < 3:
          skipped_rows += 1
          continue

        last_revision = filtered_revisions[-1]

        link_results = extract_wikilink(get_tr(last_revision), page_title, subject_col_idx)

        # no or too many links found
        if not link_results or len(link_results) != 1:
          skipped_rows += 1
          continue

        link_result = link_results[0]
        if not link_result.pagename or link_result.pagename == "":
          skipped_rows += 1
          continue
        
        # Often <table>s are used as layout tables to structure <ul>s. Thus they contain many entities.
        # But somestimes <ul>s are just used to style bullet points in front of an element.
        # So we filter all rows that have a <ul> with at least 3 <li>
        if contains_list(get_tr(last_revision), 3):
          skipped_rows += 1
          continue

        filtered_rows.append(row)
        matched_rows += 1

        contained_revision.update([str(r["revisionID"]) for r in filtered_revisions])

        row["link"] = {
          "namespace": link_result.namespace,
          "pageName": link_result.pagename,
          "anchor": link_result.anchor,
          "text": link_result.display_text,
          "match": link_result.match
        }

        # remove unneeded props
        for revision in revisions:
          revision.pop("similarityFirst", None)
          revision.pop("similarityLast", None)
          revision.pop("contentType", None)

        hist_lens.append(len(filtered_revisions))
      
      if len(filtered_rows) == 0:
        skipped_tables += 1
        logging.info(f'Skipping table {doc["tableID"]} on page {doc["pageTitle"]}')
        continue

      doc["rows"] = filtered_rows
      doc.pop("lastRevisionID", None)
      doc.pop("lastTable", None)
      # Exclude table header of revisions that were removed completly
      doc["schemas"] = {k: v for k, v in doc["schemas"].items() if k in contained_revision}

      matched_tables += 1
      row_lens.append(len(filtered_rows))

      # Open the file if not yet done
      if not dest_file:
        dest_file = open(join(dest_dir, file_name), "w", encoding="utf-8")

      try:
        output = json.dumps(doc, ensure_ascii=False) + "\n"
        dest_file.write(output)
      except:
        logging.error(f'Error while writing table {doc["tableID"]} on page {doc["pageTitle"]}')
        skipped_tables += 1
        skipped_rows += len(rows)
    
      logging.info(f'Processed table {doc["tableID"]} on page {doc["pageTitle"]}')

    if dest_file:
      dest_file.close()
  
  logging.info(f'Processed {file_name}.')
  
  return (skipped_tables, matched_tables, skipped_rows, matched_rows, hist_lens, row_lens)