from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="buct-course",
    version="1.2.0",
    author="LingXin07",
    author_email="ling1163840260@gmail.com",
    description="北京化工大学课程平台作业查询",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ling0727-ai/python-buct-course",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.12",
    install_requires=[
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
    ],
    keywords="buct, education, api, automation",
)