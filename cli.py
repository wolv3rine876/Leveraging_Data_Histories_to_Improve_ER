import click

# Commands are registered by the different modules

from labeling.labeling import label

from sampling.sampling import sample
from sampling.ditto_prompt import gen_prompts

from filtering.filtering import filter

from aggr.reformatter import reformat
from aggr.aggr import aggr

from eval.eval import eval

@click.group()
def entry_point():
  pass

entry_point.add_command(filter)
entry_point.add_command(sample)
entry_point.add_command(label)
entry_point.add_command(gen_prompts)
entry_point.add_command(reformat)
entry_point.add_command(aggr)
entry_point.add_command(eval)

if __name__ == "__main__":
  entry_point()