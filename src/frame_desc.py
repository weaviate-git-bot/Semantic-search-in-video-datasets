import argparse
import json
import subprocess
import os
from PIL import Image
import open_clip
import torch
import time

# Initialize the model
model, _, transform = open_clip.create_model_and_transforms(
    "coca_ViT-L-14",
    pretrained="mscoco_finetuned_laion2B-s13B-b90k"
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def output_generate(image):
    im = transform(image).unsqueeze(0).to(device)
    model.to(device)
    im = im.float()
    with torch.no_grad(), torch.cuda.amp.autocast():
        generated = model.generate(im, seq_len=20)
    return open_clip.decode(generated[0].detach()).split("<end_of_text>")[0].replace("<start_of_text>", "")


def get_image(frames, video_file, folder_path):
    ffmpeg_commands = []
    for i, frame in enumerate(frames):
        ffmpeg_commands.append(f"ffmpeg -ss {frame} -i {video_file} -vframes 1 {folder_path}/{frame}.jpg")
    for command in ffmpeg_commands:
        subprocess.run(command, shell=True)


def process_video_frames(video_file, json_file, folder_path):
    with open(json_file) as f:
        data = json.load(f)

    for sent in data['sentences']:
        frames = []
        starttime = sent['starttime']
        endtime = sent['endtime']
        frames.append(starttime)
        frames.append(endtime)
        midtime = (float(starttime) + float(endtime)) / 2
        frames.append(midtime)
        if sent['verbs'] != []:
            for verb in sent['verbs']:
                if verb not in frames:
                    frames.append(verb['vstart'])
        
        get_image(frames, video_file, folder_path)
        
        frame_data = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            if os.path.isfile(file_path):
                image = Image.open(file_path)
                frame_text = output_generate(image)
                print(frame_text, 'f')
                frame_data.append(frame_text)
                os.remove(file_path)
        
        frame_data = unique(frame_data)
        sent['frame_data'] = frame_data
    
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=1)


def main(video_file, json_file, folder_path):

    # Process video frames
    process_video_frames(video_file, json_file, folder_path)

    # End measuring time
    end_time = time.time()
    execution_time = end_time - start_time


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process video frames and generate frame data")
    parser.add_argument("video_file", type=str, help="Input video file path")
    parser.add_argument("json_file", type=str, help="Input JSON file path")
    parser.add_argument("folder_path", type=str, help="Folder path to store frames")
    args = parser.parse_args()

    main(args.video_file, args.json_file, args.folder_path)
