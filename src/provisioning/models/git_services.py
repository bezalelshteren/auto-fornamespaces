from pathlib import Path
import subprocess

class GitChecking:

    def __init__(self, git_repo_path: Path):
        self.git_repo_path = git_repo_path

    def is_git_repo(self) -> bool:
        """
        Checks whether the specified path is a Git repository.
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_current_branch(self) -> str | None:
        """
        Returns the current branch name of the Git repository.
        If the path is not a Git repository, returns None.
        """

        if not self.is_git_repo():
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error getting current Git branch: {e}")
            return None

    def clone_or_update(self, repo_url: str, target_revision: str = "master") -> bool:
        """
        Clones the specified Git repository to the git_repo_path.
        If the repository already exists, it will be updated to the target revision.
        Returns True if successful, False otherwise.
        """

        if self.git_repo_path.exists():
            # If the directory exists, check if it's a Git repository
            if self.is_git_repo():
                # Pull the latest changes
                try:
                    subprocess.run(
                        ["git", "fetch"],
                        cwd=self.git_repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    subprocess.run(
                        ["git", "checkout", target_revision],
                        cwd=self.git_repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    subprocess.run(
                        ["git", "pull"],
                        cwd=self.git_repo_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"Error updating Git repository: {e}")
                    return False
            else:
                print(f"Directory {self.git_repo_path} exists but is not a Git repository.")
                return False
        else:
            # Clone the repository
            try:
                subprocess.run(
                    ["git", "clone", "-b", target_revision, repo_url, str(self.git_repo_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error cloning Git repository: {e}")
                return False



    def checkout_branch(self, branch_name: str) -> bool:
        """
        Checks out the specified branch in the Git repository.
        Returns True if successful, False otherwise.
        """

        if not self.is_git_repo():
            print(f"Directory {self.git_repo_path} is not a Git repository.")
            return False

        try:
            subprocess.run(
                ["git", "checkout", branch_name],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error checking out branch '{branch_name}': {e}")
            return False

    def git_add_commit_push(self, commit_message: str) -> bool:
        """
        Stages all changes, commits them with the provided message,
        and pushes to the current branch.
        Returns True if successful, False otherwise.
        """

        if not self.is_git_repo():
            print(f"Directory {self.git_repo_path} is not a Git repository.")
            return False

        if self.get_current_branch() == "master":
            print("Warning: You are on the 'master' branch. It's recommended to work on a feature branch.")
            return False
        try:
            subprocess.run(
                ["git", "add", "."],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            subprocess.run(
                ["git", "push"],
                cwd=self.git_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error during git add/commit/push: {e}")
            return False



    def delete_repo_localy(self) -> bool:
        """
        Deletes the local Git repository directory.
        Returns True if successful, False otherwise.
        """

        if self.git_repo_path.exists():
            try:
                import shutil
                shutil.rmtree(self.git_repo_path)
                return True
            except Exception as e:
                print(f"Error deleting local Git repository: {e}")
                return False
        else:
            print(f"Directory {self.git_repo_path} does not exist.")
            return False
