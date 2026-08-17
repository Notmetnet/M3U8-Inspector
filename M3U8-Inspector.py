import argparse

from modules.m3u8Parser import (
    HEADERS,
    LocalM3u8Streamer,
    M3u8Downloader,
    M3u8Parser,
    M3u8Streamer,
    StreamInfo,
)

parser = argparse.ArgumentParser(
    description="Extract and parse M3U8 files and links made easier."
)

_ = parser.add_argument(  # Required source
    "-u", "--url", required=True, help="The source of the M3U8 content."
)

_ = parser.add_argument(  # Checks if playlist is master
    "-iM",
    "--is-master",
    action="store_true",
    help="Checks if the M3U8 source is a master playlist.",
)

_ = parser.add_argument(  # Dispalys list of streams
    "-lS",
    "--list-streams",
    action="store_true",
    help="Displays the list of streams in a master playlist.",
)

_ = parser.add_argument(
    "-lC",
    "--list-contents",
    action="store_true",
    help="Returns the full contents of the M3U8 source.",
)

_ = parser.add_argument(
    "-sP",
    "--stream-playlist",
    action="store_true",
    help="Streams the M3U8 playlist via HTTP.",
)

_ = parser.add_argument(
    "-sL",
    "--stream-local",
    action="store_true",
    help="Streams local M3U8 playlist via HTTP.",
)

_ = parser.add_argument(
    "-d",
    "--download",
    action="store_true",
    help="Downloads the selected M3U8 playlist (Only downloads the playlist.)",
)


def parse_is_master(url: str) -> bool:
    m3u8_parser = M3u8Parser(source=url)
    _ = m3u8_parser.parse()

    return m3u8_parser.is_master()


def parse_list_streams(url: str) -> list[StreamInfo]:
    m3u8_parser = M3u8Parser(source=url)
    _ = m3u8_parser.parse()

    return m3u8_parser.get_streams()


def parse_list_contents(url: str) -> str:
    m3u8_parser = M3u8Parser(source=url)
    _ = m3u8_parser.parse()

    return m3u8_parser.get_content()


def parse_stream_segments(url: str, local: bool = False):
    if not local:
        m3u8_parser = M3u8Streamer(source=url, headers=HEADERS)
        m3u8_parser.stream()
    else:
        streamer = LocalM3u8Streamer(source=url)
        streamer.stream()


def parse_download(url: str):
    playlist = M3u8Parser(source=url)
    _ = playlist.parse()

    if not playlist.is_master():
        print("Cannot be a master playlist.")

    timestamps = playlist.get_timestamps()
    segments = playlist.get_segments()

    downloader = M3u8Downloader(
        timestamps=timestamps, segments=segments, output="./output"
    )
    output_path = downloader.download_segments()

    print(f"Saved to: {output_path}")


class Args(argparse.Namespace):
    is_master: bool | None = None
    url: str = ""
    list_streams: bool | None = None
    list_contents: bool | None = None
    stream_playlist: bool | None = None
    stream_local: bool | None = None
    download: bool | None = None


if __name__ == "__main__":
    args = parser.parse_args(namespace=Args())

    if args.is_master:
        print(parse_is_master(args.url))
    elif args.list_streams:
        streams = parse_list_streams(args.url)
        print()
        for stream in streams:
            print(f"Stream Link: {stream.get('M3U8-LINK')}")
            print(f"Resolution: {stream.get('RESOLUTION')}\n")

    elif args.list_contents:
        print()
        print(parse_list_contents(args.url))

    elif args.stream_playlist:
        parse_stream_segments(args.url)

    elif args.stream_local:
        parse_stream_segments(args.url, local=True)

    elif args.download:
        parse_download(args.url)
