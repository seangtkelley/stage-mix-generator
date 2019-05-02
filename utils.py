import os
import shutil
import youtube_dl
import urllib.request
from bs4 import BeautifulSoup

def get_mcountdown_top(n=10):
    pass

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