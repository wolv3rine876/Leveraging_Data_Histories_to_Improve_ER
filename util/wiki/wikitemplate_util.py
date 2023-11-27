
def replace_pagename(content: str, page_name: str) -> str:
  """ Replace all {{PAGENAME}} templates with the given page_name """

  return content.replace("{{PAGENAME}}", page_name)