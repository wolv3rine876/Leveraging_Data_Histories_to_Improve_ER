import json
import logging
import click


logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(levelname)s [%(process)d] - %(message)s")

@click.command()
@click.argument('idx', type=str) 
@click.argument('src', type=str)
@click.argument('dest', type=str)
def reformat(idx, src, dest):
  """Reformats per-revision classification for aggregation.
     idx should be the path to the .index file that is created when generating the prompts.
  """

  with open(idx, "rb") as idx_file:
    with open(src, "rb") as src_file:
      with open(dest, "w", encoding="utf-8") as dest_file:

        idx = json.loads(idx_file.readline())

        for entity_pair in idx:

          entity_predictions = []

          for pair in entity_pair["revisions"]:
            classification = json.loads(src_file.readline())
            
            date1 = pair["left"]["revisionDate"]
            date2 = pair["right"]["revisionDate"]
            match = entity_pair["match"]

            prediction = True if classification["match"] == 1 else False
            prediction_confidence = classification["match_confidence"]

            entity_predictions.append({
              "date1": date1,
              "date2": date2,
              "match": match,
              "prediction": prediction,
              "predictionConfidence": prediction_confidence
            })

          dest_file.write(json.dumps(entity_predictions, ensure_ascii=False) + "\n")