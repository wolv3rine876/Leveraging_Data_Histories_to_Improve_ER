from sampling.formatter.base_prompt_formatter import BasePromptFormatter
from util.html.html_util import get_cols
from util.wiki.wiki_table_util import get_tr

class ROConcatHistFormatter(BasePromptFormatter):
  """
    ro: DISTINCT=False, SEP=False
    roUnq: DISTINCT=True, SEP=False
    roSep: DISTINCT=True, SEP=True
  """
    
  def __init__(self, DISTINCT: bool = False, SEP: bool = False):
    super().__init__()
    self.distinct = DISTINCT
    self.separated = SEP
    self.separator = f" {self.HIST} " if SEP else " "

  def format_entry(self, revs1: list, revs2: list) -> str:

    seen_pairs = set()
    fmtd_revisions = []

    for revision in reversed(revs1):

      cols = get_cols(revision["schema"])
      vals = get_cols(get_tr(revision))

      row = {k: v for k, v in zip(cols, vals) if (k, v) not in seen_pairs}
      fmtd_revisions.append(self.dict_to_entry(row))

      if self.distinct:
        seen_pairs.update(zip(cols, vals))

    return self.separator.join(fmtd_revisions)
  
  def get_config_name(self):
    if not self.distinct and not self.separated:
      return "ro"
    if self.distinct and not self.separated:
      return "roUnq"
    if self.distinct and self.separated:
      return "roSep"