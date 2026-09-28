import json
import re

def normalize_for_match(text: str) -> str:
    if not text:
        return ""
    val = text.lower()
    val = re.sub(r"-\s*\n\s*", "", val)
    val = val.replace("“", "").replace("”", "").replace("‘", "").replace("’", "").replace("'", "").replace("\"", "")
    val = val.replace("`", "")
    val = re.sub(r"[^a-z0-9 ]+", " ", val)
    val = re.sub(r"\s+", " ", val)
    return val.strip()

chunks = json.load(open("chunks.json", "r", encoding="utf-8"))
chunk_text = chunks[1067]["chunk_text"]

evidence = "Lieutenant Governor's Relief Fund, if the fund meets all the following conditions: (A) it is the only fund of its kind established in the State or the Union territory; (B) it is under the overall control of the Chief Secretary or the Department of Finance of the respective State or the Union territory; (C) it is administered in a manner specified by the State Government or the Lieutenant Governor;"

norm_ev = normalize_for_match(evidence)
norm_chunk = normalize_for_match(chunk_text)

print("Evidence in Chunk:", norm_ev in norm_chunk)
if norm_ev not in norm_chunk:
    print("\n--- NORM EV ---")
    print(norm_ev)
    print("\n--- NORM CHUNK ---")
    print(norm_chunk)
