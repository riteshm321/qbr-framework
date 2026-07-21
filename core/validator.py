import os

def validate_files(folder):

    files = os.listdir(folder)

    print("\nDetected Files\n")

    for f in files:

        print("✔", f)

    return files