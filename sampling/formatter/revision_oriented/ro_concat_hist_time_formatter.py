import re
from sampling.formatter.base_prompt_formatter import BasePromptFormatter
from util.html.html_util import get_cols
from util.rev.revision_util import nearest_rev
from util.wiki.wiki_table_util import get_tr
from util.wiki.wikilink_util import parse_wiki_date

class ROConcatHistTimeFormatter(BasePromptFormatter):
  """
    roTime_dmy: Y=True, M=True, D=True, TUNION=False
    roTime_my:  Y=True, M=True, D=False, TUNION=False
    roTUnion_my:  Y=True, M=True, D=False, TUNION=True
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

    dates = list(map(lambda r: parse_wiki_date(r["revisionDate"]), revs1))
    if self.time_union:
      dates = dates + list(map(lambda r: parse_wiki_date(r["revisionDate"]), revs2))
    dates.sort(reverse=True)

    fmtd_revisions = []

    for date in dates:

      revision = nearest_rev(revs1, date)

      cols = get_cols(revision["schema"])
      vals = get_cols(get_tr(revision))

      row = {k: v for k, v in zip(cols, vals)}
      fmtd_revision = f"{self.TIME} {date.strftime(self.fmt)} {self.dict_to_entry(row)}"
      fmtd_revisions.append(fmtd_revision)

    return " ".join(fmtd_revisions)
  
  def get_config_name(self):
    fmt = re.sub('[^0-9a-zA-Z]+', '', self.fmt.lower())
    name = ""
    if not self.time_union:
      name = "roTime"
    else:
      name = "roTUnion_my"
    return f"{name}_fmt"