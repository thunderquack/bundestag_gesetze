import time
import torch
import requests
import faiss
import numpy as np
from transformers import BertModel, BertTokenizer

# Load pre-trained model tokenizer and model
tokenizer = BertTokenizer.from_pretrained("bert-base-german-dbmdz-uncased")
model = BertModel.from_pretrained("bert-base-german-dbmdz-uncased")
dimension = 768  # Dimensionality of BERT embeddings
faiss_index = faiss.IndexFlatL2(dimension)

def german_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad(): outputs = model(**inputs) # hidden states
    # Use the average of the last hidden states as the embedding vector
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    return embeddings

def information_retrieval(querystring, count):
    query = {
        "size": count,
        "query": {
            "multi_match": {
                "query": querystring,
                "fields": ["text_t", "title^10", "description^3"],
                "fuzziness": "AUTO"
            }
        }
    }
    response = requests.post("http://localhost:9200/bundestag_gesetze/_search",
                             headers={'Content-Type': 'application/json'},
                             json=query)
    search_results = response.json()['hits']['hits']
    return search_results

def similarity(search_results, querystring, k):

    # we first translate the search results into vectors
    vectors = []
    for result in search_results:
        text = result['_source']['text_t']
        vector = german_embedding(text)
        vectors.append(vector)

    # create a faiss index with the computed embeddings
    vectors = np.array(vectors).astype('float32')
    faiss_index.reset()
    faiss_index.add(vectors)
    query_vector = german_embedding(querystring)
    distances, indices = faiss_index.search(np.array([query_vector]), k)

    # Sort indices based on distances
    sorted_indices = [index for _, index in sorted(zip(distances[0], indices[0]))]

    return sorted_indices


querystring = "Unter Berücksichtigung der Vorschriften zum Eigentum und Nachbarrecht, wie ist die rechtliche Lage bezüglich der Eigentumsansprüche auf Überhang, insbesondere Früchte zu bewerten, die auf meinem Grundstück gewachsen sind, aber in den räumlichen Bereich des Nachbargrundstücks hineinragen?"
search_results = information_retrieval(querystring, 10)
sorted_indices = similarity(search_results, querystring, 3)
for i in sorted_indices:
    print(search_results[i]['_source']['text_t'])
