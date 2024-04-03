import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

install_requires = [line.strip() for line in open("requirements.txt").readlines()]

setuptools.setup(
    name='pyMotorport',
    version='1.0.213',
    author='Benjamin SAGGIN',
    description='A library to control Newport SMC100 controllers',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/Ben3094/pyMotorport',
    project_urls = {
        "Bug Tracker": "https://github.com/Ben3094/pyMotorport/issues"
    },
    license='MIT',
    packages=['pyMotorport'],
    install_requires=install_requires,
)