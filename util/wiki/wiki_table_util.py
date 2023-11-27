def get_tr(revision: dict):
  """
    Concats the cells of the given revision to one <tr>
  """
  cells = revision["cells"]
  return f"<tr>{''.join([cell['content'] for cell in cells])}</tr>"