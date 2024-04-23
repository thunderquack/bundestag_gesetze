import os
import json
import re

def get_headline_level(line):
    """ Return the headline level based on the number of '#' characters """
    return line.count('#')

def parse_metadata(lines):
    """Parses the metadata at the beginning of the markdown file."""
    metadata = {}
    metadata_lines = []
    inside_metadata = False
    for line in lines:
        if line.strip() == '---':
            if inside_metadata:
                # End of metadata section
                break
            else:
                # Start of metadata section
                inside_metadata = True
        elif inside_metadata:
            metadata_lines.append(line)
    for line in metadata_lines:
        key_value_match = re.match(r"(\w+):\s*(.*)", line)
        if key_value_match:
            key, value = key_value_match.groups()
            metadata[key.lower()] = value.strip()
    return metadata

def parse(file_path, directory_name):
    chunks = []  # List to hold all chunks as dictionaries
    current_hierarchy = []  # To keep track of the hierarchy leading to the current headline
    current_paragraph = ''  # Variable to hold the current paragraph number

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.readlines()

        # Parse metadata if it exists
        metadata = {}
        if content and content[0].strip() == '---':
            metadata = parse_metadata(content)
            # Skip past the metadata section to the rest of the content
            content = content[content.index('---', 1) + 1:] if '---' in content else content
        
        # get the origslug metadata field
        origslug = metadata.get('origslug', '')

        for line in content:
            if line.startswith('#'):
                level = get_headline_level(line.strip())
                title = line.strip().lstrip('#').strip()

                # Extract paragraph number (if present) after "§" symbol
                paragraph_match = re.search(r'\u00a7\s*([\w\d]+)', title)
                if paragraph_match:
                    current_paragraph = paragraph_match.group(1)

                # Adjust the current_hierarchy to match the new level
                if len(current_hierarchy) >= level:
                    current_hierarchy = current_hierarchy[:level-1]
                current_hierarchy.append(title)
                
                # Define the chunk with its description and paragraph number
                description = current_hierarchy[:-1]  # The description is the hierarchy excluding the current title
                descriptions = '\n'.join(description)

                # compute a string from directory_name which has all umlaute replaced with an underscore
                dirclean = directory_name.replace('ä', '_').replace('ö', '_').replace('ü', '_').replace('ß', '_').replace('Ä', '_').replace('Ö', '_').replace('Ü', '_')

                chunk = {
                    'url_s': 'https://www.gesetze-im-internet.de/' + origslug + '/__' + current_paragraph + '.html',
                    'directory_name': directory_name,
                    'title': title,
                    'description': descriptions + '\n' + title,
                    'paragraph': current_paragraph,
                    'text_t': descriptions + '\n' + title + '\n\n',
                    'level': level
                }
                if (current_paragraph != ''): chunks.append(chunk)
            else:
                if chunks:  # Append text to the last chunk
                    chunks[-1]['text_t'] += line

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

    split_files = 3

    # Calculate the number of chunks per file
    total_chunks = len(all_chunks)
    chunks_per_file = total_chunks // split_files

    # Write the JSON lines to three separate files
    for i in range(split_files):
        start_index = i * chunks_per_file
        end_index = (i + 1) * chunks_per_file if i < 2 else total_chunks
        file_chunks = all_chunks[start_index:end_index]

        file_name = f'bundestag_gesetze_part{i + 1}.jsonl'
        with open(file_name, 'w', encoding='utf-8') as json_file:
            for chunk in file_chunks:
                # Write the prefix line
                json_file.write(json.dumps({"index": {}}) + '\n')
                # Write the chunk as a JSON line
                json_file.write(json.dumps(chunk) + '\n')
            
# Run the function with the starting directory
find_and_parse_index_md('.')
