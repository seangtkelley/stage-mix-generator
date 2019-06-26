from flask import Flask, request, render_template
import os
import utils, workflow

app = Flask(__name__)

@app.route("/", methods=['GET'])
def main():
    return render_template('main.html')

@app.route("/create", methods=['POST'])
def create():
    if request.form.get('findVideos', False):
        # get video urls from youtube search
        song_audio_url, stage_video_urls = utils.find_urls_from_search(request.form['artist'], request.form['songTitle'])
    else:
        # get videos from form
        song_audio_url = request.form['songAudioUrl']
        stage_video_urls = request.form['stageVideoUrls'].splitlines()

    # download videos
    utils.download_yt_video(song_audio_url, utils.LA_FMT, utils.LA_EXT, workflow.DWNLD_DIR, f"song_audio.{utils.LA_EXT}")
    for i, url in enumerate(stage_video_urls):
        try:
            utils.download_yt_video(url, utils.SV_FMT, utils.SV_EXT, workflow.DWNLD_DIR, f"stage_video{i}.{utils.SV_EXT}")
            utils.download_yt_video(url, utils.SA_FMT, utils.SA_EXT, workflow.DWNLD_DIR, f"stage_audio{i}.{utils.SA_EXT}")
        except Exception as e:
            print(e)
            stage_video_urls.remove(url)

    # build filepaths to downloaded videos
    song_audio_path = os.path.join(workflow.DWNLD_DIR, f"song_audio.{utils.LA_EXT}")
    stage_video_paths = [ os.path.join(workflow.DWNLD_DIR, f"stage_video{i}.{utils.SV_EXT}") for i in range(len(stage_video_urls)) ]
    stage_audio_paths = [ os.path.join(workflow.DWNLD_DIR, f"stage_audio{i}.{utils.SA_EXT}") for i in range(len(stage_video_urls)) ]

    # create mix
    edit_style = int(request.form.get('editingOption', 0))
    mix_filepath, stage_videos_used = workflow.gen_mix(song_audio_path, stage_video_paths, stage_audio_paths, edit_style=edit_style)

    if request.form.get('ytUpload', False):
        utils.upload_to_yt(mix_filepath, f"{request.form['artist']} - {request.form['songTitle']} - Stage Mix", "Videos Used: \n" + "\n".join([ stage_video_urls[i] for i in stage_videos_used ]))

    return "Mix Created"