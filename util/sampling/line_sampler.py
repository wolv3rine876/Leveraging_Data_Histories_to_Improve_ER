from os import listdir
from os.path import isfile, join
from click import echo
import numpy as np


class LineSampler:
  """
    Allows to randomly sample lines in files. Therefore it returns the file-path and byte-offset of the sampled line.
  """
    
  def __init__(self, paths):
    if type(paths) is str:
      paths = [paths]

    self._paths = paths
    self._sample_idx = 0

    files = [path for path in paths if isfile(path)] + [join(path, f) for path in [directory for directory in paths if not isfile(directory)] for f in listdir(path) if isfile(join(path, f))]

    echo(F"Sampling from {len(files)} files. This might take a while...")
    
    self._values = []
    for file_name in files:
      # find the line beginnings
      with open(file_name, "rb") as file:
        self._values.append((file_name, file.tell()))
        for _ in file:
          self._values.append((file_name, file.tell()))
        # remove the last values, as no line starts at the EOF
        self._values.pop()
    
    np.random.shuffle(self._values)

  def choice(self):
    if(self._sample_idx == len(self._values)):
      self._sample_idx = 0
      np.random.shuffle(self._values)

    file, byte_offset = self._values[self._sample_idx]
    self._sample_idx += 1

    return file, byte_offset
  
  def split(self, split=0.8, size: float=None):
    """
      Splits the shuffled data by the given factor. If size is given, the total size is reduced to the given size factor,
    """
    
    if(0 >= split >= 1):
      raise ValueError("Factor has to be in (0, 1)")
    if(0 >= size > 1):
      raise ValueError("Size has to be in (0, 1]")
    
    vals = self._values

    if size:
      vals = vals[0 : round(size * len(vals))]
    
    split_idx = round(split * len(vals))
    return vals[: split_idx], vals[split_idx:]



