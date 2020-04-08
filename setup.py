from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="cchat",
    version="0.1.0",
    py_modules=find_packages(),
    description="Cli chat app made with Python & Twilio's Programmable Chat "
                "REST API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wangonya/cchat",
    author="Kinyanjui Wangonya",
    author_email="kwangonya@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    install_requires=[
        "prompt_toolkit",
        "requests",
        "twilio",
    ],
    entry_points="""
        [console_scripts]
        cchat=app:main
        """,
)