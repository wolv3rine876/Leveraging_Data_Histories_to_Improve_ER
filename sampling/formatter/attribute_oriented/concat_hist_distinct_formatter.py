from sampling.formatter.base_prompt_formatter import BasePromptFormatter
from util.html.html_util import get_cols
from util.wiki.wiki_table_util import get_tr

class ConcatHistDistinctFormater(BasePromptFormatter):
  """
    aoUnq: SEP=False
    aoSep: SEP=True
  """

  def __init__(self, SEP: bool = False):
    super().__init__()

    self.separate = SEP
    self.separator = f" {self.HIST} " if SEP else " "
    
  def format_entry(self, revs1: list, revs2: list) -> str:

    values = dict()
    schemas = dict()

    for revision in reversed(revs1):

      cols = get_cols(revision["schema"])
      vals = get_cols(get_tr(revision))
      col_ids = [cell["columnId"] for cell in revision["cells"]]

      for col, (val, col_id) in zip(cols, zip(vals, col_ids)):

        for c_id, cols in schemas.items():
          if col in cols:
            col_id = c_id

        value_set = values.setdefault(col_id, [])
        schema_set = schemas.setdefault(col_id, [])

        if val not in value_set:
          value_set.append(val.strip())
        if col not in schema_set:
          schema_set.append(col.strip())
    
    return self.dict_to_entry({self.separator.join(schemas[col_id]): self.separator.join(vals) for col_id, vals in values.items()})
  
  def get_config_name(self):
    if not self.separate:
      return "aoUnq"
    else:
      return "aoSep"