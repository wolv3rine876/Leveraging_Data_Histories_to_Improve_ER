from sampling.formatter.base_prompt_formatter import BasePromptFormatter
from util.html.html_util import get_cols
from util.wiki.wiki_table_util import get_tr

class ConcatHistFormater(BasePromptFormatter):
  """
    ao: DESC=True
  """
    
  def __init__(self, DESC: bool = True):
    super().__init__()

    self.desc = DESC

  def format_entry(self, revs1: list, revs2: list) -> str:

    if self.desc:
      revs1.reverse()

    values = dict()
    schemas = dict()

    for revision in revs1:

      cols = get_cols(revision["schema"])
      vals = get_cols(get_tr(revision))
      col_ids = [cell["columnId"] for cell in revision["cells"]]

      for col, (val, col_id) in zip(cols, zip(vals, col_ids)):

        for c_id, cols in schemas.items():
          if col in cols and c_id != col_id:
            col_id = c_id

        l = values.setdefault(col_id, [])

        l.append(val.strip())
        if col_id not in schemas:
          schemas[col_id] = col
    
    return self.dict_to_entry({schemas[col_id]: " ".join(vals) for col_id, vals in values.items()})
  
  def get_config_name(self):
    if self.desc:
      return "ao"
    return "concat_hist_asc"
