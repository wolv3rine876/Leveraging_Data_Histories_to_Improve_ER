import re
from bs4 import BeautifulSoup

from util.wiki.wikitemplate_util import replace_pagename
from util.wiki.wikilink_util import replace_wikilinks


def get_text(html: str, page_name: str, separator: str="||") -> str:
  """
  Extracts the text from the given html

  Parameters:
    html (str): The html
    page_name (str): (Optional) If given, all {{PAGENAME}} occurances will be replaced with the given value.
    separator (str): (Optional) The separator to use (||).

  Returns:
    text (str): the extracted text
  """
 
  soup = _get_soup(html, page_name)

  text = soup.get_text(separator=separator)
  if page_name is not None:
    text = replace_pagename(content=text, page_name=page_name)

  return _clean_text(text)

def contains_list(html:str, min_li=0) -> bool:
  """
  Checks if the given html contains an <ul></ul> or <ol></ol> and a given amount of <li></li>

  Parameters:
    html (str): The html to check
    min_li (int): (Optional) The minimum number of <li> elements that should be contained in a <ul>.
  
  Return:
    (bool): True if a matching list was found.
  
  """

  soup = BeautifulSoup(html, "html.parser")
  for list in soup.find_all("ul"):
    
    if len(list.find_all("li")) >= min_li:
      return True
  
  for list in soup.find_all("ol"):
    
    if len(list.find_all("li")) >= min_li:
      return True

  return False

def get_cols(tr) -> list:
  """
  Returns all cells in the <tr> as list of strings.

  Parameters:
    tr (str) or (list): A table row or list of cells
  
  Return:
    (List): A list if a string for each <th> or <td>.
  
  """
  if type(tr) is str:
    tr  = [tr]

  dishes = [_get_soup(html, None) for html in tr]

  return [_clean_text(cell.get_text()) for soup in dishes for cell in soup.find_all(["th", "td"])]

def transform_to_matrix(html: str) -> list:
  """Transform the given html table to a 2D list."""

  soup = _get_soup(html, None)
  rows = soup.find_all("tr")
  return [[_clean_text(cell.get_text()) for cell in tr.find_all(["th", "td"])] for tr in rows]

def _get_soup(html: str, page_name: str) -> str:
 
  html = replace_wikilinks(html)

  if page_name:
    html = replace_pagename(content=html, page_name=page_name)

  soup = BeautifulSoup(html, "html.parser")

  # Add the title attribute to each link, if it adds additional information.
  for a in soup.find_all("a"):
    title = a["title"] if a.has_attr("title") else ""
    text = a.get_text()
    if text.lower() not in title.lower() and title.lower() not in text.lower():
      a.string = f"{text.strip()} ({title.strip()})"

  return soup

def _clean_text(text: str) -> str:
  return re.sub("\s+", " ", text).strip().replace("\n", "").replace("\t", "").replace("\r", "")