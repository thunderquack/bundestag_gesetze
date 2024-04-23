import os
import time
import json
import faiss
import torch
import numpy as np
from transformers import BertModel, BertTokenizer
from concurrent.futures import ThreadPoolExecutor

# Load pre-trained model tokenizer and model
model_name = "dbmdz/bert-base-german-uncased"
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertModel.from_pretrained(model_name)
dimension = 768  # Dimensionality of BERT embeddings

# Function to embed a text using BERT
# An embedding is a vector of size 768
def embedding(text):
    # make downcase of given text; the model is trained on lowercased text
    text = text.lower()
    text = text.replace('\n', ' ')
    replaced_text = text.replace('  ', ' ')
    while (replaced_text!=text):
        text = replaced_text
        replaced_text = text.replace('  ', ' ')
    # Tokenize the text
    inputs = tokenizer(text, return_tensors="pt", truncation='longest_first', max_length=512)
    # Extract the embeddings
    with torch.no_grad(): outputs = model(**inputs) # hidden states
    # Use the average of the last hidden states as the embedding vector
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    #embeddings_with_index = np.insert(embeddings, 0, index)
    return embeddings

# Read jsonl file and return a list of strings.
# The order of the objects in the list is important
# because the line number is used as the index.
def read_text_list(jsonl_file):
    lines = []

    with open(jsonl_file, 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith('{"index":'): continue # if line starts with {"index":{}} skip it
            if 'text_t' not in line: continue # if line does not contain 'text_t', skip it
            lines.append(line)

    return lines

# Read text list and return a list of json objects.
# Keeps the order of the lines.
def parse_json_lines(lines, batch_size=100):
    def parse_batch(batch):
        json_records = []
        for line in batch:
            try:
                record = json.loads(line)
                # the json object should have a 'text_t' field that contains the text to be indexed
                json_records.append(record)
            except json.JSONDecodeError:
                pass  # Optionally log parse errors or invalid lines
        return json_records

    print(f"Parsing {len(lines)} lines in batches of {batch_size}")
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(parse_batch, lines[i:i + batch_size]) for i in range(0, len(lines), batch_size)]
        # this concurrency is needed for very large files; it preserves the order of the lines (important!)
        return [record for future in futures for record in future.result()]

def process_file(jsonl_file):
    faiss_index_file = jsonl_file + '.faiss'

    if os.path.exists(faiss_index_file):
        print(f"FAISS index for {jsonl_file} already exists. Skipping.")
        return
    
    # read jsonl file and parse it into a list of json objects
    text_list = read_text_list(jsonl_file)
    print(f"Read {len(text_list)} lines from {jsonl_file}")
    json_records = parse_json_lines(text_list)
    print(f"Parsed {len(json_records)} json objects from {jsonl_file}")

    # concurrent embedding computation
    start_time = time.time()
    print(f"Starting to compute embeddings for {len(json_records)} records")
    with ThreadPoolExecutor() as executor:
        futures = []
        for i in range(0, len(json_records)):
            record = json_records[i]
            record_text = record['text_t']
            future = executor.submit(embedding, record_text)
            futures.append(future)

            # Log progress every 100 lines
            if (i+1) % 10000 == 0:
                elapsed = time.time() - start_time
                estimated_total = elapsed / (i+1) * len(json_records)
                remaining = estimated_total - elapsed
                print(f"Submitted {i+1}/{len(json_records)} records to concurrent executor. Estimated time remaining: {remaining/60:.2f} minutes.")

        # wait for all futures to finish
        vectors = []
        start_time = time.time()
        print(f"Waiting for {len(futures)} futures to finish")
        for i in range(0, len(futures)):
            future = futures[i]
            vector = future.result()
            vectors.append(vector)

            # Log progress every 100 lines
            if (i+1) % 100 == 0:
                elapsed = time.time() - start_time
                estimated_total = elapsed / (i+1) * len(json_records)
                remaining = estimated_total - elapsed
                print(f"Computed {i+1}/{len(json_records)} embeddings. Estimated time remaining: {remaining/60:.2f} minutes.")

    print(f"Finished computing embeddings for {len(json_records)} records, computing FAISS index")

    # Convert list of vectors to a FAISS compatible format
    vectors = np.array(vectors).astype('float32')
    # Create a FAISS index
    faiss_index = faiss.IndexFlatL2(dimension)
    faiss_index.add(vectors)  # Add vectors to the index

    # Save the index to a file
    faiss.write_index(faiss_index, jsonl_file + '.faiss')
    print(f"Finished and saved FAISS index to {jsonl_file + '.faiss'}")

# Process all .jsonl files
if __name__ == "__main__":
    directory = '.'
    for file in os.listdir(directory):
        if file.endswith('.jsonl'):
            print(f"Processing file: {file}")
            process_file(os.path.join(directory, file))
