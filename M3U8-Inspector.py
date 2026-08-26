import argparse

from modules.M3u8Downloader import M3u8Downloader
from modules.M3u8Parser import M3u8Parser
from modules.M3u8Streamer import LocalM3u8Streamer, M3u8Streamer

parser = argparse.ArgumentParser(
    description="Extract and parse M3U8 files and links made easier."
)

subparsers = parser.add_subparsers(dest="command")

m3u8_parser = subparsers.add_parser("parse", help="Parse M3U8 sources.")
downloader = subparsers.add_parser("download", help="Download M3U8 sources.")
streamer = subparsers.add_parser("streamer", help="Stream M3U8 sources.")

# *
# * M3U8 Parser subparser
# *

_ = m3u8_parser.add_argument(
    "-u", "--url", required=True, help="The source of the M3U8 content."
)

_ = m3u8_parser.add_argument("-H", "--headers", help="Use custom headers")

_ = m3u8_parser.add_argument(
    "-iM",
    "--is-master",
    action="store_true",
    help="Checks if the M3U8 source is a master playlist.",
)

_ = m3u8_parser.add_argument(
    "-lS",
    "--list-streams",
    action="store_true",
    help="Displays the list of streams in a master playlist.",
)

_ = m3u8_parser.add_argument(
    "-lC",
    "--list-contents",
    action="store_true",
    help="Returns the full contents of the M3U8 source.",
)

# *
# * Streamer subparser
# *

_ = streamer.add_argument(
    "-u", "--url", required=True, help="The source of the M3U8 content."
)

_ = streamer.add_argument(
    "-s",
    "--stream",
    action="store_true",
    help="Streams the M3U8 playlist via HTTP.",
)

_ = streamer.add_argument(
    "-sL",
    "--stream-local",
    action="store_true",
    help="Streams local M3U8 playlist via HTTP.",
)

# *
# * Downloader subparser
# *

_ = downloader.add_argument(
    "-u", "--url", required=True, help="The source of the M3U8 content."
)

_ = downloader.add_argument(
    "-d",
    "--download",
    action="store_true",
    help="Downloads the selected M3U8 playlist (Only downloads the playlist.)",
)


def parse_stream_segments(url: str, local: bool = False):
    if not local:
        m3u8_parser = M3u8Streamer(source=url, headers={"": ""})
        m3u8_parser.stream()
    else:
        streamer = LocalM3u8Streamer(source=url)
        streamer.stream()


def parse_download(url: str, headers: str):
    playlist = M3u8Parser(source=url, headers=headers)
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
    stream: bool | None = None
    stream_local: bool | None = None
    download: bool | None = None

    headers: str = ""
    command: str = ""


if __name__ == "__main__":
    args = parser.parse_args(namespace=Args())

    if args.command == "parse":
        m3u8 = M3u8Parser(source=args.url, headers=args.headers)
        _ = m3u8.parse()

        if args.is_master:
            print(m3u8.is_master())

        elif args.list_streams:
            streams = m3u8.get_streams()

            for stream in streams:
                print(f"Stream Link: {stream.get('M3U8-LINK')}")
                print(f"Resolution: {stream.get('RESOLUTION')}\n")

        elif args.list_contents:
            print(m3u8.get_content())

    elif args.stream:
        parse_stream_segments(args.url)

    elif args.stream_local:
        parse_stream_segments(args.url, local=True)

    elif args.download:
        parse_download(args.url)
