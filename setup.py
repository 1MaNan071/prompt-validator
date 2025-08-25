from setuptools import setup, find_packages

setup(
    name="prompt-validator",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "langchain>=0.3.0",
        "langchain-community>=0.3.0",
        "langchain-core>=0.3.0",
        "langchain-groq>=0.1.0",
        "groq>=0.11.0",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
        "rich>=13.7.0",
        "pydantic>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "prompt-validator=prompt_validator.main:validate",
        ],
    },
    author="Manan Wakode",
    description="A module to validate and update prompt directories",
    python_requires=">=3.9",
)