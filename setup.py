from setuptools import find_packages, setup

setup(
    name="codexflow",
    version="0.4.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=["PyYAML>=6.0"],
)
