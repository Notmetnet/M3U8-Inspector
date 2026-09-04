import os
from pathlib import PurePosixPath
from typing import TypedDict
from urllib.parse import urlparse

import requests

StreamInfo = TypedDict(
    "StreamInfo",
    {"BANDWIDTH": str, "RESOLUTION": str, "NAME": str, "M3U8-LINK": str},
    total=False,
)


class M3u8Parser:
    def __init__(self, source: str, headers: dict[str, str]):
        self.source: str = source
        self.headers: dict[str, str] = headers

        self.__content: str = ""
        self.__lines: list[str] = []
        self.__resolution: str = ""
        self.__is_master: bool = True

        self.__streams: list[StreamInfo] = []
        self.__segments: list[str] = []
        self.__timestamps: list[str] = []

    def parse(self):
        if not is_m3u8_extension(self.source):
            print(f"Invalid source type: {self.source}")

        if os.path.exists(self.source):
            with open(self.source, "r", encoding="utf-8") as fh:
                self.__content = fh.read()
                self.__lines = self.__content.splitlines()

        else:
            response = requests.get(self.source, headers=self.headers)
            self.__content = response.text
            self.__lines = self.__content.splitlines()

        self.parse_lines()

        return self.__content

    def parse_lines(self):
        self.__streams = []
        segments: list[str] = []
        timestamps: list[str] = []

        def parse_stream_inf(line: str, m3u8_stream_url: str) -> StreamInfo:
            attrs = line.split(":", 1)[1]
            parts = attrs.split(",")

            data: StreamInfo = {}
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    data[key] = value.strip('"')

            data["M3U8-LINK"] = m3u8_stream_url
            return data

        for index, line in enumerate(self.__lines):
            if line.startswith("#EXT-X-STREAM-INF:") and index + 1 < len(self.__lines):
                next_line = self.__lines[index + 1].strip()
                info = parse_stream_inf(line, next_line)
                self.__streams.append(info)

            self.__is_master = bool(self.__streams)

            if line.startswith("http"):
                segments.append(line)

            if line.startswith("#EXTINF:"):
                formatted_line = line.split(":", 1)[1].replace(",", "")
                timestamps.append(formatted_line)

        self.__segments = segments
        self.__timestamps = timestamps

    def is_master(self):
        return self.__is_master

    def get_segments(self) -> list[str]:
        return self.__segments

    def get_streams(self) -> list[StreamInfo]:
        return self.__streams

    def get_timestamps(self):
        return self.__timestamps

    def get_content(self) -> str:
        return self.__content


def is_m3u8_extension(url: str):
    path = urlparse(url).path
    suffix = PurePosixPath(path).suffix
    return suffix == ".m3u8"


def build_m3u8_playlist(
    timestamps: list[str], segments: list[str], output_path: str = "./playlist.m3u8"
):
    base_build = """
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-TARGETDURATION:20
"""

    if len(timestamps) != len(segments):
        raise ValueError("Timestamps and segments should have the same length")

    with open(output_path, "w") as fh:
        _ = fh.write(base_build)
        for i in range(len(timestamps)):
            fh.writelines("#EXTINF:" + str(timestamps[i]) + "," + "\n")
            fh.writelines(segments[i] + "\n")
        _ = fh.write("#EXT-X-ENDLIST")
