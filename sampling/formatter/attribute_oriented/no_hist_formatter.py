from datetime import timedelta
from sampling.formatter.base_prompt_formatter import BasePromptFormatter
from util.html.html_util import get_cols
from util.rev.revision_util import nearest_rev
from util.wiki.wiki_table_util import get_tr
from util.wiki.wikilink_util import parse_wiki_date

class NoHistPromptFormatter(BasePromptFormatter):
  """
    nhNewest: NEWEST=True, ALIGN=False
    nhOldest: NEWEST=False, ALIGN=False
    nhNearest: NEWEST=True, ALIGN=True
  """

  MAX_TIME_DIFF = timedelta(days=182)

  def __init__(self, NEWEST: bool = True, ALIGN: bool = False,):
    super().__init__()

    self.align = ALIGN
    self.newest = NEWEST or ALIGN # align only implemented for newest
    self.idx = -1 if NEWEST else 0
  
  def format_entry(self, revs1: list, revs2: list) -> str:
        
    rev = None

    if self.align:
      date1 = parse_wiki_date(revs1[self.idx]["revisionDate"])
      date2 = parse_wiki_date(revs2[self.idx]["revisionDate"])
      rev = nearest_rev(revs1, min(date1, date2))
   
    else:
       revs1[self.idx]

    cols = get_cols(rev["schema"])
    vals = get_cols(get_tr(rev))
    
    d = dict(zip(cols, vals))

    return self.dict_to_entry(d)
  
  def get_config_name(self):
    if self.newest and not self.align:
      return "nhNewest"
    if not self.newest and not self.align:
      return "nhOldest"
    if self.newest and self.align:
      return "nhNearest"
