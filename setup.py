#!/bin/env python
# coding: utf-8

from setuptools import setup, find_packages

setup(
    name='ctabustracker',
    version='0.2dev1',
    description=("A python wrapper for the Chicago Transit Authority's"
                 ' Bustracker API.'),
    long_description='',
    url='https://github.com/tsaylor/ctabustracker',
    author='Tim Saylor',
    author_email='tim.saylor@gmail.com',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'beautifulsoup4',
        'lxml'
    ],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, <4'
)
