import gitctl.command
import gitctl.handler

def main():
    """Runs the gitctl functionality."""
    args = gitctl.command.parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
