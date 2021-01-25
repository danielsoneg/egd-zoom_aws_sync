import setuptools

setuptools.setup(
    name="s3index",
    version="0.1.0",
    author="Eric Danielson",
    author_email="eric@egd.im",
    description="HTML Index generator for s3 buckets",
    packages=setuptools.find_packages(),
    install_requires=["arrow", "click", "boto3", "jinja2", ],
    python_requires=">=3.6",
    entry_points={
            "console_scripts": [
                "s3index=s3index:main",
            ],
    },
)
