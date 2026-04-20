import os
import sys
from pathlib import Path
# Get the path to the project
project_path = Path(__file__).parent.parent.parent.parent # current_folder -> src -> test -> project

# Adding the directory to the sources of syspath
sources = os.path.join(project_path, "src")
sys.path.append(sources)
