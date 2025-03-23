#!/usr/bin/env python
"""
Setup script for the Jira MCP package.
"""
from setuptools import setup, find_packages
import os

# Get long description from README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements.txt for dependencies
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh.readlines()]

setup(
    name="jira-mcp",
    version="0.2.0",
    author="Nokia Team",
    author_email="user@example.com",
    description="A modular Model Context Protocol (MCP) server for Jira",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/jira-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    include_package_data=True,
    # Entry points for command-line scripts
    entry_points={
        "console_scripts": [
            "jira-mcp=jira_mcp.main:main",
        ],
    },
) 