from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

setup(
    name='resultsdb-updater',
    version='7.0.0',
    description=('A micro-service that listens for messages on the message '
                 'bus and updates ResultsDB'),
    license='GPLv2+',
    author='Matt Prahl',
    author_email='mprahl@redhat.com',
    url='https://github.com/release-engineering/resultsdb-updater',
    install_requires=requirements,
    packages=find_packages(),
    entry_points="""
    [moksha.consumer]
    ciconsumer = resultsdbupdater.consumer:CIConsumer
    """,
)
