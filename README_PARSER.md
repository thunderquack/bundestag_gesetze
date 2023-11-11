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
    "query": "Gehören mir die Früchte die aus meinem Grundstück in des Nachbarn Garten wachsen?",
    "fields": ["text_t", "paragraph^20", "title^10", "description^3"], "fuzziness": "AUTO"
}}}'
```


