from pathlib import Path
# from ..config.settings import GIT_REPO_PATH, GIT_REPO_FOR_ARGOCD_OBJECTS
import subprocess

GIT_REPO_PATH = Path(__file__).resolve().parents[3] / "git-repos" 

class GitActions:

    def __init__(self, git_repo_to_clone):
        self.git_repo_path = GIT_REPO_PATH
        self.git_repo_to_clone = git_repo_to_clone
        self.git_repo_for_argo = self.git_repo_path / "argocd-registry"

        print(f"[GitActions] git_repo_path     = {self.git_repo_path}")
        print(f"[GitActions] git_repo_for_argo = {self.git_repo_for_argo}")
        print(f"[GitActions] git_repo_to_clone = {self.git_repo_to_clone}")




    def directory_exists(self) -> bool:
        """
        Checks whether the Git repository directory exists.
        """
        if not self.git_repo_for_argo.exists():
            print(
                f"Error: directory does not exist: "
                f"{self.git_repo_for_argo}"
            )
            return False

        if not self.git_repo_for_argo.is_dir():
            print(
                f"Error: path exists but is not a directory: "
                f"{self.git_repo_for_argo}"
            )
            return False

        if not (self.git_repo_for_argo / ".git").exists():
            print(
                f"Error: directory exists but is not a Git repository: "
                f"{self.git_repo_for_argo}"
            )
            return False

        print(f"[directory_exists] OK -> {self.git_repo_for_argo}")
        return True



    def get_current_branch(self) -> str | None:
        """
        Returns the current branch name of the Git repository.
        If the path is not a Git repository, returns None.
        """

        # FIX: this condition was inverted (`if self.directory_exists(): return None`),
        # which returned None exactly when the repo DID exist, and otherwise fell
        # through into subprocess.run() with a cwd that doesn't exist.
        if not self.directory_exists():
            print("[get_current_branch] repo does not exist, returning None")
            return None

        try:
            print(f"$ git rev-parse --abbrev-ref HEAD   (cwd={self.git_repo_for_argo})")
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.git_repo_for_argo,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"  stdout: {result.stdout.strip()}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error getting current Git branch: {e}")
            print(f"  stderr: {e.stderr}")
            return None

    def clone_or_update(self, target_revision: str = "main") -> str|None:
        """
        Clones the specified Git repository to the git_repo_path.
        If the repository already exists, it will be updated to the target revision.
        Returns True if successful, False otherwise.
        """

        print(f"[clone_or_update] target_revision={target_revision}")

        # Make sure the parent folder exists before we try to clone into it.
        self.git_repo_path.mkdir(parents=True, exist_ok=True)

        if self.git_repo_for_argo.exists():
            # If the directory exists, check if it's a Git repository
            if self.directory_exists():
                # Pull the latest changes
                try:
                    print(f"$ git fetch   (cwd={self.git_repo_for_argo})")
                    r = subprocess.run(
                        ["git", "fetch"],
                        cwd=self.git_repo_for_argo,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    print(f"  stdout: {r.stdout.strip()}  stderr: {r.stderr.strip()}")

                    print(f"$ git checkout {target_revision}   (cwd={self.git_repo_for_argo})")
                    r = subprocess.run(
                        ["git", "checkout", target_revision],
                        cwd=self.git_repo_for_argo,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    print(f"  stdout: {r.stdout.strip()}  stderr: {r.stderr.strip()}")

                    print(f"$ git pull   (cwd={self.git_repo_for_argo})")
                    r = subprocess.run(
                        ["git", "pull"],
                        cwd=self.git_repo_for_argo,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    print(f"  stdout: {r.stdout.strip()}  stderr: {r.stderr.strip()}")

                    print(f"[clone_or_update] Repository updated to {target_revision}.")
                    return f"Repository updated to {target_revision}."
                except subprocess.CalledProcessError as e:
                    print(f"Error updating Git repository: {e}")
                    print(f"  stderr: {e.stderr}")
                    return None
            else:
                print(f"Directory {self.git_repo_path} exists but is not a Git repository.")
                return None
        else:
            # Clone the repository
            try:
                # FIX: clone destination was self.git_repo_path (the parent
                # "git-repos" folder), while directory_exists()/every other
                # method checks self.git_repo_for_argo ("git-repos/argocd-registry").
                # Those two never matched, so right after a "successful" clone,
                # directory_exists() still reported False. Cloning into
                # git_repo_for_argo now, so the two paths agree.
                print(
                    f"$ git clone -b {target_revision} {self.git_repo_to_clone} "
                    f"{self.git_repo_for_argo}"
                )
                r = subprocess.run(
                    ["git", "clone", "-b", target_revision, self.git_repo_to_clone, str(self.git_repo_for_argo)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"  stdout: {r.stdout.strip()}  stderr: {r.stderr.strip()}")
                print(f"[clone_or_update] Repository {self.git_repo_to_clone} cloned to {self.git_repo_for_argo}.")
                return f"Repository {self.git_repo_to_clone} cloned to {self.git_repo_for_argo}."
            except subprocess.CalledProcessError as e:
                print(f"Error cloning Git repository: {e}")
                print(f"  stderr: {e.stderr}")
                return None

    def checkout_branch(self, branch_name: str) -> bool:
        """
        Creates and checks out a new Git branch.

        Returns:
            True if the branch was created and checked out successfully.
            False if the operation failed.
        """

        print(f"[checkout_branch] branch_name={branch_name}")

        if not self.directory_exists():
            print(
                f"Git repository directory does not exist: "
                f"{self.git_repo_path}"
            )
            return False

        try:
            # FIX: `git checkout -b` only ever creates a NEW branch. If this
            # branch was already created by an earlier run for the same
            # tenant/app (exactly what happened in your logs), `-b` fails
            # with "a branch named ... already exists" and nothing switches
            # branch at all — you're left on whatever branch you were on
            # before (main), and the push-guard then correctly refuses it.
            # So: check first whether the branch already exists, and if so
            # just check it out normally instead of trying to create it again.
            print(f"$ git rev-parse --verify --quiet {branch_name}   (cwd={self.git_repo_for_argo})")
            exists_check = subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", branch_name],
                cwd=self.git_repo_for_argo,
                capture_output=True,
                text=True,
            )
            print(f"  exit code: {exists_check.returncode}")

            if exists_check.returncode == 0:
                print(f"[checkout_branch] branch '{branch_name}' already exists — checking it out instead of creating it")
                git_checkout_args = ["checkout", branch_name]
            else:
                git_checkout_args = ["checkout", "-b", branch_name]

            print(f"$ git {' '.join(git_checkout_args)}   (cwd={self.git_repo_for_argo})")
            result = subprocess.run(
                ["git", *git_checkout_args],
                cwd=self.git_repo_for_argo,
                capture_output=True,
                text=True,
            )

            print(f"  exit code: {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")

            if result.returncode != 0:
                print(
                    f"Error checking out branch '{branch_name}'."
                )

                print("Git stdout:")
                print(result.stdout)

                print("Git stderr:")
                print(result.stderr)

                return False

            print(
                f"Successfully created and checked out branch "
                f"'{branch_name}'."
            )

            return True

        except OSError as e:
            print(f"Failed to execute Git: {e}")
            return False

    # def git_add_commit_push(self, commit_message: str) -> bool:
    #     """
    #     Stages all changes, commits them with the provided message,
    #     and pushes to the current branch.
    #     Returns True if successful, False otherwise.
    #     """
    #
    #     if not self.directory_exists():
    #         print(f"Directory {self.git_repo_path} is not a Git repository.")
    #         return False
    #
    #     if self.get_current_branch() == "main":
    #         print("Warning: You are on the 'main' branch. It's recommended to work on a feature branch.")
    #         return False
    #     try:
    #         subprocess.run(
    #             ["git", "add", "."],
    #             cwd=self.git_repo_path,
    #             capture_output=True,
    #             text=True,
    #             check=True
    #         )
    #         subprocess.run(
    #             ["git", "commit", "-m", commit_message],
    #             cwd=self.git_repo_path,
    #             capture_output=True,
    #             text=True,
    #             check=True
    #         )
    #         subprocess.run(
    #             ["git", "push"],
    #             cwd=self.git_repo_path,
    #             capture_output=True,
    #             text=True,
    #             check=True
    #         )
    #         return True
    #     except subprocess.CalledProcessError as e:
    #         print(f"Error during git add/commit/push: {e}")
    #         return False
    #
    #
    #
    # def delete_repo_localy(self) -> bool:
    #     """1
    #     Deletes the local Git repository directory.
    #     Returns True if successful, False otherwise.
    #     """
    #     if self.git_repo_path.exists():
    #         try:
    #             subprocess.run(
    #                 ["rm", "-rf", str(self.git_repo_path)],
    #                 capture_output=True,
    #                 text=True,
    #                 check=True
    #             )
    #             return True
    #         except subprocess.CalledProcessError as e:
    #             print(f"Error deleting Git repository: {e}")
    #             return False
    #     else:
    #         print(f"Directory {self.git_repo_path} does not exist.")
    #         return False
    def git_add_commit_push(self, commit_message: str) -> bool:
        """
        Stages all changes, commits them, and pushes the current branch.
        """

        print(f"[git_add_commit_push] commit_message={commit_message!r}")

        if not self.directory_exists():
            print(
                f"Directory {self.git_repo_path} "
                f"is not a Git repository."

            )
            return False

        current_branch = self.get_current_branch()
        print(f"[git_add_commit_push] current_branch={current_branch}")

        if current_branch == "main" or current_branch == "master":
            print("Refusing to push directly to main.")
            return False

        try:
            # git add .
            print(f"$ git add .   (cwd={self.git_repo_for_argo})")
            result = subprocess.run(
                ["git", "add", "."],
                cwd=self.git_repo_for_argo,
                capture_output=True,
                text=True,
            )
            print(f"  exit code: {result.returncode}  stdout: {result.stdout}  stderr: {result.stderr}")

            if result.returncode != 0:
                print("Git add failed:")
                print(result.stderr)
                return False

            # Check whether there are changes to commit
            print(f"$ git status --porcelain   (cwd={self.git_repo_for_argo})")
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.git_repo_for_argo,
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"  stdout: {result.stdout}")

            if not result.stdout.strip():
                print("No changes to commit.")
                return False

            # git commit
            print(f"$ git commit -m {commit_message!r}   (cwd={self.git_repo_for_argo})")
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.git_repo_for_argo,
                capture_output=True,
                text=True,
            )
            print(f"  exit code: {result.returncode}")

            if result.returncode != 0:
                print("Git commit failed:")
                print("STDOUT:")
                print(result.stdout)
                print("STDERR:")
                print(result.stderr)
                return False

            # git push
            print(f"$ git push -u origin {current_branch}   (cwd={self.git_repo_for_argo})")
            result = subprocess.run(
                ["git", "push", "-u", "origin", current_branch],
                cwd=self.git_repo_for_argo,
                capture_output=True,
                text=True,
            )
            print(self.git_repo_path , "**********************")
            print(f"  exit code: {result.returncode}")
            if result.returncode != 0:
                print("Git push failed:")
                print("STDOUT:")
                print(result.stdout)
                print("STDERR:")
                print(result.stderr)
                return False

            print(f"Successfully pushed branch '{current_branch}'.")
            return True

        except OSError as e:
            print(f"Failed to execute Git command: {e}")
            return False

# git = GitActions(git_repo_to_clone="https://github.com/bezalelshteren/argocd-registry.git"
# )
# m = git.clone_or_update()
# print(m)
# git.checkout_branch("automation/demo-branch")
# v = git.get_current_branch()
# print(v)
# c = git.git_add_commit_push("frhu")
# print(c)