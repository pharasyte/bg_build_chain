import subprocess

def build_commit():

    # Call git add "git add ."
    result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
    print(result.stdout)
    
    # Call git commit "git commit -a "build""
    result = subprocess.run(['git', 'commit', '-a', '-m', 'build'], capture_output=True, text=True)
    print(result.stdout)
    

def is_file_changed(file):
    """
    Checks if a file has changes compared to the most recent commit.
    
    Args:
    file (str): The file path to check.
    
    Returns:
    bool: True if the file has changes, False otherwise.
    """
    result = subprocess.run(['git', 'diff', '--name-only', file], capture_output=True, text=True)
    return bool(result.stdout.strip())

def commit_files(files, commit_message):
    """
    Stages specific files and commits them with the provided commit message
    only if they have changes compared to the most recent commit.
    
    Args:
    files (list of str): List of file paths to stage.
    commit_message (str): The commit message.
    """
    
    if isinstance(files, str):
        files = [files]

    changed_files = [file for file in files if is_file_changed(file)]
    
    if not changed_files:
        print("No changes detected in the specified files. No commit will be made.")
        return
    
    try:
        # Stage and commit the changed files
        for file in changed_files:
            subprocess.run(['git', 'add', file], check=True)

        subprocess.run(['git', 'commit', '-m', commit_message], check=True)

        print("Files committed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

# Example usage
files_to_commit = ['file1.txt', 'file2.py']
commit_files(files_to_commit, 'Committing specific files')
