import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

import requests

from modules.M3u8Parser import build_m3u8_playlist


class M3u8Downloader:
    def __init__(
        self,
        timestamps: list[str],
        segments: list[str],
        output: str,
        headers: dict[str, str],
    ):
        self.__timestamps = timestamps
        self.__segments = segments
        self.output: str = output
        self.headers: dict[str, str] = headers
        self.__len = len(self.__segments)

    def download_segments(self, max_workers: int = 5, timeout: int = 1):
        if len(self.__segments) != len(self.__timestamps):
            raise ValueError("Timestamps and segments need to have the same length")

        def download_one(i: int, segment: str):
            sleep(timeout)
            response = requests.get(segment, headers=self.headers)
            print(f"Downloading {segment}")
            os.makedirs(self.output, exist_ok=True)

            try:
                segment_name = f"seg_{i:06d}.ts"
                output_file = os.path.join(self.output, segment_name)

                with open(output_file, "wb") as fh:
                    _ = fh.write(response.content)

            except Exception as e:
                print(e)

        with ThreadPoolExecutor(max_workers) as executor:
            futures = [
                executor.submit(download_one, i, segment)
                for i, segment in enumerate(self.__segments)
            ]
            for future in as_completed(futures):
                future.result()

        local_segments = [f"seg_{i:06d}.ts" for i in range(len(self.__segments))]
        playlist_path = os.path.join(self.output, "playlist.m3u8")
        build_m3u8_playlist(
            self.__timestamps, local_segments, output_path=playlist_path
        )
        return playlist_path
