from setuptools import setup, find_packages

with open("README.md", "r", encoding='utf-8') as f:
    readme = f.read()

with open('LICENSE', encoding='utf-8') as f:
    license = f.read()

setup(
    name='builelib',
    version='0.1.27',
    description='builelib: building Energy-modeling Library',
    author='Masato Miyata',
    author_email='builelib@gmail.com',
    url='https://github.com/SuzuToyoda/builelib',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    package_data={'builelib': ['input_data/*', 'database/*', 'climatedata/*']},
    include_package_data=True,
    python_requires='>=3.7',
)
