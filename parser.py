import os
import json
import re

def get_headline_level(line):
    """ Return the headline level based on the number of '#' characters """
    return line.count('#')

def parse(file_path, directory_name):
    chunks = []  # List to hold all chunks as dictionaries
    current_hierarchy = []  # To keep track of the hierarchy leading to the current headline
    current_paragraph = ''  # Variable to hold the current paragraph number

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.readlines()
        for line in content:
            if line.startswith('#'):
                level = get_headline_level(line.strip())
                title = line.strip().lstrip('#').strip()

                # Extract paragraph number (if present) after "§" symbol
                paragraph_match = re.search(r'\u00a7\s*([\w\d]+)', title)
                if paragraph_match:
                    current_paragraph = paragraph_match.group(1)
                    # Remove the paragraph token from the title
                    title = title.replace(paragraph_match.group(0), '').strip()

                # Adjust the current_hierarchy to match the new level
                if len(current_hierarchy) >= level:
                    current_hierarchy = current_hierarchy[:level-1]
                current_hierarchy.append(title)
                
                # Define the chunk with its description and paragraph number
                description = current_hierarchy[:-1]  # The description is the hierarchy excluding the current title
                chunk = {
                    'directory_name': directory_name,
                    'title': title,
                    'description': description,
                    'paragraph': current_paragraph,
                    'text': '',
                    'level': level
                }
                chunks.append(chunk)
            else:
                if chunks:  # Append text to the last chunk
                    chunks[-1]['text'] += line

    return chunks


def find_and_parse_index_md(start_path):
    all_chunks = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file == "index.md":
                full_path = os.path.join(root, file)
                directory_name = os.path.basename(root)  # Extract the directory name
                chunks = parse(full_path, directory_name)
                all_chunks.extend(chunks)

    # Convert the list of chunks to a JSON array
    json_array = json.dumps(all_chunks, indent=4)

    # Write the JSON array to the filesystem
    with open('parsed_content.json', 'w') as json_file:
        json_file.write(json_array)

find_and_parse_index_md('.')

