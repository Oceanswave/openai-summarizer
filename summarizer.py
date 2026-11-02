import os
from os import listdir, getenv
from os.path import isfile, join, expanduser
import time
import json
import tiktoken
from dotenv import load_dotenv

import openai

load_dotenv()

opanai_api_key = getenv("OPENAI_API_KEY")
if (opanai_api_key == None):
    print("OPENAI_API_KEY is not set")
    exit(1)

monitoring_dir = getenv("SUMMARIZER_PATH")
if (monitoring_dir == None):
    monitoring_dir = expanduser('~/Music/Teams')
    
openai.api_key = opanai_api_key
                           
def fileInDirectory(my_dir: str):
    onlyfiles = [f for f in listdir(my_dir) if isfile(join(my_dir, f))]
    return(onlyfiles)

def listComparison(OriginalList: list, NewList: list):
    differencesList = [x for x in NewList if x not in OriginalList]
    return(differencesList)
    
def fileWatcher(my_dir: str, pollTime: int):
    while True:
        if 'watching' not in locals(): #Check if this is the first time the function has run
            previousFileList = fileInDirectory(my_dir)
            watching = 1
            print('First Time')
            print(previousFileList)
        
        time.sleep(pollTime)
        
        newFileList = fileInDirectory(my_dir)
        
        fileDiff = listComparison(previousFileList, newFileList)
        
        previousFileList = newFileList
        if len(fileDiff) == 0: continue

        for file in fileDiff:
            if file.lower().endswith(".mp3"):
                    print(f"mp3 file found {file}")
                    convertAudioToText(my_dir, join(my_dir, file))
            elif file.lower().endswith("-transcript.json"):
                    print(f"json transcript file found: {file}")
                    summarizeText(my_dir, join(my_dir, file))

def convertAudioToText(my_dir: str, audioFilePath: str):
    print("converting audio to text for file: " + audioFilePath + "...")
    audio_file = open(audioFilePath, "rb")
    params = dict(prompt="Speaker 1: Hello, World.\nSpeaker 2: That's Great.\n")
    transcript = openai.Audio.transcribe("whisper-1", audio_file, **params)
    with open(join(my_dir, os.path.abspath(os.path.splitext(audioFilePath)[0]) + "-transcript.json"), "w") as outfile:
        outfile.write(json.dumps(transcript, indent=4))
    print("text: " + transcript["text"])
    return transcript

def create_chunks(text, chunkSize, overlap):
    tt_encoding = tiktoken.get_encoding("gpt2")
    tokens = tt_encoding.encode(text)
    total_tokens = len(tokens)

    chunks = []
    for i in range(0, total_tokens, chunkSize - overlap):
        chunk = tokens[i:i + chunkSize]
        chunks.append(chunk)
    return chunks

def summarizeText(my_dir: str, whisperFilePath: str):
    print("summarizing text...")
    jsonData = open(whisperFilePath)
    data = json.load(jsonData)
    text = data["text"];
    chunks = create_chunks(text, 3000, 50)
    tt_encoding = tiktoken.get_encoding("gpt2")
    final_response = [];
    for index, chunk in enumerate(chunks):
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summaries transcripts for users. You make an attempt to identify the most important parts of the transcript ."},
                {"role": "user", "content": f"Think this through step by step: Please provide a detailed summary of the following transcript pointing out five key highlights and any action items. Additionally, list each individual in the conversation, provide their names if available along with their roles. Additionally, list all questions made in the conversation and provide what answers that were provided. Finally, include any key statements they made and indicate the person who said them:\n {tt_encoding.decode(chunk)}"},
            ]
        )
        with open(join(my_dir, os.path.abspath(os.path.splitext(whisperFilePath)[0]) + f"-summary-{index}.json"), "w") as outfile:
            outfile.write(json.dumps(response, indent=4))

        final_response.append(response["choices"][0]["message"]["content"])

    with open(join(my_dir, os.path.abspath(os.path.splitext(whisperFilePath)[0]) + f"-summary.txt"), "w") as outfile:
        outfile.write(' '.join(map(str, final_response)))
    print(final_response)
    return response

fileWatcher(monitoring_dir, 1)