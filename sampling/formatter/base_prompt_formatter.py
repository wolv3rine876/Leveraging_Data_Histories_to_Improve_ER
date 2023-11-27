class BasePromptFormatter:
    
  def __init__(self):
    self.COL = "COL"
    self.VAL = "VAL"
    self.HIST = "HIST"
    self.TIME = "TIME"
    self.NONE = "NONE"
    self.PERIOD = "PERIOD"

  def format_entry(self, revs1: list, revs2: list) -> str:
    """
      Formats the given revs1 to a ditto compatible entry.
    """
    raise NotImplementedError()
  
  def get_config_name(self):
    """
      Retruns a str that represents the Formatter's configuration.
    """
    raise NotImplementedError()
  
  def dict_to_entry(self, d: dict) -> str:
    return ' '.join([ f"{self.COL} {k} {self.VAL} {v}" for k, v in d.items()])