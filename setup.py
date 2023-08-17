from setuptools import setup
import os


def readme():
    with open("README.md") as f:
        return f.read()


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
data_files = [
    (
        "share/accelergy/estimation_plug_ins/accelergy-library-plugin",
        ["./accelergywrapper.py", "./helper_functions.py",
         "./scaling.py", "./library.estimator.yaml"],
    ),
]


def add_csv_dir(path):
    target = f'share/accelergy/estimation_plug_ins/' \
             f'accelergy-library-plugin/{path}'
    files = [os.path.join(path, f)
             for f in os.listdir(path) if f.endswith('.csv')]
    data_files.append((target, files))


for f in os.listdir('library'):
    if os.path.isdir(os.path.join('library', f)):
        add_csv_dir(os.path.join('library', f))
add_csv_dir('library')


setup(
    name="library",
    version="0.1",
    description="An energy estimation plug-in for Accelergy framework for "
    "serving a library of components.",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: "
        "Electronic Design Automation (EDA)",
    ],
    keywords="accelerator hardware energy estimation",
    author="Tanner Andrulis",
    author_email="andrulis@Mit.edu",
    license="MIT",
    install_requires=['accelergy>=0.4'],
    python_requires=">=3.8",
    data_files=data_files,
    include_package_data=True,
    entry_points={},
    zip_safe=False,
)
