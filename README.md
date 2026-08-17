
# M3U8-Inspector

M3U8-Inspector is simple CLI that is quick and easy way to view, parse, stream, and download M3U8 files. I created this because I wanted a quick and easy way to view and download M3U8 playlists through a CLI.
## Installation

Install M3U8-Inspector via Python

```bash
git clone https://github.com/Notmetnet/M3U8-Inspector.git
cd M3U8-Inspector
```

Install dependencies

```bash
python3 -m venv venv
pip install -r requirements.txt
```
## Basic Usage/Examples

Brings up the help menu

```bash
python3 M3U8-Inspector.py -h
```

The URL (or the file) of the M3U8 is required for the parser to work

```bash
python3 M3U8-Inspector.py -u 'https://some-m3u8-url.com/playlist.m3u8'
```

or 

```bash
python3 M3U8-Inspector.py -u 'C:/some/path/to/m3u8/playlist.m3u8'
```

A quick and simple way to check if a M3U8 source is a playlist or master is

```bash
python M3U8-Inspector.py -u 'https://some-m3u8-url.com/playlist.m3u8' --is-master
```

### Downloader

M3U8-Inspector allows for a quick and easy way to download the segments of playlists and build a **playlist.m3u8** containing the downloaded segments.

This command will download the segments of the M3U8 playlist and output them in the directory `./output` along with the **playlist.m3u8** *(This only works on URLS)*.

```bash
python M3U8-Inspector.py -u 'https://some-m3u8-url.com/playlist.m3u8' --download
```

### Streamer

M3U8 sources are streamed via HTTP on a web browser. M3U8 sources can also be streamed if they're already downloaded.

The command to stream a URL via is

```bash
python3 M3U8-Inspector.py -u 'https://some-m3u8-url.com/playlist.m3u8'  --stream-playlist
```

To stream already downloaded playlists is

```bash
python3 M3U8-Inspector.py -u 'C:/some/path/to/m3u8/playlist.m3u8' --stream-local
```
## Upcoming features

- Stream M3U8 URLs with custom headers
- More options for the CLI
- Frontend webpage along side CLI
- Allow frontend stream pages to altered
- Allowing multiple M3U8 playlists to be linked together *(Have episode integration)*
