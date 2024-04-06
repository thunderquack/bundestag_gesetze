import subprocess
import os
import shutil

def clone_and_run():
    git_clone_cmd = "git clone https://github.com/thunderquack/gesetze-tools.git"
    subprocess.run(git_clone_cmd, check=True, shell=True)

    os.chdir("gesetze-tools")

    pip_install_cmd = "pip install -r requirements.txt"
    subprocess.run(pip_install_cmd, check=True, shell=True)

    update_list_cmd = "python lawde.py updatelist"
    subprocess.run(update_list_cmd, check=True, shell=True)

    load_all_cmd = "python lawde.py loadall"
    subprocess.run(load_all_cmd, check=True, shell=True)

    convert_cmd = "python lawdown.py convert laws .."
    subprocess.run(convert_cmd, check=True, shell=True)

    os.chdir("..")
    current_directory = os.getcwd()
    print(f"Current Directory: {current_directory}")

    directory_to_delete = os.path.join(current_directory, 'gesetze-tools')
    try:
        shutil.rmtree(directory_to_delete)
        print(f"Folder {directory_to_delete} is removed.")
    except Exception as e:
        print(f"Error deleting folder {directory_to_delete}: {e}")

if __name__ == "__main__":
    clone_and_run()