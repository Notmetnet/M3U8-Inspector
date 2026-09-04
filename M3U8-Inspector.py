import argparse
import json
import sys
from contextlib import redirect_stdout

from modules.M3u8Downloader import M3u8Downloader
from modules.M3u8Parser import M3u8Parser
from modules.M3u8Streamer import LocalM3u8Streamer, M3u8Streamer

parser = argparse.ArgumentParser(
    description="Extract and parse M3U8 files and links made easier."
)

_ = parser.add_argument(
    "-H", "--headers", type=json.loads, default={}, help="HTTP headers as JSON."
)

_ = parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    default=False,
    help="Enables verbose logging.",
)

_ = parser.add_argument(
    "--stdio", action="store_true", help="Communicate using JSON over stdin/stdout."
)

subparsers = parser.add_subparsers(dest="command")

m3u8_parser = subparsers.add_parser("parse", help="Parse M3U8 sources.")
downloader = subparsers.add_parser("download", help="Download M3U8 sources.")
streamer = subparsers.add_parser("stream", help="Stream M3U8 sources.")

# *
# * M3U8 Parser subparser
# *

_ = m3u8_parser.add_argument(
    "-u", "--url", required=True, help="The source of the M3U8 content."
)

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
    "-o",
    "--output",
    default="./downloaded",
    help="Output of the downloaded M3U8 video.",
)

_ = downloader.add_argument("-mW", "--max-workers", default=5, type=int)

_ = downloader.add_argument("-r", "--rate-limit", default=1, type=int)


class Args(argparse.Namespace):
    is_master: bool | None = None
    url: str = ""
    list_streams: bool | None = None
    list_contents: bool | None = None
    stream: bool | None = None
    stream_local: bool | None = None
    download: bool | None = None
    max_workers: int = 5
    rate_limit: int = 1

    headers: dict[str, str] = {}
    command: str = ""
    verbose: bool = False
    output: str = ""
    stdio: bool = False


def handle_request(request: dict):
    command = request.get("command")

    headers = request.get("headers", {})
    verbose = request.get("verbose", False)

    if command == "parse":
        url = request["url"]
        operation = request.get("operation", "inspect")

        m3u8 = M3u8Parser(
            source=url,
            headers=headers,
        )

        m3u8.parse()

        if operation == "is_master":
            return {"is_master": m3u8.is_master()}

        if operation == "list_streams":
            return {"streams": m3u8.get_streams()}

        if operation == "list_contents":
            return {"content": m3u8.get_content()}

        # Useful default for the GUI
        return {
            "is_master": m3u8.is_master(),
            "streams": m3u8.get_streams(),
            "segments": m3u8.get_segments(),
            "timestamps": m3u8.get_timestamps(),
        }

    elif command == "download":
        url = request["url"]
        output = request.get("output", "./downloaded")
        max_workers = request.get("max_workers", 5)
        rate_limit = request.get("rate_limit", 1)

        m3u8 = M3u8Parser(
            source=url,
            headers=headers,
        )

        m3u8.parse()

        if m3u8.is_master():
            raise ValueError("M3U8 source cannot be a master playlist.")

        M3u8Downloader(
            segments=m3u8.get_segments(),
            timestamps=m3u8.get_timestamps(),
            headers=headers,
            output=output,
        ).download_segments(
            max_workers=max_workers,
            timeout=rate_limit,
        )

        return {"output": output}

    else:
        raise ValueError(f"Unknown command: {command}")


def run_stdio():
    for line in sys.stdin:
        line = line.strip()

        if not line:
            continue

        request_id = None

        try:
            request = json.loads(line)

            request_id = request.get("id")

            # Redirect existing print() calls from your modules
            # to stderr so they don't corrupt the JSON protocol.
            with redirect_stdout(sys.stderr):
                data = handle_request(request)

            response = {
                "id": request_id,
                "success": True,
                "data": data,
            }

        except Exception as error:
            response = {
                "id": request_id,
                "success": False,
                "error": str(error),
            }

        print(
            json.dumps(response),
            flush=True,
        )


def run_cli(args: Args):
    if args.command == "parse":
        m3u8 = M3u8Parser(
            source=args.url,
            headers=args.headers,
        )

        m3u8.parse()

        if args.is_master:
            print(m3u8.is_master())

        elif args.list_streams:
            streams = m3u8.get_streams()

            for stream in streams:
                print(f"Stream Link: {stream.get('M3U8-LINK')}")
                print(f"Resolution: {stream.get('RESOLUTION')}\n")

        elif args.list_contents:
            print(m3u8.get_content())
    elif args.command == "stream":
        if args.stream:
            m3u8 = M3u8Parser(source=args.url, headers=args.headers)
            _ = m3u8.parse()

            Streamer = M3u8Streamer(
                source=args.url, headers=args.headers, verbose=args.verbose
            )
            Streamer.stream()

        elif args.stream_local:
            _ = LocalM3u8Streamer(source=args.url, verbose=args.verbose).stream()

    elif args.command == "download":
        m3u8 = M3u8Parser(source=args.url, headers=args.headers)
        _ = m3u8.parse()

        if m3u8.is_master():
            print("M3U8 source cannot be a master playlist.")

        _ = M3u8Downloader(
            segments=m3u8.get_segments(),
            timestamps=m3u8.get_timestamps(),
            headers=args.headers,
            output=args.output,
        ).download_segments(max_workers=args.max_workers, timeout=args.rate_limit)


if __name__ == "__main__":
    args = parser.parse_args(namespace=Args())

    if args.stdio:
        run_stdio()
    else:
        run_cli(args)
