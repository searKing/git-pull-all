#!/usr/bin/python

import git
from git import *
import threading
import os
import sys
import getopt


# is_git_dir returns if current directory has .git/
def is_git_dir(dir_path: str):
    repo_git_dir = os.path.join(dir_path, '.git')
    if not os.path.exists(repo_git_dir):
        return False
    return True


def update_git_repo(git_repo_dir: str, dirty_git_repo_dirs: list):
    try:

        git_repo = git.Repo(git_repo_dir)
        if git_repo.is_dirty():
            dirty_git_repo_dirs.append(git_repo_dir)
            return
        remote_repo = git_repo.remote()
        print("start pulling from remote for: %s\r\n" % (git_repo_dir))
        remote_repo.pull()
        print("Done pulling for %s\r\n" % (git_repo_dir))
    except NoSuchPathError as e:
        pass
    except InvalidGitRepositoryError as e:
        pass
    finally:
        pass


def update_git_repo_thread(root_path: str, dirty_git_repo_dirs: list, git_update_thread_pools: list):
    git_update_thread_ = threading.Thread(target=update_git_repo, args=(root_path, dirty_git_repo_dirs))
    git_update_thread_.start()
    git_update_thread_pools.append(git_update_thread_)


def walk_and_update(root_path: str, continue_when_meet_git: bool, depth: int, max_depth: int, dirty_git_repo_dirs: list,
                    git_update_thread_pools: list):
    if depth >= max_depth:
        print("jump for %s too deep: depth[%d] max_depth[%d]\r\n" % (root_path, depth, max_depth))
        return
    if is_git_dir(root_path):
        update_git_repo_thread(root_path, dirty_git_repo_dirs, git_update_thread_pools)
        if not continue_when_meet_git:
            # print("jump subdirs for %s meet git\r\n" % (root_path))
            return
    depth = depth + 1
    for root_dir, sub_dirs, sub_files in os.walk(root_path):
        for sub_dir in sub_dirs:
            walk_and_update(os.path.join(root_dir, sub_dir), continue_when_meet_git, depth,
                            max_depth, dirty_git_repo_dirs, git_update_thread_pools)
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
            g_walk_paths: list = ["."]
            g_continue_when_meet_git: bool = False
            g_stop_when_meet_max_depth: int = 10
            opts, args = getopt.getopt(argv[1:], "hp:cd:",
                                       ["help", "path", "continue_when_meet_git=True", "stop_when_meet_max_depth=10"])
            if len(args) > 0:
                g_walk_paths = args
            for op, value in opts:
                if op == "-c":
                    g_continue_when_meet_git = True
                elif op == "-d":
                    g_stop_when_meet_max_depth = value
                elif op == "-h":
                    print("=======""Usage:")
                    print("python git_pull_all.py .")
                    print("python git_pull_all.py -c:true -d 10 YourPath")
                    print("python git_pull_all.py --continue_when_meet_git:true -stop_when_meet_max_depth 10 YourPath")
                    print("=======")
                    Usage("-h")
                    sys.exit()

            g_dirty_git_repo_dirs = []
            g_git_update_thread_pools = []
            for walk_path in g_walk_paths:
                walk_and_update(walk_path, g_continue_when_meet_git, 0,
                                g_stop_when_meet_max_depth, g_dirty_git_repo_dirs, g_git_update_thread_pools)
            for git_update_thread in g_git_update_thread_pools:
                git_update_thread.join(30)
            if len(g_dirty_git_repo_dirs) != 0:
                print('these repos have uncommitted changes:')
                for dirty_repo_dir in g_dirty_git_repo_dirs:
                    print('dir %s has uncommited change, please check' % (dirty_repo_dir))

        except getopt.error as msg:
            raise Usage(msg)
    except Usage as err:
        print >> sys.stderr, err.msg
        print >> sys.stderr, "for help use --help"
        return 2


if __name__ == "__main__":
    sys.exit(main())
