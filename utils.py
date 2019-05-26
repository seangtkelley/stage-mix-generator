import os
import shutil
import youtube_dl
import urllib.request
from bs4 import BeautifulSoup
from subprocess import Popen, PIPE

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