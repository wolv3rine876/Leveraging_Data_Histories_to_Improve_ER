from util.wiki.wiki_constants import WIKI_DEFAULT_NAMESPACE

class WikilinkResult:
  """Class representing an identified wikilink."""

  def from_dict(d: dict):
    return WikilinkResult(
      namespace=d["namespace"],
      pagename=d["pageName"],
      anchor=d["anchor"],
      display_text=d["text"],
      match=d["match"]
    )

  def __init__(self, pagename, anchor, display_text, match=None, namespace=None) -> None:
    self.namespace = namespace if namespace else WIKI_DEFAULT_NAMESPACE
    self.pagename = pagename
    self.anchor = anchor
    self.display_text = display_text
    self.match = match

  @property
  def has_anchor(self):
    return self.anchor is not None and self.anchor != ""

  @property
  def has_display_text(self):
    return self.display_text is not None and self.display_text != ""
  
  @property
  def identifier(self):
    return f"{self.pagename}{f'#{self.anchor}' if self.anchor else ''}".lower()

  def __str__(self):
    return "{namespace}:{pagename}{anchor}".format(
      namespace=self.namespace,
      pagename=self.pagename,
      anchor=f'#{self.anchor}' if self.has_anchor else "",
    )
  
  def __eq__(self, __value: object) -> bool:
    if not isinstance(__value, WikilinkResult):
      return False
    
    if self.pagename and __value.pagename and self.pagename.lower() != __value.pagename.lower():
      return False
    
    if self.has_anchor and __value.has_anchor and self.anchor.lower() != __value.anchor.lower():
      return False
    
    return True