# setup.py
from setuptools import setup, find_packages

setup(
    name="origin_insights_llm",
    version="0.1.0",
    packages=find_packages(),  # esto incluye infra/, app/, etc.
    install_requires=[
        "fastapi",
        "uvicorn",
        # otros requirements que se sumen luego
    ],
)
