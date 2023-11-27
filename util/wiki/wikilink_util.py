import datetime
import locale
import re
from util.wiki.wikilink_result import WikilinkResult
from util.wiki.wiki_constants import WIKIPEDIA_HOSTNANE, WIKI_DEFAULT_NAMESPACE
from util.wiki.wikitemplate_util import replace_pagename
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote, urljoin
from typing import List

WIKILINK_PATTERN = "\[\[(?P<namespace>[\w]+?(?=:))?:?(?P<pagename>[^<>\[\]\|#]+)?[#\|]?(?P<anchor>(?<=#)[^\|\n\]]+)?\|?(?P<displaytext>(?<=\|)[^\n\]]+)?\]\]"
WIKIPEDIA_PAGENAME_PATTERN = "wiki\/(?P<namespace>[\w]+?(?=:))?:?(?P<pagename>[^\#?]*)#?(?P<anchor>(?<=#)[^\#?]*)?"

def parse_wiki_date(date: str) -> datetime:
  if locale.getlocale()[0] != "en_US":
    locale.setlocale(locale.LC_ALL, 'en_US.utf8')
  return datetime.datetime.strptime(date, "%b %d, %Y, %I:%M:%S %p")

def extract_wikilink(content: str, page_title: str = None, col_idx: int = None, namespaces=[WIKI_DEFAULT_NAMESPACE]) -> List[WikilinkResult]:
  """
    Extracts [[WIKILINK]] and href referring to a given wikipedia namespace.

    Parameters:
      content (str): The html containing wikilinks
      page_title (str): (Optional) If given, all {{PAGENAME}} occurances will be replaced with the given value.
      col_idx (int): (Optional) A <tr>'s cell index to look in.
      namespaces (list): (Optional) A list of accepted wikipedia namespaces. Default is just ["MAIN"].

    Returns:
      result (List[WikilinkResult]): The extracted WikilinkResults sorted by occurence or None, if no match was found.
  """

  soup = BeautifulSoup(content, "html.parser")
  if(col_idx is not None):
    cols = soup.find_all("td")
    if len(cols) <= col_idx:
      return None
    soup = cols[col_idx]
    content = str(soup)


  # Replace {{PAGENAME}} templates
  if page_title is not None:
    content = replace_pagename(content=content, page_name=page_title)

  wikilinks = []

  # Look for [[Wikilinks]]
  for match in re.finditer(WIKILINK_PATTERN, content):
    link = match.group(0)
    # check for [[ ]]
    if re.search("\[\[\s*\]\]", link) is None:
      namespace = match.group("namespace")
      pagename =match.group("pagename")
      anchor = match.group("anchor")
      display_text = match.group("displaytext")
      wikilink = WikilinkResult(match=link, namespace=namespace, pagename=pagename, anchor=anchor, display_text=display_text)
      if wikilink.namespace in namespaces:
        wikilinks.append((match.start(), wikilink))

  # look for href links
  for link in soup.find_all("a"):
    href = link.get("href")

    if href is None:
      continue
    
    href_idx = content.find(href)

    href = unquote(link.get("href"))
    
    # convert rel urls to abs urls
    if href.startswith("/"):
      href = urljoin("http://" + WIKIPEDIA_HOSTNANE, href)
    
    try:
      uri = urlparse(href)
    
      if uri.hostname is not None and uri.hostname.lower() == WIKIPEDIA_HOSTNANE:
        
        link_text = link.get_text()
        if link_text:
          link_text = link_text.strip("\n ")

        href_match = re.search(WIKIPEDIA_PAGENAME_PATTERN, uri.path)
        if href_match:
          namespace = href_match.group("namespace")
          pagename = href_match.group("pagename")
          anchor = href_match.group("anchor")
          display_text = link_text if link_text else link.get("title")
          wikilink = WikilinkResult(match=href, pagename=pagename, display_text=display_text, anchor=uri.fragment, namespace=namespace)
          if wikilink.namespace in namespaces:
            wikilinks.append((href_idx, wikilink))
    
    except ValueError:
      continue
    

  wikilinks = [t[1] for t in sorted(wikilinks, key=lambda t: t[0])]

  return wikilinks if len(wikilinks) > 0 else None

def replace_wikilinks(content: str) -> str:
  """
    Replaces all [[WIKILINK]]s with their respective title or pagename.

    Parameters:
      content (str): The text containing wikilinks

    Returns:
      text (str): The given text without wikilinks.
  """
  content = re.sub(WIKILINK_PATTERN, lambda m: m.group("displaytext") if m.group("displaytext") is not None else m.group("pagename"), content)
  return content

def build_wikipedia_url(page_name: str, revisionId: int) -> str:
  baseUrl = urljoin('https://' + WIKIPEDIA_HOSTNANE, f'w/index.php?title={page_name.replace(" ", "_")}')
  if revisionId:
    baseUrl += f'&oldid={str(revisionId)}'
  return baseUrl