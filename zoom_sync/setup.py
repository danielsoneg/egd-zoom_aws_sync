from setuptools import setup, find_packages

setup(
    name='zoom_sync',
    version='1.0',
    description='Packages for syncing Zoom videos to S3',
    author='Eric Danielson',
    author_email='eric@egd.im',
    python_requires=">=3.6",
    packages=find_packages(),
    install_requires=[
        'arrow',
        'boto3',
        'humanize',
        'python-jose',
        'requests',
    ],  # external packages as dependencies
)
