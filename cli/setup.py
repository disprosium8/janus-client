from setuptools import setup, find_packages

setup(
    name='JanusCLI',
    version='0.1',
    description='ESnet Janus Client CLI',
    url='https://github.com/disprosium8/janus-client',
    author='Ezra Kissel',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='dtn client cli',

    packages=find_packages(),

    install_requires=['ptyprocess', 'libtmux', 'pygments', 'docopt'],

    entry_points = {
        'console_scripts': [
            'janus = januscli.januscli:main',
        ]
    }
)
