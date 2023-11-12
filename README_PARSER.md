# Parser for Bundestag Gesetze files

## Make a index dump from the Gesetze files
```
python3 parser.py
```

The resulting files...
```
bundestag_gesetze_part1.jsonl
bundestag_gesetze_part2.jsonl
bundestag_gesetze_part3.jsonl
```
are in elasticsearch index format, a json list format with indexing directions.
The result is splitted into separate files because the bulk upload process accepts only files less than 100MB in size.
To test that the file creation was successful, we actually throw it against an opensearch index:

### Start a docker container with a single-node instance of opensearch (an elasticsearch branch)

We run a local opensearch instance with this single docker run command:
```
docker run --name opensearch -p 9200:9200 -d -e OPENSEARCH_JAVA_OPTS="-Xms2G -Xmx2G" -e discovery.type=single-node -e DISABLE_SECURITY_PLUGIN=true -v $(pwd)/opensearch_data:/usr/share/opensearch/data opensearchproject/opensearch:latest
```

### Ensure that the container is running properly
```
curl -X GET localhost:9200
```

## Feed the dump into the opensearch index

First we must unblock index creation, which is on by default:
```
curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "cluster.blocks.create_index": null
  }
}'
```

Then we must create an index before using it:
```
curl -X PUT localhost:9200/bundestag_gesetze
```

Finally we can bulk-upload the jsonlist files:
```
curl -XPOST "http://localhost:9200/bundestag_gesetze/_bulk?filter_path=took,errors" -H "Content-Type: application/x-ndjson" --data-binary @bundestag_gesetze_part1.jsonl
curl -XPOST "http://localhost:9200/bundestag_gesetze/_bulk?filter_path=took,errors" -H "Content-Type: application/x-ndjson" --data-binary @bundestag_gesetze_part2.jsonl
curl -XPOST "http://localhost:9200/bundestag_gesetze/_bulk?filter_path=took,errors" -H "Content-Type: application/x-ndjson" --data-binary @bundestag_gesetze_part3.jsonl
```

To check if the upload was successfull, read the index size:
```
curl -X GET "localhost:9200/_cat/indices/bundestag_gesetze?h=index,store.size"
```

### Make a search request
The final test if the search index is working is done doing an actual search request:
```
curl -X POST "http://localhost:9200/bundestag_gesetze/_search" -H 'Content-Type: application/json' -d'
{"size": 3, "query": {"multi_match": {
    "query": "Unter Berücksichtigung der Vorschriften zum Eigentum und Nachbarrecht, wie ist die rechtliche Lage bezüglich der Eigentumsansprüche auf Überhang, insbesondere Früchte zu bewerten, die auf meinem Grundstück gewachsen sind, aber in den räumlichenn Bereich des Nachbargrundstücks hineinragen?",
    "fields": ["text_t", "paragraph^20", "title^10", "description^3"], "fuzziness": "AUTO"
}}}'
```

### Python Search Client with FAISS Post-Ranking

We can now create a python client which reads the search index. An opensearch search can be done with a similarity matching,
but that matching has no function to measure the semantic similarty. That can be computed with a FAISS similarity ranking.
The following command will execute an example script which uses a client request to the opensearch index, creates a FAISS
index from the search results on-the-fly and sorts those search results by similarity to the search query.
```
python3 elastic_similar_search.py
```

This is not very fast because the re-indexing for a FAISS index is slow. A better way would be to push all of the documents
into a pre-compiled search index (see next chapter). It is much faster but it requires to keep all data of the index and the
source documents in the RAM completely.


## FAISS Vector Search Server

The FAISS index is a vector search index which can find the most similar document for a given document.
We can use the faiss library to generate a faiss index for each of the jsonl dump files. This method requires
to choose a proper embedding strategy, we are using here a german BERT LLM as sponsor for an appropriate embedding.

### Vector Indexing
At first an index must be computed. This is a long-running process which will take several hours even on a fast computer.
```
python3 faiss_indexing.py
```

The following faiss files will be generated here as result:
```
bundestag_gesetze_part1.jsonl.faiss
bundestag_gesetze_part2.jsonl.faiss
bundestag_gesetze_part3.jsonl.faiss
```

### FAISS Search Server
Next we can start up a web server which will read all the `.faiss` index files and provides a search API at a http port.
```
python3 faiss_search.py
```

Now you can search for similar documents using a curl command:
```
curl -X POST http://localhost:5000/search \
     -H "Content-Type: application/json" \
     -d '{"query": "Unter Berücksichtigung der Vorschriften zum Eigentum und Nachbarrecht, wie ist die rechtliche Lage bezüglich der Eigentumsansprüche auf Überhang, insbesondere Früchte zu bewerten, die auf meinem Grundstück gewachsen sind, aber in den räumlichenn Bereich des Nachbargrundstücks hineinragen?", "count": "3"}'
```
This will return three json objects, ordered by similarity; most similar first.

The result for this search is:

```
curl -X POST http://localhost:5000/search \
     -H "Content-Type: application/json" \
     -d '{"query": "Unter Berücksichtigung der Vorschriften zum Eigentum und Nachbarrecht, wie ist die rechtliche Lage bezüglich der Eigentumsansprüche auf Überhang, insbesondere Früchte zu bewerten, die auf meinem Grundstück gewachsen sind, aber in den räumlichenn Bereich des Nachbargrundstücks hineinragen?", "count": "3"}'
[
    {
        "url_s": "https://www.gesetze-im-internet.de/bgb/__911.html",
        "directory_name": "bgb",
        "title": "\u00a7 911 \u00dcberfall",
        "description": "B\u00fcrgerliches Gesetzbuch (BGB)\nBuch 3 - Sachenrecht\nAbschnitt 3 - Eigentum\nTitel 1 - Inhalt des Eigentums\n\u00a7 911 \u00dcberfall",
        "paragraph": "911",
        "text_t": "B\u00fcrgerliches Gesetzbuch (BGB)\nBuch 3 - Sachenrecht\nAbschnitt 3 - Eigentum\nTitel 1 - Inhalt des Eigentums\n\u00a7 911 \u00dcberfall\n\n\nFr\u00fcchte, die von einem Baume oder einem Strauche auf ein\nNachbargrundst\u00fcck hin\u00fcberfallen, gelten als Fr\u00fcchte dieses\nGrundst\u00fccks. Diese Vorschrift findet keine Anwendung, wenn das\nNachbargrundst\u00fcck dem \u00f6ffentlichen Gebrauch dient.\n\n\n",
        "level": 5,
        "distance": 36.07160949707031
    },
    {
        "url_s": "https://www.gesetze-im-internet.de/sachenrberg/__85.html",
        "directory_name": "sachenrberg",
        "title": "\u00a7 85 Unvermessene Fl\u00e4chen",
        "description": "Gesetz zur Sachenrechtsbereinigung im Beitrittsgebiet (SachenRBerG)\nKapitel 2 - Nutzung fremder Grundst\u00fccke durch den Bau oder den Erwerb von Geb\u00e4uden\nAbschnitt 4 - Verfahrensvorschriften\nUnterabschnitt 1 - Feststellung von Nutzungs- und Grundst\u00fccksgrenzen\n\u00a7 85 Unvermessene Fl\u00e4chen",
        "paragraph": "85",
        "text_t": "Gesetz zur Sachenrechtsbereinigung im Beitrittsgebiet (SachenRBerG)\nKapitel 2 - Nutzung fremder Grundst\u00fccke durch den Bau oder den Erwerb von Geb\u00e4uden\nAbschnitt 4 - Verfahrensvorschriften\nUnterabschnitt 1 - Feststellung von Nutzungs- und Grundst\u00fccksgrenzen\n\u00a7 85 Unvermessene Fl\u00e4chen\n\n\n(1) Sind die Grenzen der Fl\u00e4chen, auf die sich das Nutzungsrecht\nerstreckt, nicht im Liegenschaftskataster nachgewiesen (unvermessene\nFl\u00e4chen) oder wurde eine Bebauung nach den \u00a7\u00a7 4 bis 7 und 12 ohne\nBestellung eines Nutzungsrechts vorgenommen, erfolgt die Bestimmung\ndes Teils des Grundst\u00fccks, auf den sich die Nutzungsbefugnis des\nErbbauberechtigten erstreckt oder der vom Stammgrundst\u00fcck\nabgeschrieben werden soll, nach den Vorschriften des\nBodensonderungsgesetzes.\n\n(2) Einigungen der Beteiligten \u00fcber den Verlauf der\nNutzungsrechtsgrenzen und des Grundst\u00fccks sind zul\u00e4ssig.\n\n\n",
        "level": 5,
        "distance": 37.186466217041016
    },
    {
        "url_s": "https://www.gesetze-im-internet.de/sachenrberg/__21.html",
        "directory_name": "sachenrberg",
        "title": "\u00a7 21 Vermessene Fl\u00e4chen",
        "description": "Gesetz zur Sachenrechtsbereinigung im Beitrittsgebiet (SachenRBerG)\nKapitel 2 - Nutzung fremder Grundst\u00fccke durch den Bau oder den Erwerb von Geb\u00e4uden\nAbschnitt 1 - Allgemeine Bestimmungen\nUnterabschnitt 6 - Erfa\u00dfte Fl\u00e4chen\n\u00a7 21 Vermessene Fl\u00e4chen",
        "paragraph": "21",
        "text_t": "Gesetz zur Sachenrechtsbereinigung im Beitrittsgebiet (SachenRBerG)\nKapitel 2 - Nutzung fremder Grundst\u00fccke durch den Bau oder den Erwerb von Geb\u00e4uden\nAbschnitt 1 - Allgemeine Bestimmungen\nUnterabschnitt 6 - Erfa\u00dfte Fl\u00e4chen\n\u00a7 21 Vermessene Fl\u00e4chen\n\n\nDie Anspr\u00fcche auf Bestellung eines Erbbaurechts oder den Ankauf\nerstrecken sich auf das Grundst\u00fcck insgesamt, wenn dessen Grenzen im\nLiegenschaftskataster nachgewiesen sind (vermessenes Grundst\u00fcck) und\ndie Nutzungsbefugnis aus einem Nutzungsrecht oder einem Vertrag mit\nden Grenzen des Grundst\u00fccks \u00fcbereinstimmt. Im \u00fcbrigen sind die \u00a7\u00a7 22\nbis 27 anzuwenden.\n\n\n",
        "level": 5,
        "distance": 37.889591217041016
    }
]
```
