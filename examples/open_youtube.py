# name: Open YouTube
# description: Opens the YouTube app.
# permissions: open_app
# category: General

def main():
    arise.progress(30, "opening YouTube")
    result = arise.open_app("youtube")
    arise.progress(100, "done")
    return result


def test_runs():
    assert main() is not None
