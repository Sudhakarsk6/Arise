# name: Open Spotify
# description: Opens the Spotify app.
# permissions: open_app
# category: General

def main():
    return arise.open_app("spotify")


def test_runs():
    assert main() is not None
