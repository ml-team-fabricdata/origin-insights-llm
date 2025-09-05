from setuptools import setup, find_packages

setup(
    name="origin_insights_llm",
    version="0.1",
    packages=find_packages(include=["app", "app.*", "modules", "modules.*", "infra", "infra.*"]),
)