import subprocess
import sys

def install_playwright():
    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)

if __name__ == "__main__":
    install_playwright()
