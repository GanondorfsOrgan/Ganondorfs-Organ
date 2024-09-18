import json
import os
import traceback
import zipfile
import shutil

def extract_ootrs_files(base_dir='.'):
    """Extract all .ootrs files in any subdirectory of the base directory."""
    extracted_files = []
    extracted_parent_dirs = set()
    
    # Recursively walk through all directories starting from base_dir
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.ootrs'):
                ootrs_path = os.path.join(root, file)
                extract_dir = os.path.join(root, 'extracted', file.replace('.ootrs', ''))
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(ootrs_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    extracted_files.append(extract_dir)
                    extracted_parent_dirs.add(os.path.dirname(extract_dir))  # Track parent folder
    return extracted_files, list(extracted_parent_dirs)

def generate_song_list():
    extracted_dirs, extracted_parent_dirs = extract_ootrs_files()

    if not extracted_dirs:
        print("No .ootrs files found or extraction failed.")
        return False

    song_list = ""
    groups = {'_$ungrouped_songs$_': []}

    for extracted_dir in extracted_dirs:
        for root, dirs, files in os.walk(extracted_dir):
            level = root.replace(extracted_dir, '').count(os.sep)
            indent = ' ' * 4 * level
            song_list += f'{indent}- {os.path.basename(root)}\n'
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                if not f.endswith('.meta'):
                    continue
                song_name, instrument_set, seq_type, seq_groups = parse_meta_file(root, f)
                song_list += f'{subindent}key: {song_name}\n'
                for group in seq_groups:
                    if group not in groups:
                        groups[group] = []
                    groups[group].append(song_name)
                if not seq_groups:
                    groups['_$ungrouped_songs$_'].append(song_name)

    try:
        create_song_list_file(song_list, groups)
    except Exception as e:
        print("An error occurred creating the song list")
        print(traceback.format_exc())
        return False

    # Now delete the temporary extracted directories and parent folder(s)
    cleanup_extracted_directories(extracted_dirs, extracted_parent_dirs)

    return True

def create_song_list_file(song_list, groups):
    """Create the song_list.txt and groups_list.json files."""
    with open('song_list.txt', 'w', encoding='utf-8') as song_list_file:
        song_list_file.write(song_list)

    if groups:
        with open('groups_list.json', 'w', encoding='utf-8') as groups_file:
            json_output = {'groups': groups, 'ungrouped_songs': groups.pop('_$ungrouped_songs$_')}
            if not json_output['ungrouped_songs']:
                del json_output['ungrouped_songs']
            json.dump(json_output, groups_file, indent=4, ensure_ascii=False, sort_keys=True)

def cleanup_extracted_directories(extracted_dirs, extracted_parent_dirs):
    """Delete the extracted directories and the parent 'extracted' folder after processing."""
    
    # Delete the individual extracted directories first
    for dir_path in extracted_dirs:
        try:
            shutil.rmtree(dir_path)
            print(f"Temporary directory '{dir_path}' deleted.")
        except Exception as e:
            print(f"Error deleting directory {dir_path}: {e}")

    # Now remove the parent extracted folder(s) if empty
    for parent_dir in extracted_parent_dirs:
        if os.path.exists(parent_dir):
            try:
                if not os.listdir(parent_dir):
                    shutil.rmtree(parent_dir)
                    print(f"Parent 'extracted' folder '{parent_dir}' deleted.")
            except Exception as e:
                print(f"Error deleting the 'extracted' folder {parent_dir}: {e}")

def parse_meta_file(root, file):
    """Parse the contents of the .meta file."""
    path = os.path.join(root, file)
    with open(path, 'r', encoding='utf-8') as meta_file:
        lines = meta_file.readlines()

    lines = [line.rstrip() for line in lines]
    song_name = lines[0]
    instrument_set = lines[1]
    seq_type = lines[2] if len(lines) >= 3 else 'bgm'
    groups = [g.strip() for g in lines[3].split(',')] if len(lines) >= 4 else []

    return song_name, instrument_set, seq_type, groups

def main():
    song_list_generated = generate_song_list()

    if song_list_generated:
        print("song_list.txt file successfully created!")
        print("Have fun customizing your randomizer! :)")
        print("")
    else:
        print("An error occurred generating your song list")
    input("Press enter to quit.")

if __name__ == '__main__':
    main()
