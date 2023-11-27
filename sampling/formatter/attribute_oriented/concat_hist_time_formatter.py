import re
from sampling.formatter.base_prompt_formatter import BasePromptFormatter
from util.html.html_util import get_cols
from util.rev.revision_util import get_rev_at_time
from util.wiki.wiki_table_util import get_tr
from util.wiki.wikilink_util import parse_wiki_date

class ConcatHistTimeFormatter(BasePromptFormatter):
  """
    aoTime_dmy:  Y=True, M=True, D=True, TUNION=False
    aoTime_my:   Y=True, M=True, D=False, TUNION=False
    aoTUnion_my: Y=True, M=True, D=False, TUNION=True
  """
    
  def __init__(self, Y: bool, M: bool, D: bool, TUNION: bool = False):
    super().__init__()

    fmt = []
    if D:
      fmt.append("%d")
    if M:
      fmt.append("%m")
    if Y:
      fmt.append("%Y")

    self.fmt = "/".join(fmt)
    self.time_union = TUNION

  def format_entry(self, revs1: list, revs2: list) -> str:

    values = dict()
    value_dates = dict()
    schemas = dict()
    schema_dates = dict()

    dates = list(map(lambda r: parse_wiki_date(r["revisionDate"]), revs1))
    if self.time_union:
      dates = dates + list(map(lambda r: parse_wiki_date(r["revisionDate"]), revs2))
    dates.sort(reverse=True)

    for date in dates:

      revision = get_rev_at_time(revs1, date)

      cols = vals = col_ids = None

      # happens when time_union is true and a date is before the creation of an entity
      if not revision:
        col_ids = [cell["columnId"] for rev in revs1 for cell in rev["cells"]]
        # add a none value
        cols = [self.NONE for _ in col_ids]
        vals = [self.NONE for _ in col_ids]

      else:
        cols = get_cols(revision["schema"])
        vals = get_cols(get_tr(revision))
        col_ids = [cell["columnId"] for cell in revision["cells"]]

      for col, (val, col_id) in zip(cols, zip(vals, col_ids)):

        for c_id, cols in schemas.items():
          if col in cols and c_id != col_id:
            col_id = c_id

        value_set = values.setdefault(col_id, [])
        value_date_set = value_dates.setdefault(col_id, [])
        schema_set = schemas.setdefault(col_id, [])
        schema_date_set = schema_dates.setdefault(col_id, [])

        if val not in value_set or self.time_union:
          value_set.append(val.strip())
          value_date_set.append(date)

        if col not in schema_set or self.time_union:
          schema_set.append(col.strip())
          schema_date_set.append(date)
    
    return " ".join([f'{" ".join([f"{self.TIME} {t.strftime(self.fmt)} {self.COL} {c}" for t, c in zip(schema_dates[col_id], schemas[col_id])])} {" ".join([f"{self.TIME} {t.strftime(self.fmt)} {self.VAL} {v}" for t, v in zip(value_dates[col_id], vals)])}' for col_id, vals in values.items()])
  
  def get_config_name(self):
    fmt = re.sub('[^0-9a-zA-Z]+', '', self.fmt.lower())
    name = ""
    if not self.time_union:
      name = "aoTime"
    else:
      name = "aoTUnion"

    return f"{name}_{fmt}"
