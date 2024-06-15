from pathlib import Path

from setuptools import find_packages, setup

with open("iamksm_bot/version.py") as ver_file:
    exec(ver_file.read())


README: str = Path("README.md").read_text()

setup(
    name="iamksm-bot",
    version=__version__,  # NOQA
    description="A service that reviews Merge requests on Gitlab",  # noqa
    long_description=README,
    author="Kossam Ouma",
    author_email="koss.797@gmail.com",
    url="https://github.com/iamksm/ai-mr-reviewer#ai-mr-reviewer",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.8,<3.12",
    install_requires=[
        "flask~=3.0.3",
        "requests~=2.32.3",
        "python-gitlab~=4.6.0",
        "gunicorn[gevent]~=22.0.0",
        "ollama~=0.2.1",
        "pyyaml~=6.0.1",
    ],
)
