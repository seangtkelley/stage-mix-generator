import os
import shutil
import youtube_dl
import urllib.request
from bs4 import BeautifulSoup
from subprocess import Popen, PIPE
import datetime

import scenedetect
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.stats_manager import StatsManager
from scenedetect.detectors import ContentDetector

LA_FMT = '140'
LA_EXT = 'm4a'

SV_FMT = '137'
SV_EXT = 'mp4'

SA_FMT = '140'
SA_EXT = 'm4a'

def yt_search(query, exclude="completely garbage string lmao"):
    query = urllib.parse.quote(query)
    url = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&search_query="+query
    response = urllib.request.urlopen(url)
    html = response.read()
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for vid in soup.findAll(attrs={'class':'yt-uix-tile-link'}):
        if exclude not in vid['title'].lower():
            results.append('https://www.youtube.com' + vid['href'])
    return results

def download_yt_video(url, fmt, ext, output_dir, output_name):

    ydl_opts = {
        'format': fmt,
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s')
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        meta = ydl.extract_info(url, download=False)
        shutil.move(os.path.join(output_dir, f"{meta['id']}.{ext}"), os.path.join(output_dir, output_name))

def find_urls_from_search(artist, title, n=12):
    # get lyrics and stage videos from search
    lyrics_video_url = yt_search(f"{artist} {title} lyrics")[0]
    stage_video_urls = yt_search(f"{artist} {title} live performance", exclude='stage mix')[:n+1]
    return lyrics_video_url, stage_video_urls

def upload_to_yt(filepath, title, desc, private=True):
    # upload video to youtube
    args = [
        "python", 
        f"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'youtube-upload', 'bin', 'youtube-upload')}",
        f"--title={title}",
        f"--description={desc}",
        f"{filepath}"
    ]
    if private:
        args.extend(["--privacy", "private"])

    process = Popen(args, stdout=PIPE, stderr=PIPE)
    output, err = process.communicate()
    exit_code = process.wait()
    print(exit_code, str(err), str(output))

def detect_scenes(filepath):
    video_manager = VideoManager([filepath])
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)
    # Add ContentDetector algorithm (constructor takes detector options like threshold).
    scene_manager.add_detector(ContentDetector(threshold=40))
    base_timecode = video_manager.get_base_timecode()

    STATS_FILE_PATH = f"{filepath.split('/')[-1]}.stats.csv"

    try:
        # If stats file exists, load it.
        if os.path.exists(STATS_FILE_PATH):
            # Read stats from CSV file opened in read mode:
            with open(STATS_FILE_PATH, 'r') as stats_file:
                stats_manager.load_from_csv(stats_file, base_timecode)

        # Set downscale factor to improve processing speed.
        video_manager.set_downscale_factor()

        # Start video_manager.
        video_manager.start()

        # Perform scene detection on video_manager.
        scene_manager.detect_scenes(frame_source=video_manager)

        # Obtain list of detected scenes.
        scene_list = scene_manager.get_scene_list(base_timecode)
        # Like FrameTimecodes, each scene in the scene_list can be sorted if the
        # list of scenes becomes unsorted.

        # We only write to the stats file if a save is required:
        if stats_manager.is_save_required():
            with open(STATS_FILE_PATH, 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)

        # print('List of scenes obtained:')
        # for i, scene in enumerate(scene_list):
        #     print('    Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
        #         i+1,
        #         scene[0].get_timecode(), scene[0].get_frames(),
        #         scene[1].get_timecode(), scene[1].get_frames(),))
            
        return scene_list
        
    finally:
        video_manager.release()

def timecode_to_seconds(timecode):
    hrs, mins, secs = list(map(float, timecode.split(":")))
    return secs + mins*60 + hrs*3600