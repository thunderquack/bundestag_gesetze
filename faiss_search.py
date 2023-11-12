import os
import json
import faiss
import faiss_indexing
import argparse
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# Load pre-trained tokenizer and model
tokenizer = faiss_indexing.tokenizer
model = faiss_indexing.model

# Function to load FAISS indexes and corresponding data
def load_faiss_indexes(directory_path):
    index = {}
    datas = {}
    for faiss_name in os.listdir(directory_path):
        if faiss_name.endswith(".faiss"):
            jsonl_name = faiss_name[:-6]
            index_name = jsonl_name[:-6]
            index_file = os.path.join(directory_path, faiss_name)
            jsonl_file = os.path.join(directory_path, jsonl_name)

            index[index_name] = faiss.read_index(index_file)
            datas[index_name] = faiss_indexing.read_json_list(jsonl_file)
    
    return index, datas

# Load all FAISS indexes and data from the specified directory
faiss_indexes, index_data = load_faiss_indexes('.')

# Function to search across all indexes
def search_across_indexes(query_vector, k):
    combined_results = []
    for index_name, faiss_index in faiss_indexes.items():
        distances, indices = faiss_index.search(query_vector, k)
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # Ignore invalid indices
                result = index_data[index_name][idx]
                result['distance'] = float(distances[0][i])
                combined_results.append(result)
    combined_results.sort(key=lambda x: x['distance'])
    return combined_results[:k]

# Endpoint for search
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        query = request.args.get('query', '')
        count = int(request.args.get('count', '1'))
    elif request.method == 'POST':
        data = request.get_json()
        query = data.get('query', '')
        count = int(data.get('count', '1'))

    if query:
        # Embed the query
        vector = faiss_indexing.german_embedding(query)
        vector = vector.reshape(1, -1).astype('float32')

        # Search across all indexes
        results = search_across_indexes(vector, count)

        # Pretty-print the result
        pretty_json = json.dumps(results, indent=4)
        response = Response(pretty_json, content_type="application/json; charset=utf-8")
        return response
    else:
        error_message = json.dumps({"error": "Invalid query or index name"}, indent=4)
        return Response(error_message, status=400, content_type="application/json; charset=utf-8")

if __name__ == '__main__':
    # Set up the argument parser
    parser = argparse.ArgumentParser(description='Run Flask app for FAISS indexing.')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the Flask app on.')
    args = parser.parse_args()
    app.run(debug=False, port=args.port)

#curl -X POST http://localhost:5000/search \
#     -H "Content-Type: application/json" \
#     -d '{"query": "Unter Berücksichtigung der Vorschriften zum Eigentum und Nachbarrecht, wie ist die rechtliche Lage bezüglich der Eigentumsansprüche auf Überhang, insbesondere Früchte zu bewerten, die auf meinem Grundstück gewachsen sind, aber in den räumlichenn Bereich des Nachbargrundstücks hineinragen?", "count": "1"}'
