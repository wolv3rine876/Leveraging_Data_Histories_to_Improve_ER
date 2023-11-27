import os
from os.path import join
from typing import AnyStr

class RotatingFileWriter:
    
  def __init__(self, dir: str, mode: str, encoding: str=None, base_name: str="", extension: str="", max_MB:int=200):

    self.dir = dir
    self.mode = mode
    self.encoding = encoding
    self.base_name = base_name
    self.extension = extension
    self.max_MB = max_MB
    self._file = None
    self._counter = 1

  def write(self, s: AnyStr):
    self._rotate_if_needed()
    self._file.write(s)
    
  def __enter__(self):
    self._open_file()
    return self

  def __exit__(self, type, value, traceback):
    if self._file:
      self._file.close()

  def _rotate_if_needed(self):
    # Remember the old position of the cursor
    old_cursor_pos = self._file.tell()

    # get the file size
    self._file.seek(0, os.SEEK_END)
    size = self._file.tell()

    # reset the cursor
    self._file.seek(old_cursor_pos)

    # rotate if file is too large
    if size > self.max_MB * 1000000:
      self._file.close()
      self._counter += 1
      self._open_file()

  def _open_file(self):
    self._file = open(join(self.dir, self.base_name + str(self._counter) + self.extension), self.mode, encoding=self.encoding)

