import json
from math import floor
from multiprocessing import Pool
from os import walk
import os
from os.path import join, exists
import logging
import click
from sampling.formatter.revision_oriented.ro_concat_hist_formatter import ROConcatHistFormatter
from sampling.formatter.attribute_oriented.concat_hist_distinct_formatter import ConcatHistDistinctFormater
from sampling.formatter.attribute_oriented.concat_hist_formatter import ConcatHistFormater
from sampling.formatter.attribute_oriented.concat_hist_time_formatter import ConcatHistTimeFormatter

from sampling.formatter.attribute_oriented.no_hist_formatter import NoHistPromptFormatter
from sampling.formatter.revision_oriented.ro_concat_hist_time_formatter import ROConcatHistTimeFormatter
from util.rev.revision_util import get_rev_at_time, nearest_time
from util.wiki.wikilink_util import parse_wiki_date

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(levelname)s [%(process)d] - %(message)s")

_fmt_builders = {
  "nohist": lambda s: NoHistPromptFormatter(**s),
  "concat_hist": lambda s: ConcatHistFormater(**s),
  "concat_hist_distinct": lambda s: ConcatHistDistinctFormater(**s),
  "concat_hist_time": lambda s: ConcatHistTimeFormatter(**s),
  "ro_concat_hist": lambda s: ROConcatHistFormatter(**s),
  "ro_concat_hist_time": lambda s: ROConcatHistTimeFormatter(**s)
}

_splits = {
  "train": .6,
  "valid": .2,
  "test": .2,
}

@click.command()
@click.argument('src', type=str) 
@click.argument('dest', type=str)
@click.option('-fmt', '--formatter', type=str, default='nohist', help='The formatter to use for generating the output (nohist)')
@click.option('-fs', '--formatter-settings', type=(str, bool), default=dict(), multiple=True, help='Keyword args. passed to the formatter.')
@click.option('-z', '--zipped', type=bool, default=False, is_flag=True, help='Zip revisions')
@click.option('-za', '--zip-align', type=bool, default=False, is_flag=True, help='Align when zipping revisions')
@click.option('-n', '--name', type=str, default=None, help='How to name the output. If not set, the formatters config name will be used.')
def gen_prompts(src, dest, formatter, formatter_settings, zipped, zip_align, name):
  """Transforms (serializes) the json sample into the different, proposed text formats.
     Check out /sampling/formatter for more docs.

     Splits the output into train- (60%), validation- (20%) and testset (20%).
  """

  if sum(_splits.values()) != 1:
    raise AttributeError("Invalid split.")

  # init formatter
  fmt = _fmt_builders[formatter](dict(formatter_settings))

  # get output name
  if not name:
    name = f"{'zipped_' if zipped else ''}{'aligned_' if zip_align else ''}{fmt.get_config_name()}"

  dest = join(dest, name)

  if not exists(dest):
    os.mkdir(dest)

  files = [join(dir, file) for dir, _, files in walk(src) for file in files if file.endswith(".json")]

  with Pool(len(files)) as p:
    input = [(file_path, dest, fmt, zipped, zip_align) for file_path in files]
    p.starmap(_format_file, input)

def _format_file(file_path, dest, fmt, zipped, zip_align):
  with open(file_path, "rb") as src_file:

    # count lines
    size = len([1 for _ in src_file])
    src_file.seek(0)

    # Get the size name from the path
    size_name = os.path.basename(os.path.normpath(file_path))
    size_name = size_name[:size_name.index(".")]

    # output test, train and validation split
    for split_name, split_size in _splits.items():
      
      # stores which line / prompt belongs to a pair of entities.
      # This is needed to find all classifications that belong to a pair when using the aggregation method (zipping)
      revision_idx = []

      with open(join(dest, f"{split_name}.txt.{size_name}"), "w", encoding="utf-8") as dest_file:
        for _ in range(floor(size * split_size)):

          line = src_file.readline()
          doc = json.loads(line)

          is_match = doc["match"]

          revs1 = doc["row1"]["revisions"]
          revs2 = doc["row2"]["revisions"]

          formatting_pairs = [(revs1, revs2)]

          if zipped:
            
            if not zip_align:
              # Implementation of zip(e,e')
              max_revs = min(len(revs1), len(revs2))
              formatting_pairs = [([r1], [r2]) for r1, r2 in zip(list(reversed(revs1))[:max_revs], list(reversed(revs2))[:max_revs])]
            else:
              # Implementation of zipNearest(e,e')
              dates = list(map(lambda r: parse_wiki_date(r["revisionDate"]), revs1)) + list(map(lambda r: parse_wiki_date(r["revisionDate"]), revs2))
              # Prune duplicate pairs by using a set
              formatting_pairs = {(nearest_time(revs1, t), nearest_time(revs2, t)) for t in dates}
              formatting_pairs = [([get_rev_at_time(revs1, t1)], [get_rev_at_time(revs2, t2)]) for t1, t2 in sorted(formatting_pairs, key=lambda t: min(*t))]

          entity_pair = dict(match=is_match)

          # format each (potentially zipped) pair of revisions
          for revs1, revs2 in formatting_pairs:
            entry1 = fmt.format_entry(revs1, revs2)
            entry2 = fmt.format_entry(revs2, revs1)
          
            # Entries might be empty if there was no real schema detected.
            if not entry1 or not entry2:
              continue

            prompt = f"{entry1} \t {entry2} \t {1 if is_match else 0}"

            dest_file.write(prompt + "\n")

            if zipped:
              revs = entity_pair.setdefault("revisions", [])
              revs.append({
                "leftP": entry1,
                "rightP": entry2,
                "left": { "revisionDate": revs1[0]["revisionDate"] },
                "right": { "revisionDate": revs2[0]["revisionDate"] }
              })
          
          if zipped:
            revision_idx.append(entity_pair)
      
      if len(revision_idx) > 0:
        with open(join(dest, f"{split_name}.txt.{size_name}.index"), "w", encoding="utf-8") as file:
          file.write(json.dumps(revision_idx, ensure_ascii=False))
