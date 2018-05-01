from setuptools import find_packages, setup

setup(
    name='asyncirc',
    version='0.0.1',
    description='Python 3.6+ asyncio irc server and client library',
    long_description='',
    author='John Andersen',
    author_email='johnandersenpdx@gmail.com',
    maintainer='John Andersen',
    maintainer_email='johnandersenpdx@gmail.com',
    url='https://github.com/pdxjohnny/asyncirc',
    license='MIT',
    keywords=[
        'irc',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    install_requires=[],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'asyncircs = asyncirc.server:cli',
            'asyncircc = asyncirc.client:cli'
        ]
    }
)
