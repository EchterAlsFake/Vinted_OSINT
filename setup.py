from setuptools import setup, find_packages

setup(
    name="Vinted_OSINT",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "requests", "colorama", "fake_useragent", "prettytable"
    ],
    entry_points={
        'console_scripts': ['Vinted_OSINT=main:main'
            # If you want to create any executable scripts
        ],
    },
    author="Johannes Habel",
    author_email="EchterAlsFake@proton.me",
    description="An OSINT tool for Vinted.com",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license="GPLv3",
    url="https://github.com/EchterAlsFake/Vinted_OSINT",
    classifiers=[
        # Classifiers help users find your project on PyPI
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python",
    ],
)