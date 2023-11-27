import click

from labeling.col_match_labeling import col_matching
from labeling.row_match_labeling import row_matching
from labeling.sub_col_labeling import sub_col
from labeling.error_labeling import errors

@click.group()
def label():
  """Utilities for handlabeling."""
  pass

label.add_command(col_matching)
label.add_command(row_matching)
label.add_command(sub_col)
label.add_command(errors)