# Database fixer for Z64 custom music repositories | Version 1.1
import json
import os
import zipfile
import uuid
import traceback
import yaml
from pathlib import Path

def detectSongs():
    propertiesPath = 'z64packer/z64musicpacker.properties'
    binariesPath = 'z64packer/binaries.zip'
    songsPath = 'z64packer/z64songs.json'
    gamesPath = 'z64packer/z64games.json'

    if not os.path.exists(propertiesPath):
      print('This is not an Z64 repository | Missing z64musicpacker.properties file')
      return False
    
    with open(propertiesPath) as propertiesFile:
        properties = json.load(propertiesFile)
        binaries = properties['binaries']

        # Pack all the files in a single zip, to provide a faster download in the web tool
        with zipfile.ZipFile(binariesPath, 'w', zipfile.ZIP_DEFLATED) as binariesZip:

            # Try to create necessary files
            if not os.path.exists(songsPath):
                with open(songsPath, 'w+') as f: f.write('[]')
            if not os.path.exists(gamesPath):
                with open(gamesPath, 'w+') as f: f.write('[]')

            # First, open the games database
            with open(gamesPath, 'r+') as gamesFile:
                print("OPENING GAME DATABASE FILE")
                games = json.load(gamesFile)

                # Open the database, so we can modify it
                with open(songsPath, 'r+') as databaseFile:
                    print("OPENING SONG DATABASE FILE")
                    database = json.load(databaseFile)
                    
                    # First, check if the names and files are correct
                    # The database name has priority in this
                    for i, entry in enumerate(database):

                        # Check if the file is there...
                        actualPath = entry['file']
                        if os.path.isfile(os.path.join(binaries, actualPath)):
                            
                            # This commented snippet is for giving priority to the folder-file structure.
                            # But that's impossible, since if a file is renamed, we cannot know to which one it corresponds!
                            # So, if a file is renamed, it will be eliminated, and then readded.
                            # The only way to edit game names, is through the submission form, or directly inside the database.

                            # pathSplitted = actualPath.split('/')
                            # for index, pathSection in enumerate(reversed(pathSplitted)):
                            #    # Change the song name if the filename is different
                            #    if index == 0 and entry["song"] != Path(pathSection).stem:
                            #        print("DIFFERENT SONG NAME DETECTED")
                            #        print("Renaming: " + entry["song"] + " -> " + Path(pathSection).stem)
                            #        database[i]["song"] = Path(pathSection).stem
                            #    # Change the game name if the folder is different
                            #    if index == 1 and entry["game"] != pathSection:
                            #        print("DIFFERENT GAME NAME DETECTED")
                            #        print("Renaming: " + entry["game"] + " -> " + pathSection)
                            #        database[i]["game"] = pathSection
                            #    # Setup the series if there are a folder up this one
                            #    # else: games ...

                            # If the path in the folder structure, change it on the database!

                            # TODO: HERE WE NEED TO ADD THE SERIES TO THE INTENDED PATH

                            print("Checking name")
                            #intendedPath = entry['game'] + '/' + entry['song'] + os.path.splitext(actualPath)[1]
                            #if intendedPath != actualPath:
                            #    print("DIFFERENT PATH DETECTED")
                            #    print("Renaming: " + entry["file"] + " -> " + intendedPath)

                            #    # Only rename it if we find it... It may have changed already!
                            #    database[i]['file'] = intendedPath
                            #    os.renames(os.path.join(binaries, actualPath), os.path.join(binaries, intendedPath))


                        
                        # If we don't find it, then remove it from the database
                        # Still, evaluate if this is ok to do...
                        else:
                            print('MISSING ENTRY DETECTED')
                            print('Path: ' + actualPath)
                            print('Removing...')
                            database.pop(i)


                    # Check every single file inside the binaries folder
                    songs = os.walk(binaries)
                    for dirpath, dirnames, filenames in songs:
                        directory = dirpath.replace(binaries, '')

                        # Remove empty folders
                        if len(os.listdir(dirpath)) == 0:
                            print("EMPTY FOLDER DETECTED")
                            print("Folder: " + dirpath)
                            print("Clean up... Clean up...")
                            os.rmdir(dirpath)
                            continue

                        # Check every single file inside this  folder
                        for filename in filenames:
                            try:
                                # Only check ootrs and mmrs files
                                if not filename.endswith('.ootrs') and not filename.endswith('.mmrs'): continue

                                # Extract data from the file
                                type, categories, usesCustomBank, usesCustomSamples, usesFormmask = extractMetadata(os.path.join(dirpath, filename))

                                # GAME MANAGEMENT
                                # Update the games database
                                directories = directory.replace("\\","/").split('/')
                                game = safe_list_get(directories, -1, "Unknown")
                                series = safe_list_get(directories, -2, "") # We only go 1 up the directories... We don't support series in series
                                gameIndex = safe_list_index([x["game"] for x in games], game)
                                
                                # If it's not in the list, just add it
                                if gameIndex == None:
                                    print('Adding missing game to DB: ' + game + ' | ' + series)
                                    games.append({
                                        "game": game,
                                        "series": series,
                                        "platforms": [],
                                        "abbrName": game
                                    })
                                # If it's in the list, update it's series to match the folder structure
                                else:
                                    print('Updating game to series: ' + series)
                                    games[gameIndex]["series"] = series


                                # SONG MANAGEMENT
                                # Check if the file is in the database
                                fullPath = os.path.join(directory, filename).replace("\\","/")
                                detectedInDatabase = any(x["file"] == fullPath for x in database)

                                # If the file is in the DB, instead check it's integrity
                                if detectedInDatabase:
                                    print('Updating file on DB: ' + fullPath)
                                    i = [x["file"] for x in database].index(fullPath)
                                    database[i]["type"] = type
                                    database[i]["categories"] = categories
                                    database[i]["usesCustomBank"] = usesCustomBank
                                    database[i]["usesCustomSamples"] = usesCustomSamples
                                    database[i]["usesFormmask"] = usesFormmask

                                # If is not there, add it!
                                else:
                                    print('Adding missing file to DB: ' + fullPath)
                                    database.append({
                                        'game': game,
                                        'song': filename.replace('.ootrs', '').replace('.mmrs', ''),
                                        'type': type,
                                        'categories': categories,
                                        'usesCustomBank': usesCustomBank,
                                        'usesCustomSamples': usesCustomSamples,
                                        'usesFormmask': usesFormmask,
                                        'uuid': str(uuid.uuid4()),
                                        'file': fullPath
                                    })

                                # Add this file to the main zip
                                osPath = os.path.join(dirpath, filename)
                                binariesZip.write(osPath)

                            except Exception:
                                print("An error ocurred while processing the file " + filename + ": " + traceback.format_exc())

                    # Replace song database with this one
                    databaseFile.seek(0)
                    json.dump(database, databaseFile, indent=2)
                    databaseFile.truncate()

                 # Replace game database with this one
                gamesFile.seek(0)
                json.dump(games, gamesFile, indent=2)
                gamesFile.truncate()

    return True

def safe_list_get(list, idx, default):
  try:
    return list[idx]
  except IndexError:
    return default
  
def safe_list_index(iterable, value, default = None):
    for i, item in enumerate(iterable):
        if item == value:
            return i
    return default


def extractMetadata(path) -> tuple[str, list, bool, bool, bool]:
    archive = zipfile.ZipFile(path, 'r')
    namelist = archive.namelist()
    
    isOOTRS = path.endswith('.ootrs')
    isUniversalYamlFormat = any(n.endswith('.metadata') for n in namelist)
    
    if isUniversalYamlFormat: return extractMetadataFromUniversalYamlFormat(archive, namelist)
    elif isOOTRS: return extractMetadataFromOOTRS(archive, namelist)
    else: return extractMetadataFromMMRS(archive, namelist)

def extractMetadataFromUniversalYamlFormat(archive, namelist) -> tuple[str, list, bool, bool, bool]:
    for name in namelist:
        if name.endswith('.metadata'):
            with archive.open(name) as metadata_file:
                metadata_yaml = yaml.safe_load(metadata_file.read())
                metadata = metadata_yaml['metadata']

                # These first two are not optional!
                seq_type = metadata['song type'].lower()
                groups = metadata['music groups']
                usesCustomBank = any(n.endswith('.zbank') for n in namelist)
                usesCustomSamples = any(n.endswith('.zsound') for n in namelist)
                usesFormmask = len(metadata.get('formmask', [])) > 0

                return seq_type, groups, usesCustomBank, usesCustomSamples, usesFormmask


def extractMetadataFromOOTRS(archive, namelist) -> tuple[str, list, bool, bool, bool]:
    for name in namelist:
        if name.endswith('.meta'):
            with archive.open(name) as meta_file:
                lines = meta_file.readlines()
                lines = [line.decode('utf8').rstrip() for line in lines]

                # Extract the type and groups
                seq_type = (lines[2] if len(lines) >= 3 else 'bgm').lower()
                groups = [g.strip() for g in lines[3].split(',')] if len(lines) >= 4 else []

                # Check if uses custom banks and samples
                usesCustomBank = any(n.endswith('.zbank') for n in namelist)
                usesCustomSamples = any(n.endswith('.zsound') for n in namelist)

                return seq_type, groups, usesCustomBank, usesCustomSamples, False


def extractMetadataFromMMRS(archive, namelist) -> tuple[str, list, bool, bool, bool]:
    for name in namelist:
        if name == 'categories.txt':
            with archive.open(name) as categories_file:
                lines = categories_file.readlines()
                lines = [line.decode('utf8').rstrip() for line in lines]

                # Extract the categories
                categories = [g.strip() for g in lines[0].replace('-', ',').split(',')] if len(lines) >= 1 else []

                # Define the type by checking the categories
                isFanfare = all(cat in ['8', '9', '10'] for cat in categories) and len(categories) > 0
                seq_type = 'fanfare' if isFanfare else 'bgm'

                # Check if uses custom banks and samples
                usesCustomBank = any(n.endswith('.zbank') for n in namelist)
                usesCustomSamples = any(n.endswith('.zsound') for n in namelist)
                usesFormmask = any(n.endswith('.formmask') for n in namelist)

                return seq_type, categories, usesCustomBank, usesCustomSamples, usesFormmask

    

def main():
    result = detectSongs()

    if result: print("Process completed succesfully!")
    else: print("An error occured")


if __name__ == '__main__':
    main()
    