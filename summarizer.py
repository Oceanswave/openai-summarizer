import os
from os import listdir, getenv
from os.path import isfile, join, expanduser
import time
import json
from dotenv import load_dotenv

import openai
import whisper
from elevenlabslib import *

load_dotenv()

opanai_api_key = getenv("OPENAI_API_KEY")
if (opanai_api_key == None):
    print("OPENAI_API_KEY is not set")
    exit(1)

monitoring_dir = getenv("SUMMARIZER_PATH")
if (monitoring_dir == None):
    monitoring_dir = expanduser('~/Music/Teams')
    
openai.api_key = opanai_api_key
whisperModel = whisper.load_model("large")
                           
#function to return files in a directory
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
                    print("mp3 file found")
                    convertAudioToText(my_dir, join(my_dir, file))
            elif file.lower().endswith("-transcript.json"):
                    print("json transcript file found")
                    summarizeText(my_dir, join(my_dir, file))

def convertAudioToText(my_dir: str, audioFilePath: str):
    print("converting audio to text for file: " + audioFilePath + "...")
    # decode_options = dict(fp16=False)
    # transcribe_options = dict(task="transcribe", **decode_options)
    # transcript = whisperModel.transcribe(audioFilePath, **transcribe_options)
    audio_file = open(audioFilePath, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    with open(join(my_dir, os.path.abspath(os.path.splitext(audioFilePath)[0]) + "-transcript.json"), "w") as outfile:
        outfile.write(json.dumps(transcript, indent=4))
    print("text: " + transcript["text"])
    return transcript

def summarizeText(my_dir: str, whisperFilePath: str):
    print("summarizing text...")
    jsonData = open(whisperFilePath)
    data = json.load(jsonData)
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
        {"role": "system", "content": "You are a helpful assistant that summaries transcripts for users. You make an attempt to identify the most important parts of the transcript ."},
        {"role": "user", "content": "Please provide a detailed summary of the following transcript pointing out five key highlights and any action items. Additionally, list each individual in the conversation, provide their names if available along with their roles. Additionally, list any questions and their answers. Finally, include any key statements they made and indicate the person who said them:\n" + data["text"]},
      ]
    )
    with open(join(my_dir, os.path.abspath(os.path.splitext(whisperFilePath)[0]) + "-summary.json"), "w") as outfile:
        outfile.write(json.dumps(response, indent=4))
    print(response["choices"][0]["message"]["content"])
    return response

fileWatcher(monitoring_dir, 1)