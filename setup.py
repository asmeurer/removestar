import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

import versioneer

setuptools.setup(
    name="removestar",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Aaron Meurer",
    author_email="asmeurer@gmail.com",
    description="A tool to automatically replace 'import *' imports with explicit imports in files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://www.asmeurer.com/removestar/",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={'console_scripts': [ 'removestar = removestar.__main__:main']},
    python_requires= '>=3.6',
    install_requires=[
        'pyflakes'
    ],
    license='MIT',
)
