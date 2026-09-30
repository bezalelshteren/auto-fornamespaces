from pathlib import Path
import re
import subprocess


_HINTS = [
    (
        ("not found in upstream", "couldn't find remote ref",
         "did not match any file", "unknown revision",
         "ambiguous argument 'head'"),
        "The branch does not exist. If the REMOTE repo is empty (no commits "
        "yet) create an initial commit on it first: "
        "git checkout -b main ; add a file ; git commit ; git push -u origin main. "
        "Otherwise check the branch name.",
    ),
    (
        ("no tracking information", "no upstream"),
        "The local branch is not linked to a remote branch. "
        "Run: git push -u origin <branch> (or make sure the remote branch exists).",
    ),
    (
        ("repository not found", "does not appear to be a git repository"),
        "Check the repo URL: it must be a FULL url (https://... or git@...), "
        "with no spaces or newlines, and you need access to the repo.",
    ),
    (
        ("could not resolve host", "unable to access"),
        "Network problem (VPN / proxy / DNS) or a wrong host in the URL.",
    ),
    (
        ("authentication failed", "could not read username",
         "terminal prompts disabled", "permission denied"),
        "Credentials problem. The process running the server has no usable "
        "login for this repo (token / SSH key / credential manager).",
    ),
    (
        ("tell me who you are", "empty ident", "unable to auto-detect email"),
        "Git has no identity configured. Run: git config --global user.name "
        "\"Name\" ; git config --global user.email \"mail@example.com\"",
    ),
    (
        ("non-fast-forward", "fetch first", "[rejected]"),
        "The remote branch has commits you don't have locally. Pull/rebase first.",
    ),
    (
        ("would be overwritten", "please commit your changes or stash"),
        "There are uncommitted local changes blocking this operation.",
    ),
    (
        ("dubious ownership",),
        "Git refuses a folder owned by another user. "
        "Run: git config --global --add safe.directory <path>",
    ),
    (
        ("already exists and is not an empty directory",),
        "The target folder already exists and is not empty. Delete or rename it.",
    ),
]


def _mask(text: str) -> str:
    """Hide credentials embedded in URLs (https://user:token@host -> https://***@host)."""
    return re.sub(r"://[^/@\s]+@", "://***@", text)


def _hint_for(message: str) -> str | None:
    lowered = message.lower()
    for keywords, hint in _HINTS:
        if any(k in lowered for k in keywords):
            return hint
    return None


def _fail(where: str, cmd, stderr: str = "", stdout: str = "") -> None:
    """Print a failure: the command, git's own message, and a hint if we know one."""
    print(f"[{where}] FAILED: {_mask(' '.join(str(c) for c in cmd))}")

    detail = _mask((stderr or stdout or "").strip())
    for line in detail.splitlines():
        print(f"    {line}")

    hint = _hint_for(detail)
    if hint:
        print(f"    -> {hint}")


def _run_git(args: list[str], cwd=None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command, printing the command first. Output is captured, not printed."""
    print(f"$ {_mask('git ' + ' '.join(args))}")
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _git_missing(where: str, error: OSError) -> None:
    print(
        f"[{where}] FAILED to start git: {error}\n"
        f"    -> Is git installed and on the PATH of the process running the server? "
        f"(Restart the server after changing PATH.)"
    )


class GitActions:

    def __init__(self, git_repo_to_clone, git_repo_to_do_actions: Path):
        # strip(): a stray "\n" in the URL (e.g. from a multi-line string in
        # settings) makes git treat it as a bad path.
        self.git_repo_to_clone = str(git_repo_to_clone).strip()
        self.git_repo_to_do_actions = Path(git_repo_to_do_actions)

        print(
            f"[GitActions] clone_url={_mask(self.git_repo_to_clone)}  "
            f"local_repo={self.git_repo_to_do_actions}"
        )

    def directory_exists(self) -> bool:
        """
        Checks whether the Git repository directory exists.
        Prints only when something is wrong.
        """
        repo = self.git_repo_to_do_actions

        if not repo.exists():
            print(f"[directory_exists] FAILED: directory does not exist: {repo}")
            return False

        if not repo.is_dir():
            print(f"[directory_exists] FAILED: path exists but is not a directory: {repo}")
            return False

        if not (repo / ".git").exists():
            print(
                f"[directory_exists] FAILED: directory exists but is not a Git "
                f"repository (no .git inside): {repo}\n"
                f"    -> If it only holds leftovers from a failed run, delete it "
                f"and let clone_or_update clone it again."
            )
            return False

        return True

    def get_current_branch(self) -> str | None:
        """
        Returns the current branch name of the Git repository.
        If the path is not a Git repository (or has no commits yet), returns None.
        """

        if not self.directory_exists():
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.git_repo_to_do_actions,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            _fail("get_current_branch", e.cmd, e.stderr, e.stdout)
            return None
        except OSError as e:
            _git_missing("get_current_branch", e)
            return None

    def clone_or_update(self, target_revision: str = "main") -> str | None:
        """
        Clones the specified Git repository to git_repo_to_do_actions.
        If the repository already exists, it is updated to the target revision.
        Returns a status message if successful, None otherwise.
        """

        print(f"[clone_or_update] target_revision={target_revision}")

        repo = self.git_repo_to_do_actions

        try:
            if repo.exists():
                # directory_exists() already explains what is wrong
                if not self.directory_exists():
                    return None

                # Update an existing clone
                _run_git(["fetch"], cwd=repo)
                _run_git(["checkout", target_revision], cwd=repo)
                _run_git(["pull"], cwd=repo)

                message = f"Repository updated to {target_revision}."
                print(f"[clone_or_update] OK: {message}")
                return message

            # Clone the repository.
            # Clone into git_repo_to_do_actions (not its parent), so that
            # directory_exists() and every other method agree on the location.
            # No cwd here: the folder does not exist yet.
            _run_git(["clone", "-b", target_revision, self.git_repo_to_clone, str(repo)])

            message = f"Repository cloned to {repo}."
            print(f"[clone_or_update] OK: {message}")
            return message

        except subprocess.CalledProcessError as e:
            _fail("clone_or_update", e.cmd, e.stderr, e.stdout)
            return None
        except OSError as e:
            _git_missing("clone_or_update", e)
            return None

    def checkout_branch(self, branch_name: str) -> bool:
        """
        Creates and checks out a Git branch (or just checks it out if it
        already exists from an earlier run).

        Returns:
            True if the branch is checked out.
            False if the operation failed.
        """

        print(f"[checkout_branch] branch_name={branch_name}")

        if not self.directory_exists():
            return False

        repo = self.git_repo_to_do_actions

        try:
            # `git checkout -b` only creates NEW branches. If an earlier run for
            # the same tenant/app already created it, -b fails, so check first.
            # (Silent probe - its exit code is the answer, nothing to print.)
            branch_exists = subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", branch_name],
                cwd=repo,
                capture_output=True,
                text=True,
            ).returncode == 0

            if branch_exists:
                git_checkout_args = ["checkout", branch_name]
            else:
                git_checkout_args = ["checkout", "-b", branch_name]

            result = _run_git(git_checkout_args, cwd=repo, check=False)

            if result.returncode != 0:
                _fail("checkout_branch", ["git", *git_checkout_args], result.stderr, result.stdout)
                return False

            state = "already existed, checked out" if branch_exists else "created and checked out"
            print(f"[checkout_branch] OK: branch '{branch_name}' {state}.")
            return True

        except OSError as e:
            _git_missing("checkout_branch", e)
            return False

    def git_add_commit_push(self, commit_message: str) -> bool:
        """
        Stages all changes, commits them, and pushes the current branch.
        Returns True only if something was actually pushed.
        """

        print(f"[git_add_commit_push] commit_message={commit_message!r}")

        if not self.directory_exists():
            return False

        repo = self.git_repo_to_do_actions

        current_branch = self.get_current_branch()

        # Without this guard the code would run "git push -u origin None".
        if current_branch is None or current_branch == "HEAD":
            print(
                "[git_add_commit_push] FAILED: could not determine the current "
                "branch (repo without commits, or detached HEAD). Nothing was pushed."
            )
            return False

        if current_branch == "main" or current_branch == "master":
            print(f"[git_add_commit_push] Refusing to push directly to '{current_branch}'.")
            return False

        try:
            # git add .
            result = _run_git(["add", "."], cwd=repo, check=False)
            if result.returncode != 0:
                _fail("git_add_commit_push", ["git", "add", "."], result.stderr, result.stdout)
                return False

            # Check whether there are changes to commit
            result = _run_git(["status", "--porcelain"], cwd=repo, check=False)
            if result.returncode != 0:
                _fail("git_add_commit_push", ["git", "status", "--porcelain"], result.stderr, result.stdout)
                return False

            if not result.stdout.strip():
                print(
                    "[git_add_commit_push] Nothing to commit (files are identical "
                    "to what the branch already has). Nothing was pushed."
                )
                return False

            # git commit
            result = _run_git(["commit", "-m", commit_message], cwd=repo, check=False)
            if result.returncode != 0:
                _fail("git_add_commit_push", ["git", "commit", "-m", commit_message], result.stderr, result.stdout)
                return False

            # git push
            push_args = ["push", "-u", "origin", current_branch]
            result = _run_git(push_args, cwd=repo, check=False)
            if result.returncode != 0:
                _fail("git_add_commit_push", ["git", *push_args], result.stderr, result.stdout)
                return False

            print(f"[git_add_commit_push] OK: pushed branch '{current_branch}'.")
            return True

        except OSError as e:
            _git_missing("git_add_commit_push", e)
            return False
