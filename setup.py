import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

install_requires = [line.strip() for line in open("requirements.txt").readlines()]

setuptools.setup(
    name='pyNewportController',
    version='1.0.186',
    author='Benjamin SAGGIN',
    description='Testing installation of Package',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/Ben3094/pyNewportController',
    project_urls = {
        "Bug Tracker": "https://github.com/Ben3094/pyNewportController/issues"
    },
    license='MIT',
    packages=['pyNewportController'],
    install_requires=install_requires,
)