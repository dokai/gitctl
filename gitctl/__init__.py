import logging
import gitctl.parser

def main():
    """Runs the gitctl functionality."""
    # Set up the logger
    formatter = logging.Formatter('%(message)s')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logging.getLogger('gitctl').addHandler(console)
    logging.getLogger('gitctl').setLevel(logging.INFO)

    args = gitctl.parser.parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
