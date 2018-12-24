#!/usr/bin/python

import git
from git import *
import threading
import os
import sys
import getopt
from enum import Enum


class GitCommandType(Enum):
    pull = 1
    push = 2
    nop = 3


def yes_or_no(msg: str):
    yes_no = input(msg + " ? [Y]es or [n]o?")
    yes_no = yes_no.lower()
    if yes_no == "yes" or yes_no == "y":
        return True
    elif yes_no == "no" or yes_no == "n":
        return False
    else:
        return True


# is_git_dir returns if current directory has .git/
def is_git_dir(dir_path: str):
    repo_git_dir = os.path.join(dir_path, '.git')
    if not os.path.exists(repo_git_dir):
        return False
    return True


def update_git_repo(git_cmd_type: GitCommandType, git_repo_dir: str, git_stash_if_have_uncommitted_changes: bool,
                    unhandled_git_repo_dirs: list):
    try:
        git_repo = git.Repo(git_repo_dir)
        if git_cmd_type == GitCommandType.pull and git_repo.is_dirty():
            if not git_stash_if_have_uncommitted_changes:
                if not yes_or_no("Repo " + git_repo_dir + " have uncommitted changes, \n\tgit reset --hard"):
                    unhandled_git_repo_dirs.append(git_repo_dir)
                    return
            try:
                git_repo.git.stash('save', True)
            except Exception as exception:
                print("git stash repo:" + git_repo_dir + " Failed:\r\n git reset --hard recommended\r\n" + str(exception))
                unhandled_git_repo_dirs.append(git_repo_dir)
                return

        remote_repo = git_repo.remote()
        print("start git %s from remote for: %s\r\n" % (git_cmd_type.name, git_repo_dir))
        try:
            if git_cmd_type == GitCommandType.pull:
                remote_repo.pull()
            elif git_cmd_type == GitCommandType.push:
                remote_repo.push()
            elif git_cmd_type == GitCommandType.nop:
                pass
            else:
                raise Exception('unrecognised git command: ' + git_cmd_type.name)

        except Exception as exception:
            print(
                "git " + git_cmd_type.name + " repo:" + git_repo_dir + " Failed:\r\n git reset --hard recommended" + str(
                    exception))
            unhandled_git_repo_dirs.append(git_repo_dir)
            return
        print("Done git %s for %s\r\n" % (git_cmd_type.name, git_repo_dir))
    except NoSuchPathError as e:
        pass
    except InvalidGitRepositoryError as e:
        pass
    finally:
        pass


def update_git_repo_thread(git_cmd_type: GitCommandType, root_path: str, git_stash_if_have_uncommitted_changes: bool,
                           dirty_git_repo_dirs: list,
                           git_update_thread_pools: list):
    if git_stash_if_have_uncommitted_changes:
        git_update_thread_ = threading.Thread(target=update_git_repo,
                                              args=(git_cmd_type, root_path, True, dirty_git_repo_dirs))
        git_update_thread_.start()
        git_update_thread_pools.append(git_update_thread_)
    else:
        update_git_repo(root_path, False, dirty_git_repo_dirs)


def walk_and_update(git_cmd_type: GitCommandType, root_path: str, continue_when_meet_git: bool, depth: int,
                    max_depth: int,
                    git_stash_if_have_uncommitted_changes: bool, dirty_git_repo_dirs: list,
                    git_update_thread_pools: list):
    if depth >= max_depth:
        print("jump for %s too deep: depth[%d] max_depth[%d]\r\n" % (root_path, depth, max_depth))
        return
    if is_git_dir(root_path):
        update_git_repo_thread(git_cmd_type, root_path, git_stash_if_have_uncommitted_changes, dirty_git_repo_dirs,
                               git_update_thread_pools)
        if not continue_when_meet_git:
            # print("jump subdirs for %s meet git\r\n" % (root_path))
            return
    depth = depth + 1
    for root_dir, sub_dirs, sub_files in os.walk(root_path):
        for sub_dir in sub_dirs:
            walk_and_update(git_cmd_type, os.path.join(root_dir, sub_dir), continue_when_meet_git, depth,
                            max_depth, git_stash_if_have_uncommitted_changes, dirty_git_repo_dirs,
                            git_update_thread_pools)
        sub_dirs.clear()
        sub_files.clear()


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            g_git_cmd_type: GitCommandType = GitCommandType.nop
            g_walk_paths: list = ["."]
            g_git_stash_if_have_uncommitted_changes: bool = False
            g_continue_when_meet_git: bool = False
            g_stop_when_meet_max_depth: int = 10
            opts, args = getopt.getopt(argv[1:], "hycd:",
                                       ["help", "path", "git_stash_if_have_uncommitted_changes",
                                        "continue_when_meet_git", "stop_when_meet_max_depth=10"])
            if len(args) > 0:
                g_git_cmd_type = GitCommandType[args[0]]
            if len(args) > 1:
                g_walk_paths = args[1:]
            for op, value in opts:
                if op == "-y":
                    g_git_stash_if_have_uncommitted_changes = True
                if op == "-c":
                    g_continue_when_meet_git = True
                elif op == "-d":
                    g_stop_when_meet_max_depth = value
                elif op == "-h":
                    print("=======\r\n""Usage:\r\n")
                    print("python git_pull_all.py pull|push .\r\n")
                    print("python git_pull_all.py -y -c -d 10 pull|push YourPath\r\n")
                    print("python git_pull_all.py"
                          " --git_stash_if_have_uncommitted_changes "
                          "--continue_when_meet_git "
                          "--stop_when_meet_max_depth=10 pull|push YourPath")
                    print("=======\r\n")
                    Usage("-h")
                    sys.exit()

            g_dirty_git_repo_dirs = []
            g_git_update_thread_pools = []
            for walk_path in g_walk_paths:
                walk_and_update(g_git_cmd_type, walk_path, g_continue_when_meet_git, 0,
                                g_stop_when_meet_max_depth, g_git_stash_if_have_uncommitted_changes,
                                g_dirty_git_repo_dirs, g_git_update_thread_pools)
            for git_update_thread in g_git_update_thread_pools:
                git_update_thread.join(30)
            if len(g_dirty_git_repo_dirs) != 0:
                print('these repos have uncommitted changes or conflicts:\r\n')
                for dirty_repo_dir in g_dirty_git_repo_dirs:
                    print('dir %s has uncommited changes or conflicts, please check\r\n' % (dirty_repo_dir))

            print("Done git " + g_git_cmd_type.name + " all\r\n")
        except getopt.error as msg:
            raise Usage(msg)
    except Usage as err:
        print >> sys.stderr, err.msg
        print >> sys.stderr, "for help use --help\r\n"
        return 2


if __name__ == "__main__":
    sys.exit(main())
