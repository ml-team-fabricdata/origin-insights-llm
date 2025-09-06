from setuptools import setup, find_packages

setup(
    name="origin-insights-llm",
    version="0.1",
    packages=find_packages(include=["app", "app.*", "infra", "infra.*"]),
    install_requires=[],
)