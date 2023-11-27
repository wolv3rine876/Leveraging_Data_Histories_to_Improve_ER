import click
from click import echo
import json
from util.html.html_util import get_cols
from util.wiki.wiki_table_util import get_tr
from util.wiki.wikilink_result import WikilinkResult
from util.wiki.wikilink_util import build_wikipedia_url


@click.command()
@click.argument('label_src', type=str)
@click.argument('prediction_src', type=str)
@click.argument('dest', type=str)
def errors(label_src, prediction_src, dest):
  """Command-line utility for error analysis."""

  with open(label_src, "rb") as label_file:
    # Skip training / validation data
    [label_file.readline() for _ in range(160000)]

    with open(prediction_src, "rb") as prediction_file:

      for prediction_line in prediction_file:
        
        label_doc = json.loads(label_file.readline())
        prediction_doc = json.loads(prediction_line)

        label = label_doc["match"]
        prediction = True if prediction_doc["match"] == 1 else False

        # TP or TN
        if label == prediction:
          continue

        target_link1 = WikilinkResult.from_dict(label_doc["row1"]["link"])
        target_link2 = WikilinkResult.from_dict(label_doc["row2"]["link"])
        
        print("=========================================================================")
        print(f"Label: {label}")
        print(f"Pagename: {label_doc['row1']['pageTitle']}        ({build_wikipedia_url(label_doc['row1']['pageTitle'], label_doc['row1']['revisions'][-1]['revisionID'])}) -> ({target_link1.identifier})")
        print(" | ".join(get_cols(label_doc["row1"]["revisions"][-1]['schema'])))
        print(" | ".join(get_cols(get_tr(label_doc["row1"]["revisions"][-1]))))
        print("---------")
        print(f"Pagename: {label_doc['row2']['pageTitle']}        ({build_wikipedia_url(label_doc['row2']['pageTitle'], label_doc['row2']['revisions'][-1]['revisionID'])}) -> ({target_link2.identifier})")
        print(" | ".join(get_cols(label_doc["row2"]["revisions"][-1]['schema'])))
        print(" | ".join(get_cols(get_tr(label_doc["row2"]["revisions"][-1]))))
        print("=========================================================================")

        valid_prompt = False
        while not valid_prompt:
          
          try:
            prompt = input(">").lower()

            try:
              prompt = int(prompt)
              if prompt != 0 and prompt != 1:
                raise ValueError()
              
              valid_prompt = True
              truth = True if prompt == 1 else False

              output = {
                "label": label,
                "prediction": prediction,
                "truth": truth
              }

              with open(dest, "a", encoding="utf-8") as file:
                file.write(json.dumps(output, ensure_ascii=False) + "\n")

            except:
              echo("Unknown number format. Try again...")
          
          except KeyboardInterrupt:
            return
