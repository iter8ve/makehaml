from setuptools import setup

setup(
    name='makehaml',
    version='0.1',
    packages=['makehaml'],
    install_requires=['click', 'lmn-pyutils'],
    entry_points='''
        [console_scripts]
        makehaml=makehaml.cli:cli
    ''',
)