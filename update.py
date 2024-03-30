import subprocess
import os

def clone_and_run():
    git_clone_cmd = "git clone https://github.com/bundestag/gesetze-tools.git"
    subprocess.run(git_clone_cmd, check=True, shell=True)

    os.chdir("gesetze-tools")

    pip_install_cmd = "pip install -r requirements.txt"
    subprocess.run(pip_install_cmd, check=True, shell=True)

    load_all_cmd = "python lawde.py loadall"
    subprocess.run(load_all_cmd, check=True, shell=True)

    convert_cmd = "python lawdown.py convert laws .."
    subprocess.run(convert_cmd, check=True, shell=True)

if __name__ == "__main__":
    clone_and_run()