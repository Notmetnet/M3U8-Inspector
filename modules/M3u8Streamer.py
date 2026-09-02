import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import requests

HLS_URL = "https://cdn.jsdelivr.net/npm/hls.js@latest"


class M3u8StreamPage:
    def __init__(self):
        self.title: str = "M3u8 Streamer"
        self.script_inject: str = ""
        self.HTML: str = f"""<!doctype html>
<html>
<head><title>{self.title}</title></head>
<body>
<video id="video" controls autoplay style="width:100%;max-width:900px"></video>
{self.load_hls_source()}
<script>{self.script_inject}</script>
<script>
const video = document.getElementById("video");
if (Hls.isSupported()) {{
const hls = new Hls();
hls.loadSource("/playlist.m3u8");
hls.attachMedia(video);
}} else if (video.canPlayType("application/vnd.apple.mpegurl")) {{
video.src = "/playlist.m3u8";
}}
</script>
</body>
</html>"""

    def load_hls_source(self) -> str:
        hls_source = os.path.join("modules", "hls.js")
        if os.path.exists(hls_source):
            with open(hls_source, "r") as fh:
                hls_script = fh.read()

            return f"<script>{hls_script}</script>"
        else:
            return f"<script src='{HLS_URL}'></script>"


class M3u8Streamer:
    def __init__(self, source: str, headers: dict[str, str], verbose: bool = False):
        self.source: str = source
        self.headers: dict[str, str] = headers
        self.verbose: bool = verbose

    class HTTPRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            if self.server.verbose:
                super().log_message(format, *args)

        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            if parsed.path == "/":
                return self._serve_index()

            if parsed.path == "/playlist.m3u8":
                upstream_url = query.get("url", [self.server.upstream_url])[0]
                return self._serve_playlist(upstream_url)

            if parsed.path == "/segment":
                segment_url = query.get("url", [None])[0]
                if not segment_url:
                    self.send_error(400, "Missing segment url")
                    return
                return self._proxy_binary(unquote(segment_url))

            self.send_error(404)

        def _serve_index(self):
            index_html = Path(__file__).resolve().parent.parent / "index.html"

            if index_html.exists():
                html = index_html.read_text(encoding="utf-8")
            else:
                html = M3u8StreamPage().HTML

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            _ = self.wfile.write(html.encode("utf-8"))

        def _serve_playlist(self, upstream_url: str):
            resp = requests.get(
                upstream_url,
                headers=self.server.upstream_headers,
                timeout=30,
            )
            resp.raise_for_status()

            rewritten_lines: list[str] = []
            for line in resp.text.splitlines():
                if line and not line.startswith("#"):
                    absolute_url = urljoin(upstream_url, line)
                    proxy_url = f"/segment?url={quote(absolute_url, safe='')}"
                    if absolute_url.endswith(".m3u8"):
                        proxy_url = f"/playlist.m3u8?url={quote(absolute_url, safe='')}"
                    rewritten_lines.append(proxy_url)
                else:
                    rewritten_lines.append(line)

            body = "\n".join(rewritten_lines) + "\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            _ = self.wfile.write(body.encode("utf-8"))

        def _proxy_binary(self, upstream_url: str):
            resp = requests.get(
                upstream_url,
                headers=self.server.upstream_headers,
                stream=True,
                timeout=30,
            )

            self.send_response(resp.status_code)
            self.send_header(
                "Content-Type",
                resp.headers.get("Content-Type", "video/MP2T"),
            )
            self.end_headers()

            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    _ = self.wfile.write(chunk)

    def stream(self):
        server_address = ("", 8989)

        if not is_hls_source_downloaded():
            _download_hls_source()

        httpd = ThreadingHTTPServer(
            server_address,
            self.HTTPRequestHandler,
        )

        httpd.upstream_url = self.source
        httpd.upstream_headers = self.headers
        httpd.verbose = self.verbose

        print("Server running on http://localhost:8989")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()


def is_hls_source_downloaded() -> bool:
    hls_path = os.path.join("modules", "hls.js")
    return os.path.exists(hls_path)


def _download_hls_source():
    response = requests.get("https://cdn.jsdelivr.net/npm/hls.js@latest")
    os.makedirs("modules", exist_ok=True)
    if response.ok:
        with open(os.path.join("modules", "hls.js"), "w") as f:
            _ = f.write(response.text)

class LocalM3u8Streamer:
    def __init__(self, source: Path | str, verbose: bool = False):
        self.source: Path | str = Path(source).resolve()
        self.verbose: bool = verbose

    class HTTPRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            if self.server.verbose:
                super().log_message(format, *args)

        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            if parsed.path == "/":
                return self._serve_index()

            if parsed.path == "/playlist.m3u8":
                playlist = query.get("path", [str(self.server.source)])[0]

                return self._serve_playlist(Path(unquote(playlist)))

            if parsed.path == "/file":
                file_path = query.get("path", [None])[0]

                if not file_path:
                    self.send_error(400, "Missing file path")
                    return

                return self._serve_file(Path(unquote(file_path)))

            self.send_error(400)

        def _serve_index(self):
            html_page = M3u8StreamPage()
            html = html_page.HTML

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            _ = self.wfile.write(html.encode("utf-8"))

        def _serve_playlist(self, playlist_path: Path):
            playlist_path = playlist_path.resolve()

            if not playlist_path.exists():
                self.send_error(404, f"Playlist not found: {playlist_path}")

            try:
                text = playlist_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = playlist_path.read_text(encoding="utf-8", errors="replace")

            playlist_directory = playlist_path.parent
            rewritten_lines: list[str] = []

            for line in text.splitlines():
                stripped = line.strip()

                if stripped and not stripped.startswith("#"):
                    target = (playlist_directory / stripped).resolve()

                    if target.suffix.lower() == ".m3u8":
                        url = "/playlist.m3u8?path=" + quote(str(target), safe="")
                    else:
                        url = "/file?path=" + quote(str(target), safe="")

                    rewritten_lines.append(url)

                else:
                    rewritten_lines.append(line)

            body = "\n".join(rewritten_lines) + "\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.end_headers()

            _ = self.wfile.write(body.encode("utf-8"))

        def _rewrite_tag_uri(self, line: str, playlist_directory: Path) -> str:
            prefix = 'URI="'

            start = line.find(prefix)

            if start == -1:
                return line

            value_start = start + len(prefix)
            value_end = line.find('"', value_start)

            if value_end == -1:
                return line

            original_uri = line[value_start:value_end]

            target = (playlist_directory / original_uri).resolve()

            if target.suffix.lower() == ".m3u8":
                replacement = "/playlist.m3u8?path=" + quote(str(target), safe="")
            else:
                replacement = "/file?path=" + quote(str(target), safe="")

            return line[:value_start] + replacement + line[value_end:]

        def _serve_file(self, file_path: Path):
            file_path = file_path.resolve()

            if not file_path.exists():
                self.send_error(404, f"File not found: {file_path}")
                return

            if not file_path.is_file():
                self.send_error(404)
                return

            content_type = self._get_content_type(file_path)

            file_size = file_path.stat().st_size

            range_header = self.headers.get("Range")

            if range_header:
                return self._serve_range(
                    file_path, content_type, file_size, range_header
                )

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with file_path.open("rb") as file:
                while True:
                    chunk = file.read(1024 * 1024)

                    if not chunk:
                        break

                    try:
                        self.wfile.write(chunk)
                    except BrokenPipeError:
                        break

        def _serve_range(
            self,
            file_path: Path,
            content_type: str,
            file_size: int,
            range_header: str,
        ):
            try:
                byte_range = range_header.replace("bytes=", "", 1)

                start_string, end_string = byte_range.split("-", 1)

                if start_string:
                    start = int(start_string)
                else:
                    start = 0

                if end_string:
                    end = int(end_string)
                else:
                    end = file_size - 1

                end = min(end, file_size - 1)

                if start > end or start >= file_size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return

                length = end - start + 1

            except (ValueError, IndexError):
                self.send_error(400, "Invalid Range header")
                return

            self.send_response(206)
            self.send_header("Content-Type", content_type)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            with file_path.open("rb") as file:
                file.seek(start)

                remaining = length

                while remaining > 0:
                    chunk = file.read(min(1024 * 1024, remaining))

                    if not chunk:
                        break

                    try:
                        self.wfile.write(chunk)
                    except BrokenPipeError:
                        break

                    remaining -= len(chunk)

        def _get_content_type(self, path: Path) -> str:
            extension = path.suffix.lower()

            types = {
                ".m3u8": "application/vnd.apple.mpegurl",
                ".ts": "video/mp2t",
                ".m4s": "video/iso.segment",
                ".mp4": "video/mp4",
                ".aac": "audio/aac",
                ".mp3": "audio/mpeg",
                ".vtt": "text/vtt",
                ".key": "application/octet-stream",
            }

            if extension in types:
                return types[extension]

            guessed, _ = mimetypes.guess_type(path)

            return guessed or "application/octet-stream"

    def stream(self, host: str = "127.0.0.1", port: int = 8989):
        server_address = (host, port)
        if not is_hls_source_downloaded():
            _download_hls_source()

        httpd = ThreadingHTTPServer(server_address, self.HTTPRequestHandler)

        httpd.source = self.source
        httpd.stream_root = self.source.parent
        httpd.verbose = self.verbose

        if self.verbose:
            print(f"Serving M3U8: {self.source}")
            print(f"Stream directory: {self.source.parent}")

        print(f"Streaming on: http://localhost:{port}")

        try:
            httpd.serve_forever()

        except KeyboardInterrupt:
            print("\nStopping server...")

        finally:
            httpd.server_close()
