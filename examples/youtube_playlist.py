# name: Play my YouTube playlist
# description: Opens your YouTube playlist (change PLAYLIST_ID to yours).
# permissions: open_url
# category: General

PLAYLIST_ID = "PLxxxxxxxxxxxxxxxx"   # the part after list= in your playlist link


def build_url(playlist_id):
    return "https://www.youtube.com/playlist?list=" + playlist_id


def main():
    arise.progress(40, "opening playlist")
    arise.open_url(build_url(PLAYLIST_ID))
    arise.progress(100, "done")
    return "Playlist opened"


def test_url():
    assert build_url("ABC").endswith("list=ABC")
