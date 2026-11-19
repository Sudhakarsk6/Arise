# name: Open Gmail
# description: Opens the Gmail app.
# permissions: open_app
# category: Productivity

def main():
    return arise.open_app("gmail")


def test_runs():
    assert main() is not None
