from setuptools import setup, find_packages

setup(
    name='DTNaaS Client',
    version='0.1',
    description='ESnet DTN as-a-Service Client',
    url='https://github.com/disprosium8/dtnaas-client',
    author='Ezra Kissel',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='dtn rest controller',

    packages=find_packages(),

    install_requires=['requests'],
)
