import youtube_dl
import utils
import os
import glob
from subprocess import Popen, PIPE
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import numpy as np

from cvcalib.audiosync import offset

curr_dir = "/home/sean/Documents/experiments/stage-mix-generator/"
download_dir = os.path.join(curr_dir, 'temp')

# get top kpop songs
songs = [
    { 'artist': 'Red Velvet', 'title': 'Bad Boy' },
    #{ 'artist': 'ITZY', 'title': 'DALLA DALLA' },
    #{ 'artist': 'Chung ha', 'title': 'Gotta Go' }
]

LA_FMT = '140'
LA_EXT = 'm4a'

SV_FMT = '137'
SV_EXT = 'mp4'

SA_FMT = '140'
SA_EXT = 'm4a'

for song in songs:

    # get lyrics and stage videos from search
    lyrics_video_url = utils.yt_search(song['artist']+" "+song['title']+' lyrics')[0]
    stage_video_urls = utils.yt_search(song['artist']+" "+song['title']+' live performance', exclude='stage mix')[:8]

    # download videos
    utils.download_yt_video(lyrics_video_url, LA_FMT, LA_EXT, download_dir, f"lyrics_audio.{LA_EXT}")
    for i, url in enumerate(stage_video_urls):
        try:
            utils.download_yt_video(url, SV_FMT, SV_EXT, download_dir, f"stage_video{i}.{SV_EXT}")
            utils.download_yt_video(url, SA_FMT, SA_EXT, download_dir, f"stage_audio{i}.{SA_EXT}")
        except Exception as e:
            print(e)
            stage_video_urls.remove(url)

    song_audio_path = os.path.join(download_dir, f"lyrics_audio.{LA_EXT}")
    stage_video_paths = [ os.path.join(download_dir, f"stage_video{i}.{SV_EXT}") for i in range(len(stage_video_urls)) ]
    stage_audio_paths = [ os.path.join(download_dir, f"stage_audio{i}.{SA_EXT}") for i in range(len(stage_video_urls)) ]
    
    # find timestamp of start of song in stage videos
    stage_song_starts = []
    for i in range(len(stage_video_urls)):
        try:
            output = offset.find_time_offset([f"lyrics_audio.{LA_EXT}", f"stage_audio{i}.{SA_EXT}"], download_dir+'/', [0, 0])
            print(output)
            stage_song_starts.append(output[0])
        except Exception as e:
            print(e)
            stage_song_starts.append((1, 0))
    
    # get subclips of the song in the stage videos
    stage_videos_used, stage_videos, stage_audios = [], [], []
    for i in range(len(stage_video_paths)):
        if stage_song_starts[i][0] == 0:
            stage_videos_used.append(i)
            stage_videos.append(VideoFileClip(stage_video_paths[i]).subclip(stage_song_starts[i][1]))
            stage_audios.append(AudioFileClip(stage_audio_paths[i]).subclip(stage_song_starts[i][1]))

    if len(stage_videos) == 0:
        print("No suitible videos found")
        continue
    
    # load song audio
    song_audio = AudioFileClip(song_audio_path)

    # every 5 seconds during the song, splice clips from different performances
    clips = []
    stage_video_idx = 0
    for step in np.arange(0, song_audio.duration, 5):
        if step+5 < stage_videos[stage_video_idx].duration:
            clips.append(stage_videos[stage_video_idx].subclip(step, step+5))
        
        stage_video_idx = (stage_video_idx + 1) % len(stage_videos)

    # assemble clips 
    final_clip = concatenate_videoclips(clips)

    # replace audio with first stage video
    final_clip = final_clip.set_audio(stage_audios[0])

    # write mix
    final_clip.write_videofile(f"stage_mix.mp4")

    # upload video to youtube
    title = f"{song['artist']} - {song['title']} - Stage Mix"
    desc = "Videos Used: \n" + "\n".join([ stage_video_urls[i] for i in stage_videos_used ])
    args = [
        "python", 
        f"{os.path.join(curr_dir, 'youtube-upload', 'bin', 'youtube-upload')}",
        f"--title={title}",
        f"--description={desc}",
        f"{os.path.join(curr_dir, 'stage_mix.mp4')}",
        "--privacy",
        "private"
    ]
    process = Popen(args, stdout=PIPE, stderr=PIPE)
    output, err = process.communicate()
    exit_code = process.wait()
    print(exit_code, str(err), str(output))

    # delete the downloaded videos
    for i in glob.glob(os.path.join(download_dir, '*')):
        os.remove(i)