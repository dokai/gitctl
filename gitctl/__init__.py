import sys
import logging
import gitctl.parser

class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level
    def filter(self, record):
        return self.level == record.levelno

def make_handler(outstream, format, level):
    handler = logging.StreamHandler(outstream)
    formatter = logging.Formatter(format)
    handler.setFormatter(formatter)
    handler.addFilter(LevelFilter(level))
    return handler

def main():
    """Runs the gitctl functionality."""
    # Set up the logger
    logging.getLogger('gitctl').setLevel(logging.INFO)
    # Normal message go to stdout
    logging.getLogger('gitctl').addHandler(make_handler(sys.stdout, '%(message)s', logging.INFO))
    # Error messages to stderr
    logging.getLogger('gitctl').addHandler(make_handler(sys.stderr, '%(levelname)s %(message)s', logging.WARN))
    logging.getLogger('gitctl').addHandler(make_handler(sys.stderr, '%(levelname)s %(message)s', logging.CRITICAL))
    logging.getLogger('gitctl').addHandler(make_handler(sys.stderr, '%(levelname)s %(message)s', logging.DEBUG))

    args = gitctl.parser.parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
