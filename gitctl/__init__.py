import gitctl.parser

def main():
    """Runs the gitctl functionality."""
    args = gitctl.parser.parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
