from setuptools import setup, find_packages

with open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

setup(
    name="macula",
    description="Optimistic rollup fraud proof generator",
    version="0.0.1",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="protolambda",
    author_email="proto+pip@protolambda.com",
    url="https://github.com/protolambda/macula",
    python_requires=">=3.8, <4",
    license="MIT",
    packages=find_packages(),
    py_modules=["macula"],
    tests_require=[],
    extras_require={
        "testing": ["pytest"],
        "linting": ["flake8", "mypy"],
    },
    install_requires=[
        "remerkleable==0.1.24",
        "rlp",
        "ethereum",
        "Click",
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'macula = macula._cli:cli',
        ],
    },
    keywords=["optimistic", "rollup", "optimism", "fraud-proof", "evm", "ethereum"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
    ],
)
