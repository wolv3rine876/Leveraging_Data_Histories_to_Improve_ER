from collections import Counter
import json
from math import floor
from os import listdir
import os
from os.path import isfile, join
from multiprocessing import JoinableQueue, Pool, Process, Queue
import logging
import numpy as np
import click
from util.sim.jaccard import jaccard_similarity
from util.html.html_util import get_text
from shutil import rmtree
from util.wiki.wiki_table_util import get_tr

from util.wiki.wikilink_result import WikilinkResult

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: %(levelname)s [%(process)d] - %(message)s")

@click.command()
@click.argument('src', type=str)
@click.argument('dest', type=str)
@click.option('-s', '--size', type=int, default=200, help='The number of pairs to build')
@click.option('-idx', '--index', type=str, default="matches.index", help='The name of the index file in src. If not found, the index will be computed.')
@click.option('-p', '--processes', type=int, default=None, help='The number of processes to use. If not given, the CPU\'s max. will be used.')
def sample(src, dest, size, index, processes):
  """
    Implementation of the sampling stage of the data creation pipeline.
    Chooses random positive and negative row-pairs. For negative row-pairs, it chooses the most (jaccard) similar row that has a different link.
    Subsamples the given size into 5% (s), 10% (m), 50% (l) and 100% (xl) outputs.

    The index is a dictionary. Each key is a link and each value a list of identifiers that refer to the rows containing that key as link.
  """

  sizes = {
    "s": floor(.05 * size),
    "m": floor(.1 * size),
    "l": floor(.5 * size),
    "xl": size
  }

  # 50% matches 50% non-matches
  size = floor(size / 2)

  tmp_dir = join(dest, "tmp")
  if os.path.exists(tmp_dir):
    rmtree(tmp_dir)
  os.makedirs(tmp_dir)

  try:

    # ===== Build index =====
    idx_path = join(src, index)
    idx = None
    
    # check if the index already exists
    if isfile(idx_path):
      
      logging.info(f"Found exisitng index at {idx_path}")

      with open(join(src, index), "rb") as idx_file:
        idx = json.loads(idx_file.readline())
    
    # compute the index otherwise
    else:

      # get the files
      files = [f for f in listdir(src) if isfile(join(src, f)) and f.endswith(".json")]
      logging.info(f'Found {len(files)} files to sample from.')

      logging.info("Computing index")

      input = [(src, file) for file in files]
      indices = None
      with Pool(processes) as p:
        indices =  np.array(p.starmap(_build_matching_index, input))

      # find out which buckets contain more than one line -> more than one row referring to the same page.
      match_count = 0
      no_match_count = 0
      idx = dict()
      links = set([l for i in indices for l in i.keys()])

      for link in links:
        rows = []
        for i in indices:
          if link in i:
            rows.extend(i[link])
        
        row_count = len(rows)
        if row_count > 1:
          idx[link] = rows
          match_count += row_count
        else:
          no_match_count += row_count
      
      # output the index for the next time
      with open(idx_path, "w", encoding="utf-8") as file:

        logging.info(f"Writing index to {idx_path}")
        file.write(json.dumps(idx, ensure_ascii=False))
    
      # print stats
      total_count = no_match_count + match_count
      logging.info(f"{match_count} ({round(match_count / total_count * 100, 2)}%) rows have a match")
      logging.info(f"{total_count - match_count} ({round((total_count - match_count) / total_count * 100, 2)}%) rows have no match")

    # ===== Build matching pairs =====
    logging.info(f"========= Building matches ({size}) ========")
    pos_sims = _build_matches(src, tmp_dir, idx, size)

    # ===== Build non-matching pairs =====
    logging.info(f"========= Building non-matches ({size}) ========")
    #_build_non_matches(src, tmp_dir, idx, pos_sims)
    _build_no_matches(src, tmp_dir, idx, pos_sims)

    # ===== Output =====
    lines = []
    files = [f for f in listdir(tmp_dir) if isfile(join(src, f)) and f.endswith(".json")]
    for f in listdir(tmp_dir):
      with open(join(tmp_dir, f), "rb") as file:
        lines += [l for l in file]

    np.random.shuffle(lines)

    # split into different sizes
    for size_name, size in sizes.items():

      size_dest = join(dest, size_name)
      if not os.path.exists(size_dest):
        os.makedirs(size_dest)

      with open(join(size_dest, size_name + ".json"), "wb") as file:
        
        for line in lines[0:size]:
          file.write(line)

    logging.info("Processed all files.")

    rmtree(tmp_dir)

  except KeyboardInterrupt:
    p.terminate()
    logging.info("Aborting")

def _build_matching_index(src_dir: str, file_name: str):
  """
    Group all rows in the given file by their respective wikilink.
    Returns a dict. Each key is the identified link. Each value is a list of tuples.
    Each tuple identifies a specific row by file_name (index 0), byte_offset (index 1) and row_idx (index 2).
    Additionally, table_id is stored at index 3 and the latest content at index 4 to avoid fetching a file just to look up a table id or to compute similarity.
  """

  index = dict()

  with open(join(src_dir, file_name), "rb") as src_file:

    offset = 0

    for line in src_file:
      
      doc = json.loads(line)
      page_title = doc["pageTitle"]

      for row_idx, row in enumerate(doc["rows"]):
        
        link = WikilinkResult.from_dict(row["link"])

        descriptors = index.setdefault(link.identifier, [])
        descriptors.append((file_name, offset, row_idx, doc["tableID"], get_text(get_tr(row["revisions"][-1]), page_title, " ").lower()))
      
      offset = src_file.tell()

  return index

def _build_matches(src_dir: str, dest_dir, index: dict, size: int):
  """
    Builds combinations of the rows in bucket and writes it to dest_dir
  """

  sims = []
  idx = 0
  seen_combs = set()

  values = [(identifier, pointer) for identifier, pointers in index.items() for pointer in pointers]
  np.random.shuffle(values)

  while len(sims) < size:
    
    choice = values[idx]
    identifier = choice[0]
    row_pointer1 = choice[1]

    idx += 1

    # choose a partner within the same bucket that is from a different table
    bucket = index[identifier]
    row_pointer2 = None

    while not row_pointer2 or row_pointer2 == row_pointer1:
      row_pointer2 = bucket[np.random.randint(0,len(bucket))]
    
    key1 = f"{row_pointer1[3]}-{str(row_pointer1[2])}"
    key2 = f"{row_pointer2[3]}-{str(row_pointer2[2])}"
    comb = "--".join(sorted([key1, key2]))

    # Same row
    if key1 == key2:
      continue

    # Seen combination
    if comb in seen_combs:
      continue
    
    sim = jaccard_similarity(row_pointer1[4], row_pointer2[4])
    pair = _format_pair(row_pointer1, row_pointer2, matching=True, dir=src_dir)

    with open(join(dest_dir, "matches.json"), "a", encoding="utf-8") as file:
      file.write(json.dumps(pair, ensure_ascii=False) + "\n")
    
    sims.append(sim)
    seen_combs.add(comb)
  
  return sims

def _build_no_matches(src_dir: str, dest_dir: str, index: dict, pos_sims: list):
  """Samples negatives pairs by starting a set of workers that try to find pairs that randomly fit into the similarity distribution of the positive pairs."""
  
  NUM_TASKS = min(80, os.cpu_count())

  # Build negative samples following the the positive pairs similarity dist.
  intervals = np.linspace(0, 1, 101)
  sims_digitized = np.digitize(pos_sims, intervals) - 1
  sim_dist = Counter({k: floor(v * 1.001) for k, v in Counter(sims_digitized).items()}) # allow overfilling of 1% per bucket
  values = [(identifier, pointer) for identifier, pointers in index.items() for pointer in pointers]
  seen_combs = set()
  neg_sim_dist = Counter()
  
  subq = Queue(NUM_TASKS * 10)
  recqs = [JoinableQueue() for _ in range(NUM_TASKS)]
  workers = [Process(target=_build_no_matches_worker, args=(values, intervals, sim_dist, subq, recqs[i])) for i in range(NUM_TASKS)]

  # start workers
  for worker in workers:
    worker.start()

  # as long as we have less neg. pairs as pos. pairs
  while len(pos_sims) > sum(neg_sim_dist.values()):
    
    # consume a pairs generated by a worker
    bucket_idx, pointer1, pointer2 = subq.get()

    key1 = f"{pointer1[3]}-{str(pointer1[2])}"
    key2 = f"{pointer2[3]}-{str(pointer2[2])}"
    comb = "--".join(sorted([key1, key2]))

    # check if the pair is already part of the sample
    if comb in seen_combs:
      continue

    # no more values needed for this bucket
    if sim_dist[bucket_idx] == neg_sim_dist[bucket_idx]:
      continue

    # accept the pair
    neg_sim_dist.update([bucket_idx])
    seen_combs.add(comb)

    # write to disc
    pair = _format_pair(pointer1, pointer2, matching=False, dir=src_dir)
    with open(join(dest_dir, "non_matches.json"), "a", encoding="utf-8") as file:
      file.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # inform (other) workers that this pair is not required anymore
    for q in recqs:
      q.put(bucket_idx)

    logging.info(f"{sum(neg_sim_dist.values())} / {len(pos_sims)}")
  
  # clear queue if needed
  while not subq.empty():
    subq.get()
  
  # kill workers
  for worker, q in zip(workers, recqs):
    q.join()
    worker.join()

  
def _build_no_matches_worker(values: list, intervals: np.ndarray, pos_dist: Counter, subq: Queue, recq: JoinableQueue):
  """A worker that randomly tries to find a sample that is required."""

  rnd = np.random.default_rng()
  neg_dist = Counter()

  # As long as not every required pair was found.
  while sum(pos_dist.values()) > sum(neg_dist.values()):

    # receive all updates
    while not recq.empty():

      # update the pairs we are looking fore
      bucket_idx = recq.get()
      neg_dist.update([bucket_idx])
      recq.task_done()

    # choose two random rows
    idx1, idx2 = rnd.integers(0, len(values), 2)
    identifier1, pointer1 = values[idx1]
    identifier2, pointer2 = values[idx2]

    # same link
    if identifier1 == identifier2:
      continue

    # compute similarity
    sim = jaccard_similarity(pointer1[4], pointer2[4])
    bucket_idx = np.digitize(sim, intervals) - 1
    
    # no more values needed for this similarity bucket
    if pos_dist[bucket_idx] == neg_dist[bucket_idx]:
      continue
    
    # publish the pair
    subq.put((bucket_idx, pointer1, pointer2))
  
  return

def _format_pair(pointer1: tuple, pointer2: tuple, matching: bool, dir) -> dict:

  rows = []
  for file_name, byte_offset, row_idx, _, _ in [pointer1, pointer2]:
    with open(join(dir, file_name), "rb") as file:
      file.seek(byte_offset)
      doc = json.loads(file.readline())
      
      row = doc["rows"][row_idx]
      # copy important props
      row["pageTitle"] = doc["pageTitle"]
      row["subjectColumnIndex"] = doc["subjectColumnIndex"]
      row["subjectColumnProbability"] = doc["subjectColumnProbability"]
      row["tableID"] = doc["tableID"]
      row["pageID"] = doc["pageID"]
      row["pageTitle"] = doc["pageTitle"]
      row["pageTitle"] = doc["pageTitle"]
      row.pop("clusterId")
      for rev in row["revisions"]:
        rev["schema"] = doc["schemas"][str(rev["revisionID"])]
      rows.append(row)

  return {
    "match": matching,
    "row1": rows[0],
    "row2": rows[1]
  }