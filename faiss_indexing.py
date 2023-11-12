import os
import time
import json
import faiss
import torch
import numpy as np
from transformers import BertModel, BertTokenizer

# Load pre-trained model tokenizer and model
tokenizer = BertTokenizer.from_pretrained("bert-base-german-dbmdz-uncased")
model = BertModel.from_pretrained("bert-base-german-dbmdz-uncased")
dimension = 768  # Dimensionality of BERT embeddings

def german_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad(): outputs = model(**inputs) # hidden states
    # Use the average of the last hidden states as the embedding vector
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    return embeddings

def read_json_list(jsonl_file):
    json_list = []

    with open(jsonl_file, 'r', encoding='utf-8') as file:
        for line in file:
            record = json.loads(line)
            text = record.get('text_t', '')  # Assuming the text is in 'text_t' key
            if text: json_list.append(record)
    return json_list

def process_file(jsonl_file):
    faiss_index_file = jsonl_file + '.faiss'

    if os.path.exists(faiss_index_file):
        print(f"FAISS index for {jsonl_file} already exists. Skipping.")
        return
    
    json_list = read_json_list(jsonl_file)
    faiss_index = faiss.IndexFlatL2(dimension)  # Create a FAISS index
    vectors = []

    start_time = time.time()
    for i, record in enumerate(json_list):
        text = record.get('text_t', '')  # Assuming the text is in 'text_t' key
        vector = german_embedding(text)
        vectors.append(vector)

        # Log progress every 100 lines
        if (i+1) % 100 == 0:
            elapsed = time.time() - start_time
            estimated_total = elapsed / (i+1) * len(json_list)
            remaining = estimated_total - elapsed
            print(f"Processed {i+1}/{len(json_list)} records. Estimated time remaining: {remaining/60:.2f} minutes.")

    # Convert list of vectors to a FAISS compatible format
    vectors = np.array(vectors).astype('float32')
    faiss_index.add(vectors)  # Add vectors to the index

    # Save the index to a file
    faiss.write_index(faiss_index, jsonl_file + '.faiss')

# Process all .jsonl files
if __name__ == "__main__":
    directory = '.'
    for file in os.listdir(directory):
        if file.endswith('.jsonl'):
            print(f"Processing file: {file}")
            process_file(os.path.join(directory, file))
