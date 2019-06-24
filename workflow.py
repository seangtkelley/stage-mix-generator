import youtube_dl
import utils
import os
import glob
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import numpy as np
from secrets import randbelow

from cvcalib.audiosync import offset

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
DWNLD_DIR = os.path.join(CURR_DIR, 'temp')

def gen_mix(song_audio_filepath, stage_video_filepaths, stage_audio_filepaths, edit_style=0):

    song_audio_filename = song_audio_filepath.split(os.path.sep)[-1]
    stage_audio_filenames = [path.split(os.path.sep)[-1] for path in stage_audio_filepaths]

    # find timestamp of start of song in stage videos
    stage_song_starts = []
    for i in range(len(stage_video_filepaths)):
        try:
            output = offset.find_time_offset([song_audio_filename, stage_audio_filenames[i]], DWNLD_DIR+os.path.sep, [0, 0])
            print(output)
            stage_song_starts.append(output[0])
        except Exception as e:
            print(e)
            stage_song_starts.append((1, 0))
    
    # get subclips of the song in the stage videos
    stage_videos_used, stage_videos, stage_audios = [], [], []
    for i in range(len(stage_video_filepaths)):
        if stage_song_starts[i][0] == 0:
            stage_videos_used.append(i)
            stage_videos.append(VideoFileClip(stage_video_filepaths[i]).subclip(stage_song_starts[i][1]))
            stage_audios.append(AudioFileClip(stage_audio_filepaths[i]).subclip(stage_song_starts[i][1]))

    if len(stage_videos) == 0:
        print("No suitible videos found")
        return None, None
    
    # load song audio
    song_audio = AudioFileClip(song_audio_filepath)

    clips = []
    if edit_style == 1:
        # find cuts in videos
        video_scenes = []
        for idx in stage_videos_used:
            video_scenes.append(utils.detect_scenes(stage_video_filepaths[idx]))

        # assemble clips
        curr_time = 0.0
        print("song duration:", float(song_audio.duration))
        while curr_time < float(song_audio.duration):
            print("curr_time:", curr_time)

            # choose random video
            rand_idx = randbelow(len(stage_videos))

            # skip shorter videos
            if curr_time > float(stage_videos[rand_idx].duration)+2:
                continue

            # get next cut in this video
            # TODO: make this more efficient
            for i, scene in enumerate(video_scenes[rand_idx]):
                scene_end = utils.timecode_to_seconds(scene[1].get_timecode()) - stage_song_starts[rand_idx][1]
                if scene_end > curr_time+1.0 and scene_end < float(song_audio.duration)+5:
                    clips.append(stage_videos[rand_idx].subclip(curr_time, scene_end))   
                    curr_time = scene_end
                    break

    else:
        # every 5 seconds during the song, splice clips from different performances
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
    mix_filepath = os.path.join(CURR_DIR, "stage_mix.mp4")
    final_clip.write_videofile(mix_filepath)

    return mix_filepath, stage_videos_used

def main():
    # get video urls
    lyrics_video_url, stage_video_urls = utils.find_urls_from_search('BTS', 'Fake Love')

    # download videos
    utils.download_yt_video(lyrics_video_url, utils.LA_FMT, utils.LA_EXT, DWNLD_DIR, f"lyrics_audio.{utils.LA_EXT}")
    for i, url in enumerate(stage_video_urls):
        try:
            utils.download_yt_video(url, utils.SV_FMT, utils.SV_EXT, DWNLD_DIR, f"stage_video{i}.{utils.SV_EXT}")
            utils.download_yt_video(url, utils.SA_FMT, utils.SA_EXT, DWNLD_DIR, f"stage_audio{i}.{utils.SA_EXT}")
        except Exception as e:
            print(e)
            stage_video_urls.remove(url)

    song_audio_path = os.path.join(DWNLD_DIR, f"lyrics_audio.{utils.LA_EXT}")
    stage_video_paths = [ os.path.join(DWNLD_DIR, f"stage_video{i}.{utils.SV_EXT}") for i in range(len(stage_video_urls)) ]
    stage_audio_paths = [ os.path.join(DWNLD_DIR, f"stage_audio{i}.{utils.SA_EXT}") for i in range(len(stage_video_urls)) ]

    mix_filepath, stage_videos_used = gen_mix(song_audio_path, stage_video_paths, stage_audio_paths, edit_style=1)

    utils.upload_to_yt(mix_filepath, 'BTS - Fake Love - Stage Mix', "Videos Used: \n" + "\n".join([ stage_video_urls[i] for i in stage_videos_used ]))

    # delete the downloaded videos
    # for i in glob.glob(os.path.join(download_dir, '*')):
    #     os.remove(i)

if __name__ == "__main__":
    main()