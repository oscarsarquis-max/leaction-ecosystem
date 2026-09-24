import sys

from app.admin.configure import main as configure_main
from app.admin.issue_activation import main as issue_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "issue-activation":
        issue_main(sys.argv[2:])
    else:
        configure_main()
