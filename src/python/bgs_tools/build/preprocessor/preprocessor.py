from bgs_tools.build.preprocessor.parser import get_parser

RED = '\033[1;31m'
RESET = '\033[0;0m'

def preprocess_file(file, output_dir = None):
    """
    Preprocess a single file.
    """
    parser = get_parser()
    print(f"{RED}Preprocessing {file} to {output_dir}{RESET}")

    with open(file, 'r') as f:
        data = f.read()
    
    parser.parse(data)

    return parser.results

    